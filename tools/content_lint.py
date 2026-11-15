"""Content linter (Spec 5). A green run proves structure and citations, not medical correctness.

Rules so far (ticket 02):
  (a) every protocol step has a real source (non-empty guideline and section)
  (b) no drug name or dose anywhere in protocol content
  (e) ticket 10: every manifest item (replay/*.source.json) is in content/credits.json, and every
      Credits entry has name, link and licence, with restrictive licences stated plainly
  (f) Spec 2: action plans in content/plans/ (kind "action-plan") get rules (a) and (b) like protocols, and a
      non-stub plan needs a team approval (approval.approved_by and approval.approved_on)

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_content as lc  # noqa: E402  (shared approval rules, also used by the engine)

# Sourced groups: ISS crew-kit drugs (NASA papers) plus a team-value emergency group.
# shortcut: not a full formulary; the "per flight surgeon" rule below catches unnamed drugs.
_BLOCKLIST = json.loads((Path(__file__).resolve().parent / "drug_blocklist.json").read_text(encoding="utf-8"))
DRUGS = sorted({n for g in _BLOCKLIST["groups"] for n in g["names"]}, key=len, reverse=True)
MEDICATION_RE = re.compile(r"\b(medications?|medicines?|drugs?)\b", re.IGNORECASE)
HANDOFF = "per flight surgeon"

# Spec 5 story 6: the environments guidance must fit. Every protocol states, for each one,
# whether published guidance covers it.
ENVIRONMENTS = {"spacecraft-transit", "station", "moon-base", "mars-base", "rover"}
NOT_COVERED = "not covered by published guidance"
COVERAGE_FILE = "coverage.json"

DRUG_RE = re.compile(r"\b(" + "|".join(map(re.escape, DRUGS)) + r")\b", re.IGNORECASE)
# A concentration (54 mg/dL, 3.0 mmol/L) is a measurement, not a dose.
DOSE_RE = re.compile(r"\d+(?:[.,]\d+)?\s*(mg|mcg|µg|ug|g|ml|l|iu|units?|mmol|meq)\b(?!\s*/\s*d?l\b)", re.IGNORECASE)


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


# Spec 5 "Mission profile" shape (agreed with Specs 2 and 4). Each field is
# {"value", "status", "source"?, "note"?}; status is sourced (needs a link) or the team-value label.
PROFILE_FIELDS = ["gravity", "radiation_rate", "comm_delay", "evacuation", "medical_kit", "exercise_kit",
                  "crew_size", "duration", "dust", "closed_habitat"]
SOURCED = "sourced"
TEAM_VALUE = "not confirmed: team value"


def lint_profile(doc):
    """Test (d): every profile value is sourced (with a link) or labelled "not confirmed: team value"."""
    problems = [f"{k}: needs a non-empty string" for k in ("id", "name") if not _filled(doc.get(k))]
    for field in PROFILE_FIELDS:
        entry = doc.get(field)
        if not isinstance(entry, dict) or "value" not in entry:
            problems.append(f"{field}: missing (needs value and status)")
        elif entry.get("status") == SOURCED:
            if not (isinstance(entry.get("source"), str) and entry["source"].startswith(("https://", "http://"))):
                problems.append(f"{field}: sourced value needs a link (http/https source)")
        elif entry.get("status") != TEAM_VALUE:
            problems.append(f"{field}: status must be {SOURCED!r} or {TEAM_VALUE!r}")
    return problems


# Spec 3 reads this file (backend/detection.py CONTENT); it is not a Mission profile.
BOUNDS_FILE = "detection-cut-offs.json"
HONEST_LABELS = {"Earth reference, no space data", "team value", "estimate, not validated", TEAM_VALUE}


def _link(text):
    return isinstance(text, str) and ("https://" in text or "http://" in text)


def _labelled(where, item):
    """Label and source present; a label outside the honest set must point to a linked (space/personal) source."""
    problems = []
    if not _filled(item.get("label")):
        problems.append(f"{where}: needs a label")
    if not _filled(item.get("source")):
        problems.append(f"{where}: needs a source")
    elif item.get("label") not in HONEST_LABELS and not _link(item["source"]):
        problems.append(f"{where}: label {item.get('label')!r} is not a standard label, so the source needs a link")
    return problems


def lint_bounds(doc):
    """Safety bounds and detection cut-offs: every item labelled and sourced; bounds have a sane limit."""
    problems = []
    for i, c in enumerate(doc.get("cutoffs", [])):
        problems += _labelled(f"cutoffs/{i} ({c.get('name')})", c)
    for i, b in enumerate(doc.get("safety_bounds", [])):
        where = f"safety_bounds/{i} ({b.get('indicator')})"
        if not _filled(b.get("indicator")):
            problems.append(f"{where}: needs an indicator")
        low, high = b.get("low"), b.get("high")
        nums = [v for v in (low, high) if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not nums:
            problems.append(f"{where}: needs a numeric low or high")
        if len(nums) == 2 and low >= high:
            problems.append(f"{where}: low must be below high")
        problems += _labelled(where, b)
    return problems


# The 17 risks on https://www.nasa.gov/hrp/risks/ (read 2026-11-15), verbatim titles.
HRP_RISKS = {
    "Risk of Altered Immune System Responses", "Risk of Altered Sensorimotor and Vestibular Function",
    "Risk of Cardiovascular Adaptations", "Risk of Decompression Sickness",
    "Risk of Host-Microorganism Interactions", "Risk of Hypoxia", "Risk of Inadequate Food and Nutrition",
    "Risk of Injury and Compromised Performance from Spacewalks",
    "Risk of Reduced Cardiorespiratory and Musculoskeletal Fitness",
    "Risk of Spaceflight Associated Neuro-ocular Syndrome (SANS)", "Risk of Spaceflight-Induced Bone Changes",
    "Risk of Behavioral Changes and Psychiatric Disorders", "Risk of Inadequate Teamwork",
    "Risk of Inadequate Sleep and Irregular Schedules", "Risk of Inadequate Systems Operations Support",
    "Risk of Injury from Dynamic Loads", "Risk of Radiation-Induced Cancers",
}
UNCOVERED = "uncovered"
IF_ABNORMAL = ("now", "remeasure", "tell_crew", "tell_ground")


def lint_card(doc):
    """Test (c): every card's Why names an HRP risk (or is flagged uncovered with a reason); no drug or dose."""
    problems = [f"{k}: needs a non-empty string" for k in ("indicator", "unit", "space_note") if not _filled(doc.get(k))]
    how = doc.get("how")
    if not (isinstance(how, list) and how and all(_filled(h) for h in how)):
        problems.append("how: needs a non-empty list of steps")
    why = doc.get("why") or {}
    for k in ("text", "source"):
        if not _filled(why.get(k)):
            problems.append(f"why.{k}: needs a non-empty string")
    risk = why.get("hrp_risk")
    if risk == UNCOVERED:
        if not _filled(why.get("uncovered_reason")):
            problems.append("why: an uncovered HRP risk needs an uncovered_reason")
    elif risk not in HRP_RISKS:
        problems.append(f"why.hrp_risk {risk!r} is not a NASA HRP risk title (or {UNCOVERED!r})")
    steps = doc.get("if_abnormal") or {}
    problems += [f"if_abnormal.{k}: needs a non-empty string" for k in IF_ABNORMAL if not _filled(steps.get(k))]
    for text in _strings({k: v for k, v in doc.items() if k != "sources"}):
        problems += [f"drug name {m.group(0)!r} in {text!r}" for m in DRUG_RE.finditer(text)]
        problems += [f"dose {m.group(0)!r} in {text!r}" for m in DOSE_RE.finditer(text)]
    return problems


