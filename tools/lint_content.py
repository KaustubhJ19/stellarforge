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

import json
import re
import sys
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
