"""Approve protocol steps (Spec 1: AI drafts, humans approve, AI never overrides).

A PERSON on content/approvers.json runs this in a terminal. It shows each step next to the evidence-pack
quote it cites and asks for a yes per step. It records approved_by, approved_on (today) and a hash
of the step, so any later edit sends the step back to draft.

    python tools/approve_steps.py <protocol-id> [--step STEP_ID ...] [--content DIR]

An AI must never run this. It refuses to run without an interactive terminal.
To edit a step, change the JSON (the stale hash returns it to draft) and approve it again.
To reject a step, delete it or leave it as a draft: drafts are never rendered.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_content as lc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class ApprovalError(ValueError):
    pass


def approve(doc: dict, step_ids, name: str, approvers: set[str], today: str) -> list[str]:
    """Mark the named steps approved by `name`. Returns the ids approved."""
    if name not in approvers:
        raise ApprovalError(f"{name!r} is not on the approvers list")
    by_id = {s.get("id"): s for s in doc.get("steps", [])}
    unknown = [sid for sid in step_ids if sid not in by_id]
    if unknown:
        raise ApprovalError(f"unknown step {unknown[0]!r}")
    for sid in step_ids:
        s = by_id[sid]
        s.update(status=lc.APPROVED, approved_by=name, approved_on=today)
        s["approved_hash"] = lc.step_hash(s)
    return list(step_ids)


def _quotes(pack, source):
    for rec in (pack or {}).get("recommendations", []):
        if (rec.get("guideline"), rec.get("section")) == (source.get("guideline"), source.get("section")):
            return rec.get("quotes") or [f"({rec.get('kind', 'no quote')})"]
    return ["(section NOT in the evidence pack: the linter will reject this step)"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("protocol")
    ap.add_argument("--step", action="append", default=[], help="step id (repeat); default: every step not yet approved")
    ap.add_argument("--content", type=Path, default=ROOT / "content")
    args = ap.parse_args(argv)
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("approve_steps: refusing to run without an interactive terminal. Approval is a human act.", file=sys.stderr)
        return 2
    path = args.content / "protocols" / f"{args.protocol}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    pack_path = args.content / "protocols" / f"{args.protocol}.evidence.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8")) if pack_path.exists() else None
    approvers = lc.load_approvers(args.content / "approvers.json")
    name = input("Your name, exactly as on content/approvers.json: ").strip()
    if name not in approvers:
        print(f"{name!r} is not on the approvers list. Nothing approved.", file=sys.stderr)
        return 1
    ids = args.step or [s["id"] for s in doc["steps"] if lc.approval_problem(s, approvers)]
    chosen = []
    for s in (st for st in doc["steps"] if st["id"] in ids):
        print(f"\n--- {s['id']} ({s.get('status', 'no status')}, drafted by {s.get('drafted_by', 'a person')})")
        if not lc.approval_problem(s, approvers):
            print(f"NOTE:   already approved by {s['approved_by']} on {s['approved_on']}; a yes re-approves it as you.")
        print(f"STEP:   {s['text']}")
        print(f"CITES:  {s['source']['guideline']} / {s['source']['section']}")
        for q in _quotes(pack, s["source"]):
            print(f"QUOTE:  {q}")
        if input("Approve this exact text? [y/N] ").strip().lower() == "y":
            chosen.append(s["id"])
    if not chosen:
        print("Nothing approved.")
        return 0
    approve(doc, chosen, name, approvers, date.today().isoformat())
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Approved {len(chosen)} step(s) in {path.name} as {name}. Run tools/content_lint.py next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