CREDITS_FILE = "credits.json"
# Licences that limit how the data may be used must say so in plain words on the Credits page.
RESTRICTIVE_RE = re.compile(r"\bNC\b|non-?commercial|research", re.IGNORECASE)


def lint_credits(doc, manifest):
    """Ticket 10: every entry has name, link and licence; restrictive licences say so plainly.
    Test (e): every manifest item (a replay/*.source.json name) is named by an entry's "manifest" list."""
    entries = doc.get("entries") if isinstance(doc, dict) else None
    if not (isinstance(entries, list) and entries):
        return ["credits: needs a non-empty list of entries"]
    problems, credited = [], set()
    for i, e in enumerate(entries):
        where = f"entries[{i}] ({e.get('name', '?')})"
        problems += [f"{where}: {k} needs a non-empty string" for k in ("name", "licence") if not _filled(e.get(k))]
        if not (_filled(e.get("link")) and e["link"].startswith("https://")):
            problems.append(f"{where}: link needs an https:// address")
        if _filled(e.get("licence")) and RESTRICTIVE_RE.search(e["licence"]) and not _filled(e.get("restriction")):
            problems.append(f"{where}: a restrictive licence needs a plain-words restriction")
        credited |= set(e.get("manifest", []))
    problems += [f"test (e): manifest item {m} is missing from the Credits" for m in sorted(set(manifest) - credited)]
    return problems


