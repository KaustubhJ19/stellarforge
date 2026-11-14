"""Content linter (Spec 5). A green run proves structure and citations, not medical correctness.

Rules so far (ticket 02):
  (a) every protocol step has a real source (non-empty guideline and section)
  (b) no drug name or dose anywhere in protocol content

Command line:
    python tools/content_lint.py [content_dir]   # default: content/ ; exit 0 clean, 1 problems
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contracts"))

from validate import ContractError, validate  # noqa: E402

# shortcut: a fixed list of common emergency/cardiac drugs, not a full formulary;
# extend it whenever new protocol content is added.
DRUGS = [
    "epinephrine", "adrenaline", "norepinephrine", "noradrenaline", "amiodarone", "lidocaine",
    "atropine", "vasopressin", "adenosine", "aspirin", "acetylsalicylic", "nitroglycerin",
    "glyceryl trinitrate", "morphine", "fentanyl", "ketamine", "heparin", "clopidogrel",
    "ticagrelor", "alteplase", "tenecteplase", "magnesium sulfate", "sodium bicarbonate",
    "calcium chloride", "naloxone", "midazolam", "diazepam", "propofol", "dextrose", "glucagon",
]
MEDICATION_RE = re.compile(r"\b(medications?|medicines?|drugs?)\b", re.IGNORECASE)
HANDOFF = "per flight surgeon"

# Spec 5 story 6: the environments guidance must fit. Every protocol states, for each one,
# whether published guidance covers it.
ENVIRONMENTS = {"spacecraft-transit", "station", "moon-base", "mars-base", "rover"}
NOT_COVERED = "not covered by published guidance"
COVERAGE_FILE = "coverage.json"

DRUG_RE = re.compile(r"\b(" + "|".join(map(re.escape, DRUGS)) + r")\b", re.IGNORECASE)
DOSE_RE = re.compile(r"\d+(?:[.,]\d+)?\s*(mg|mcg|µg|ug|g|ml|l|iu|units?|mmol|meq)\b", re.IGNORECASE)


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _filled(value):
    return isinstance(value, str) and value.strip() != ""


def lint_protocol(doc):
    """Return a list of problems (empty list = clean)."""
    try:
        validate("Protocol", doc)
    except ContractError as exc:
        return [f"contract: {exc}"]

    problems = []
    for i, step in enumerate(doc["steps"]):
        src = step["source"]
        if not (_filled(src.get("guideline")) and _filled(src.get("section"))):
            problems.append(f"steps/{i}: source needs a non-empty guideline and section")
    for text in _strings(doc):
        for m in DRUG_RE.finditer(text):
            problems.append(f"drug name {m.group(0)!r} in {text!r}")
        for m in DOSE_RE.finditer(text):
            problems.append(f"dose {m.group(0)!r} in {text!r}")
    # Citations are excluded: journal names like "Aerospace Medicine" are not instructions.
    shown = [doc["title"]] + [s for step in doc["steps"] for s in _strings([step["text"], step["equipment"]])]
    for text in shown:
        if MEDICATION_RE.search(text) and HANDOFF not in text.lower():
            problems.append(f"medication mentioned without {HANDOFF!r} handoff in {text!r}")
    return problems


def lint_coverage(doc, protocol_ids):
    """Check coverage.json: every protocol states, per environment, covered (with basis) or the honest label."""
    problems = [f"{pid}: protocol has no entry in {COVERAGE_FILE}" for pid in sorted(protocol_ids - doc.keys())]
    problems += [f"{pid}: {COVERAGE_FILE} entry for unknown protocol" for pid in sorted(doc.keys() - protocol_ids)]
    for pid, entry in doc.items():
        if not _filled(entry.get("source")):
            problems.append(f"{pid}: coverage needs a source")
        envs = entry.get("environments", {})
        problems += [f"{pid}: environment {e!r} not listed" for e in sorted(ENVIRONMENTS - envs.keys())]
        problems += [f"{pid}: unknown environment {e!r}" for e in sorted(envs.keys() - ENVIRONMENTS)]
        for env, c in envs.items():
            if c.get("covered") is True:
                if not _filled(c.get("basis")):
                    problems.append(f"{pid}/{env}: covered environment needs a basis (section)")
            elif c.get("label") != NOT_COVERED:
                problems.append(f"{pid}/{env}: uncovered environment must be labelled {NOT_COVERED!r}")
            for note in c.get("notes", []):
                if not (_filled(note.get("text")) and _filled(note.get("section"))):
                    problems.append(f"{pid}/{env}: note needs text and section")
    return problems


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc}"]


def lint_dir(content_dir):
    """Lint protocols and their coverage under content_dir/protocols. Returns {path: [problems]} for failing files."""
    failures = {}
    folder = Path(content_dir) / "protocols"
    ids = set()
    for path in sorted(p for p in folder.glob("*.json") if p.name != COVERAGE_FILE):
        doc, problems = _load(path)
        if doc is not None:
            problems = lint_protocol(doc)
            if isinstance(doc, dict) and "id" in doc:
                ids.add(doc["id"])
        if problems:
            failures[path] = problems
    cov_path = folder / COVERAGE_FILE
    if ids and not cov_path.exists():
        failures[cov_path] = ["missing: every protocol needs environment coverage"]
    elif cov_path.exists():
        cov, problems = _load(cov_path)
        problems = problems or lint_coverage(cov, ids)
        if problems:
            failures[cov_path] = problems
    return failures


def main(argv):
    content_dir = Path(argv[1]) if len(argv) > 1 else ROOT / "content"
    failures = lint_dir(content_dir)
    for path, problems in failures.items():
        for p in problems:
            print(f"{path}: {p}", file=sys.stderr)
    if failures:
        return 1
    print(f"{content_dir}: content lint clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
