"""Content linter (Spec 4, task 4.2 / ticket 02).

Fails the build when protocol content is unsafe:
  * a protocol step (or any threshold) has no source {guideline, section};
  * any drug name from the deny-list appears;
  * any dose (number + dose unit) appears.

Run:  python tools/lint_content.py [content_dir] [--deny path]
Exit code 1 on any issue.

Thresholds convention: any JSON object with a "threshold" key must carry a sibling
"source" {guideline, section}.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DENY = Path(__file__).resolve().parent / "drug-denylist.txt"
MEDICATION_PLACEHOLDER = "per flight surgeon / onboard medical checklist"

# Number followed by a dose unit. Plain counts ("30 compressions") do not match.
DOSE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mg/kg|mcg/kg|mg|mcg|µg|ug|g|ml|l|iu|units?|mmol|meq)(?![a-z]|/dl)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    file: str
    where: str
    reason: str

    def __str__(self) -> str:
        return f"{self.file}: {self.where}: {self.reason}"


def load_deny_list(path: Path = DEFAULT_DENY) -> list[str]:
    if not path.exists():
        return []
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line.lower())
    return terms


def find_drug_or_dose(text: str, deny: list[str]) -> str | None:
    """Return a reason string if text names a drug or a dose, else None."""
    low = text.lower()
    for term in deny:
        if re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", low):
            return f"drug name '{term}'"
    m = DOSE_RE.search(text)
    if m:
        return f"dose '{m.group(0)}'"
    return None


# --- Spec 1 (protocol library): "AI drafts, humans approve, AI never overrides" -------------
# A step reaches crew only when a person on the approvers list approved it, on a date, and its
# text has not changed since (hash stored at approval). Stub protocols (test doubles) are exempt
# but may only carry visibly fake "STUB" text.
DEFAULT_APPROVERS = ROOT / "content" / "approvers.json"
APPROVED, DRAFT = "approved", "draft"
STUB_PREFIX = "STUB"
_HASHED = ("text", "source", "equipment", "rescuers")  # everything a rescuer sees or the engine filters on
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_approvers(path: Path = DEFAULT_APPROVERS) -> set[str]:
    """Names allowed to approve. Missing file = nobody can approve."""
    if not path.exists():
        return set()
    names = json.loads(path.read_text(encoding="utf-8")).get("approvers", [])
    return {n.strip() for n in names if isinstance(n, str) and n.strip()}


def step_hash(step: dict) -> str:
    """sha256 of the rendered parts of a step. Any edit after approval changes it."""
    body = json.dumps({k: step.get(k) for k in _HASHED}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _valid_date(value) -> bool:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def approval_problem(step, approvers: set[str]) -> str | None:
    """None when the step may be rendered; otherwise why not."""
    if not isinstance(step, dict):
        return "not a step"
    status = step.get("status")
    if status != APPROVED:
        if status == DRAFT and not (isinstance(step.get("drafted_by"), str) and step["drafted_by"].strip()):
            return "draft without drafted_by"
        return f"not approved (status {status!r})"
    if step.get("approved_by") not in approvers:
        return f"approver {step.get('approved_by')!r} is not on the approvers list"
    if not _valid_date(step.get("approved_on")):
        return "approved step needs approved_on (YYYY-MM-DD)"
    if step.get("approved_hash") != step_hash(step):
        return "step changed after approval: back to draft (re-approve)"
    return None


def stub_problem(step) -> str | None:
    """Stub protocols carry only visibly fake text."""
    text = step.get("text") if isinstance(step, dict) else None
    # The fixed medication hand-off (Rule 4) is not clinical text, so a stub may carry it verbatim.
    if not (isinstance(text, str) and (text.startswith(STUB_PREFIX) or text == MEDICATION_PLACEHOLDER)):
        return f"stub protocol step must start with {STUB_PREFIX!r}"
    return None


def _source_ok(src) -> bool:
    return (
        isinstance(src, dict)
        and isinstance(src.get("guideline"), str) and src["guideline"].strip() != ""
        and isinstance(src.get("section"), str) and src["section"].strip() != ""
    )


def _walk(node, path="$"):
    yield path, node
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def lint_data(data, name: str, deny: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    if isinstance(data, dict) and isinstance(data.get("steps"), list):
        for i, step in enumerate(data["steps"]):
            sid = step.get("id", f"#{i}") if isinstance(step, dict) else f"#{i}"
            if not isinstance(step, dict) or not _source_ok(step.get("source")):
                issues.append(Issue(name, f"step {sid}", "no source (needs guideline and section)"))
    for path, node in _walk(data):
        if isinstance(node, dict) and "threshold" in node and not _source_ok(node.get("source")):
            issues.append(Issue(name, path, "threshold has no source"))
        if isinstance(node, str):
            reason = find_drug_or_dose(node, deny)
            if reason:
                issues.append(Issue(name, path, reason))
    return issues


def lint_tree(root: Path, deny: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for f in sorted(root.rglob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            issues.append(Issue(str(f), "$", f"invalid JSON: {e}"))
            continue
        issues += lint_data(data, str(f.relative_to(root)), deny)
        issues += lint_approval(data, f, root)
    return issues


def lint_approval(data, f: Path, root: Path) -> list[Issue]:
    """Spec 1: a protocol file (content/protocols/<id>.json) serves only approved steps; a stub only STUB text."""
    if not (f.parent == root / "protocols" and f.name.count(".") == 1 and isinstance(data, dict)
            and isinstance(data.get("steps"), list)):
        return []
    approvers = load_approvers(root / "approvers.json")
    issues = []
    for i, step in enumerate(data["steps"]):
        why = stub_problem(step) if data.get("stub") is True else approval_problem(step, approvers)
        if why:
            sid = step.get("id", f"#{i}") if isinstance(step, dict) else f"#{i}"
            issues.append(Issue(str(f.relative_to(root)), f"step {sid}", why))
    return issues


def main(argv: list[str]) -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("root", nargs="?", default=str(ROOT / "content"))
    p.add_argument("--deny", default=str(DEFAULT_DENY))
    a = p.parse_args(argv)
    root = Path(a.root)
    deny = load_deny_list(Path(a.deny))
    issues = lint_tree(root, deny)
    for i in issues:
        print(f"LINT FAIL  {i}")
    if not deny:
        print("LINT NOTE  drug deny-list is empty: drug names are not checked until Spec 5 supplies the list (doses are).")
    print(f"content lint: {len(issues)} issue(s) in {root}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