# ---- Spec 1: AI drafts, humans approve, AI never overrides -----------------------------------
APPROVERS_FILE = "approvers.json"
EVIDENCE_SUFFIX = ".evidence.json"
PACK_PARTS = ("why", "sources", "recommendations", "microgravity", "pulse")
PULSE_MODEL = {"yes", "no", "check"}


def _cite(src):
    return (src.get("guideline"), src.get("section")) if isinstance(src, dict) else (None, None)


def lint_approval(doc, approvers, pack):
    """Every step approved by a listed person, on a date, unchanged since, citing a section in its evidence pack."""
    problems = []
    cited = {(r.get("guideline"), r.get("section")) for r in (pack or {}).get("recommendations", []) if isinstance(r, dict)}
    for i, step in enumerate(doc.get("steps", [])):
        sid = step.get("id", i) if isinstance(step, dict) else i
        why = lc.approval_problem(step, approvers)
        if why:
            problems.append(f"steps/{sid}: {why}")
            continue
        if pack is None:
            problems.append(f"steps/{sid}: approved step but the protocol has no evidence pack")
        elif _cite(step.get("source")) not in cited:
            problems.append(f"steps/{sid}: cites {_cite(step.get('source'))[1]!r}, which is not in its evidence pack")
    return problems


def lint_stub_protocol(doc):
    """A stub skips approval, so it may only carry visibly fake text."""
    return [f"steps/{s.get('id', i) if isinstance(s, dict) else i}: {why}"
            for i, s in enumerate(doc.get("steps", [])) if (why := lc.stub_problem(s))]


def _pulse_problems(pulse):
    ok = isinstance(pulse, dict) and pulse.get("model") in PULSE_MODEL
    return [] if ok else [f"pulse: model must be one of {sorted(PULSE_MODEL)}"]


def lint_pack(doc):
    """Evidence pack: why the condition is in the library, licensed sources, verbatim quotes per section."""
    if not isinstance(doc, dict):
        return ["evidence pack must be an object"]
    problems = [f"evidence pack needs {k!r}" for k in ("protocol",) + PACK_PARTS if k not in doc]
    if problems:
        return problems
    for k in ("why", "microgravity"):
        if not _filled(doc[k]):
            problems.append(f"evidence pack needs a non-empty {k!r}")
    for i, src in enumerate(doc["sources"] or [None]):
        if not (isinstance(src, dict) and _filled(src.get("guideline"))):
            problems.append(f"sources/{i}: needs a guideline")
        elif not _filled(src.get("licence")):
            problems.append(f"sources/{i}: needs a licence")
    guidelines = {s.get("guideline") for s in doc["sources"] if isinstance(s, dict)}
    for i, rec in enumerate(doc["recommendations"] or [None]):
        if not (isinstance(rec, dict) and _filled(rec.get("guideline")) and _filled(rec.get("section"))):
            problems.append(f"recommendations/{i}: needs a guideline and a section")
            continue
        if rec["guideline"] not in guidelines:
            problems.append(f"recommendations/{i}: guideline is not listed in sources")
        quotes = rec.get("quotes")
        if rec.get("kind") != "team rule" and not (isinstance(quotes, list) and quotes and all(map(_filled, quotes))):
            problems.append(f"recommendations/{i}: needs at least one verbatim quote")
    problems += _pulse_problems(doc["pulse"])
    return problems


CONDITION_FIELDS = ("id", "name", "protocol", "state", "prior_incidence", "signs", "pulse", "labels")
CONDITION_STATES = {"existing", "pending"}
PRIOR_STATUS = {"sourced", "team value", "pending"}


