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
    return problems


def lint_dir(content_dir):
    """Lint every protocol file under content_dir/protocols. Returns {path: [problems]} for failing files."""
    failures = {}
    for path in sorted((Path(content_dir) / "protocols").glob("*.json")):
        try:
            problems = lint_protocol(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            problems = [f"invalid JSON: {exc}"]
        if problems:
            failures[path] = problems
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
