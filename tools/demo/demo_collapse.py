"""Run Spec 3 detection over the real crew B emergency replay; save the emergency Alert and auto Trigger it raises.

The backup recording (tools/demo/record_demo.mjs) posts these to the Spec 4 app, so the collapse on
screen is the one Spec 3 detects in Spec 1's replay, not a hand-made test double.

    python tools/demo/demo_collapse.py out/collapse.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from backend.detection import Detection, load_content  # noqa: E402  (Spec 3)


def collapse_messages(replay_path=ROOT / "replay" / "emergency-crew-B.json", records_path=ROOT / "replay" / "crew-records.json"):
    records = json.loads(Path(records_path).read_text(encoding="utf-8"))
    records = records if isinstance(records, list) else records["records"]
    cutoffs, bounds = load_content()
    det = Detection(records, cutoffs, bounds)
    out = []
    for ev in json.loads(Path(replay_path).read_text(encoding="utf-8"))["events"]:
        for m in det.on_message({"type": ev["type"], "payload": ev["payload"], "t": ev["t"]}) or []:
            if m["type"] == "trigger" or (m["type"] == "alert" and m["payload"].get("kind") == "emergency"):
                out.append(m)
        if {m["type"] for m in out} == {"alert", "trigger"}:
            return out
    raise SystemExit("Spec 3 detection raised no emergency in the replay")


if __name__ == "__main__":
    msgs = collapse_messages()
    Path(sys.argv[1]).write_text(json.dumps(msgs, indent=2), encoding="utf-8")
    for m in msgs:
        print(m["type"], m["payload"].get("kind"), m["payload"].get("reason", m["payload"].get("urgency")))