def lint_condition(doc, protocol_ids):
    """Condition record: prior (sourced, team value or pending), signs with sources, Pulse, protocol."""
    if not isinstance(doc, dict):
        return ["condition record must be an object"]
    problems = [f"condition needs {k!r}" for k in CONDITION_FIELDS if k not in doc]
    if problems:
        return problems
    if not _filled(doc["name"]):
        problems.append("condition needs a name")
    if doc["state"] not in CONDITION_STATES:
        problems.append(f"state must be one of {sorted(CONDITION_STATES)}")
    elif doc["state"] == "existing" and doc["protocol"] not in protocol_ids:
        problems.append(f"existing condition names protocol {doc['protocol']!r}, which is not on disk")
    prior = doc["prior_incidence"]
    status = prior.get("status") if isinstance(prior, dict) else None
    if status not in PRIOR_STATUS:
        problems.append(f"prior_incidence: status must be one of {sorted(PRIOR_STATUS)}")
    elif status == "pending" and prior.get("value") is not None:
        problems.append("prior_incidence: pending prior must not carry a value")
    elif status != "pending" and not isinstance(prior.get("value"), (int, float)):
        problems.append("prior_incidence: needs a numeric value")
    elif status == "sourced" and not _filled(prior.get("source")):
        problems.append("prior_incidence: sourced prior needs a source")
    for i, sign in enumerate(doc["signs"] if isinstance(doc["signs"], list) else [None]):
        if not (isinstance(sign, dict) and _filled(sign.get("sign")) and _filled(sign.get("source"))):
            problems.append(f"signs/{i}: each sign needs text and a source")
    problems += _pulse_problems(doc["pulse"])
    if not (isinstance(doc["labels"], list) and all(map(_filled, doc["labels"]))):
        problems.append("labels must be a list of non-empty strings")
    return problems


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc}"]


def lint_plan(doc):
    """Spec 2 action plan: the protocol rules plus a recorded team approval (Spec 1 workflow)."""
    problems = lint_protocol(doc)
    approval = doc.get("approval") if isinstance(doc, dict) else None
    if not (isinstance(approval, dict) and _filled(approval.get("approved_by")) and _filled(approval.get("approved_on"))):
        problems.append("approval: an action plan needs approved_by and approved_on (team approval)")
    return problems


def _stub(doc):
    """Spec 4's non-clinical test doubles declare "stub": true; they are not Spec 5 content."""
    return isinstance(doc, dict) and doc.get("stub") is True


def lint_dir(content_dir):
    """Lint protocols and their coverage under content_dir/protocols. Returns {path: [problems]} for failing files."""
    failures = {}
    folder = Path(content_dir) / "protocols"
    ids = set()
    approvers = lc.load_approvers(Path(content_dir) / APPROVERS_FILE)
    # <id>.roles/.excerpts/.recorded/.evidence.json are companion files, not protocols.
    for path in sorted(p for p in folder.glob("*.json") if p.name != COVERAGE_FILE and p.name.count(".") == 1):
        doc, problems = _load(path)
        if _stub(doc):
            problems = lint_stub_protocol(doc)  # a stub skips approval, so it must stay visibly fake
            if problems:
                failures[path] = problems
            continue
        if doc is not None:
            problems = lint_protocol(doc)
            if isinstance(doc, dict) and "id" in doc:
                ids.add(doc["id"])
                pack_path = folder / f"{doc['id']}{EVIDENCE_SUFFIX}"
                pack = _load(pack_path)[0] if pack_path.exists() else None
                problems += lint_approval(doc, approvers, pack if isinstance(pack, dict) else None)
        if problems:
            failures[path] = problems
    for path in sorted(folder.glob(f"*{EVIDENCE_SUFFIX}")):
        doc, problems = _load(path)
        problems = problems or lint_pack(doc)
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
    for path in sorted((Path(content_dir) / "conditions").glob("*.json")):
        doc, problems = _load(path)
        problems = problems or lint_condition(doc, ids)
        if problems:
            failures[path] = problems
    # Spec 2 action plans; <id>.evidence.json and daily-loop.json / warm-start.json are not plans.
    for path in sorted((Path(content_dir) / "plans").glob("*.json")):
        doc, problems = _load(path)
        if path.name.count(".") != 1 or not (isinstance(doc, dict) and doc.get("kind") == "action-plan") or _stub(doc):
            continue
        problems = problems or lint_plan(doc)
        if problems:
            failures[path] = problems
    for path in sorted((Path(content_dir) / "profiles").glob("*.json")):
        doc, problems = _load(path)
        if _stub(doc):
            continue
        problems = problems or (lint_bounds(doc) if path.name == BOUNDS_FILE else lint_profile(doc))
        if problems:
            failures[path] = problems
    for path in sorted((Path(content_dir) / "cards").glob("*.json")):
        doc, problems = _load(path)
        problems = problems or lint_card(doc)
        if problems:
            failures[path] = problems
    # Spec 1 has no single manifest yet: the data lead's per-replay records are the manifest.
    manifest = {p.name for p in (Path(content_dir).parent / "replay").glob("*.source.json")}
    credits_path = Path(content_dir) / CREDITS_FILE
    if credits_path.exists():
        doc, problems = _load(credits_path)
        problems = problems or lint_credits(doc, manifest)
        if problems:
            failures[credits_path] = problems
    elif manifest:
        failures[credits_path] = ["missing: every manifest item needs a Credits entry (test e)"]
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
