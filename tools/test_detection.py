"""Detection wired to the Spec 1 contracts: service messages in, contract-valid messages out.

Message shape (backend/service.py): {"t": <mission seconds>, "type": <str>, "payload": <obj>}.
Out: "alert" (Alert), "trigger" (Trigger, kind auto) and "reading_state" (Reading with its new state).
Golden replays: the generated crew replays (replay/generated/, git-ignored; run tools/crew_replays.py)
and an emergency stream in the exact format of tools/emergency_replay.py (Pulse needs Windows).
Run the false-alert report: PYTHONPATH=. python tools/test_detection.py
"""
import json
import sys
from pathlib import Path

import pytest

from backend.detection import Detection

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contracts"))
from validate import validate  # noqa: E402

GENERATED = ROOT / "replay" / "generated"
CONTRACT = {"alert": "Alert", "trigger": "Trigger", "reading_state": "Reading"}
# Starting values from docs/cut-offs-needed.md (checked sources); team values until content/ holds them.
CUTOFFS = {"cusum_k": 0.5, "drift_amber": 4, "drift_red": 8, "acute_amber": 3, "acute_red": 4, "min_window": 7,
           "hr_high": 150, "hr_low": 50, "sbp_low": 90, "sustain_s": 30, "min_sigma": 1}
RECORD_B = {"schema_version": "1.0.0", "id": "B", "sex": "female", "missionProfile": "mars_transit",
            "anchor": {"resting_heart_rate": {"mean": 55.0, "sd": 3.0}}}


def reading(crew, indicator, value, unit, t, source="sim"):
    return {"t": t, "type": "reading", "payload": {"schema_version": "1.0.0", "crew": crew, "indicator": indicator,
                                                    "value": value, "unit": unit, "t": t, "source": source,
                                                    "confidence": 0.9, "state": "released"}}


def run(det, messages):
    out = []
    for m in messages:
        out += det.on_message(m)
    return out


def assert_valid(out):
    for m in out:
        validate(CONTRACT[m["type"]], m["payload"])
        assert m["t"] == m["payload"]["t"]


def emergency_stream(crew="B"):
    """Same names and units as tools/emergency_replay.py: one reading per second per indicator."""
    rhythm = lambda t: ("NormalSinus" if t < 240 else "SinusTachycardia" if t < 300
                        else "UnstableVentricularTachycardia" if t < 360 else "CoarseVentricularFibrillation")
    msgs = []
    for t in range(0, 400):
        hr = 75 if t < 240 else 165
        sbp = 118 if t <= 300 else 75  # pressure falls just after VT starts, so the rhythm route fires first
        msgs += [reading(crew, "heart_rate", hr, "1/min", t), reading(crew, "systolic_bp", sbp, "mmHg", t),
                 reading(crew, "cardiac_rhythm", rhythm(t), "rhythm", t)]
    return msgs


# --- Emergency (ticket 05) ---------------------------------------------------------------

def test_pulse_emergency_raises_one_auto_trigger_at_unstable_vt():
    out = run(Detection([RECORD_B], CUTOFFS), emergency_stream())
    assert_valid(out)
    triggers = [m["payload"] for m in out if m["type"] == "trigger"]
    assert len(triggers) == 1 and triggers[0]["kind"] == "auto"
    assert triggers[0]["t"] == 300 and "VT" in triggers[0]["reason"]


def test_auto_and_manual_trigger_give_the_same_emergency_alert():
    auto = [m["payload"] for m in run(Detection([RECORD_B], CUTOFFS), emergency_stream()) if m["type"] == "alert"]
    manual_trigger = {"t": 300, "type": "trigger", "payload": {"schema_version": "1.0.0", "kind": "manual",
                                                               "crew": "B", "t": 300, "reason": "Emergency button"}}
    det = Detection([RECORD_B], CUTOFFS)
    manual = [m["payload"] for m in run(det, emergency_stream()[:900] + [manual_trigger]) if m["type"] == "alert"]
    a, b = auto[-1], manual[-1]
    assert (a["kind"], a["urgency"], a["status"]) == (b["kind"], b["urgency"], b["status"]) == ("emergency", "ACT_NOW", "red")
    assert set(a) == set(b)


# --- Quarantine through Labels (ticket 07) ----------------------------------------------

def quiet_then_jump(det):
    msgs = [reading("B", "resting_heart_rate", 55 + (d % 3 - 1), "bpm", d * 86_400, "sensor") for d in range(30)]
    return run(det, msgs + [reading("B", "resting_heart_rate", 80, "bpm", 30 * 86_400, "sensor")])


def test_reading_after_an_alert_is_reported_quarantined_with_its_contract_fields():
    out = quiet_then_jump(Detection([RECORD_B], CUTOFFS))
    assert_valid(out)
    held = [m["payload"] for m in out if m["type"] == "reading_state"]
    assert held and held[-1]["state"] == "quarantined" and held[-1]["source"] == "sensor"


def test_false_alarm_label_releases_held_readings():
    det = Detection([RECORD_B], CUTOFFS)
    quiet_then_jump(det)
    out = det.on_label({"crew": "B", "t": 30 * 86_400 + 60, "note": "false alarm"})
    assert_valid(out)
    assert [m["payload"]["state"] for m in out] == ["released"]


def test_other_labels_change_nothing():
    det = Detection([RECORD_B], CUTOFFS)
    quiet_then_jump(det)
    assert det.on_label({"crew": "B", "t": 1, "kind": "ground_reply", "note": "see you soon"}) == []


def test_unknown_crew_is_ignored():
    assert Detection([RECORD_B], CUTOFFS).on_message(reading("Z", "resting_heart_rate", 60, "bpm", 0)) == []


# --- Golden crew replays (tickets 03, 13) ------------------------------------------------

def crew_replays():
    records = json.loads((GENERATED / "crew-records.json").read_text())
    return records, [json.loads((GENERATED / f"crew-{c}.json").read_text()) for c in "ABCD"]


def false_alert_report(cutoffs=CUTOFFS, bounds=()):
    """Alerts per crew-day on the four crew replays (Earth wearable data shaped as crew)."""
    records, replays = crew_replays()
    det, out, days = Detection(records, cutoffs, bounds), [], 0.0
    for rp in replays:
        events = rp["events"]
        days += (events[-1]["t"] - events[0]["t"]) / 86_400
        out += run(det, [{**e, "payload": {"schema_version": rp["schema_version"], **e["payload"]}} for e in events])
    alerts = [m["payload"] for m in out if m["type"] == "alert"]
    by_kind = {k: sum(a["kind"] == k for a in alerts) for k in ("drift", "acute")}
    return out, {"crew_days": round(days), **by_kind, "alerts_per_crew_day": len(alerts) / days}


@pytest.mark.skipif(not (GENERATED / "crew-A.json").exists(), reason="crew replays not generated (tools/crew_replays.py)")
def test_crew_replays_give_only_contract_valid_messages():
    out, report = false_alert_report()
    assert_valid(out)
    assert report["crew_days"] > 500


if __name__ == "__main__":
    from backend.detection import load_content
    print("starting values:", false_alert_report()[1])
    print("content values: ", false_alert_report(*load_content())[1])
