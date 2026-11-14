"""Tickets 05 and 08: emergency Trigger (auto and manual) and 2-3 likely causes, before Spec 1 contracts exist.

Readings of rhythm state, heart rate and systolic blood pressure go in; a Trigger and an emergency
Alert with likely causes come out. Golden replay tests on the Pulse emergency follow once it exists.
"""
import pytest

from backend.baseline_a import LIKELY_CAUSE_LABEL, BaselineA, Thresholds, likely_causes
from backend.emergency import AutoDetect, EmergencyThresholds, emergency_alert, manual_trigger

# Test values only; the real ones are "Earth reference / team value" items kept in content/.
ETH = EmergencyThresholds(hr_high=150, hr_low=40, sbp_low=90, sustain_s=60)
DAY = 86_400.0


def stream(det, readings):
    """readings: (t, indicator, value). Returns every Trigger raised."""
    return [tr for t, ind, v in readings if (tr := det.process(ind, v, t))]


def test_shockable_or_non_perfusing_rhythm_raises_an_auto_trigger_at_once():
    for rhythm in ("VT", "VF", "PEA", "asystole"):
        found = stream(AutoDetect("C001", ETH), [(0, "rhythm", "sinus"), (5, "rhythm", rhythm)])
        assert len(found) == 1
        assert found[0]["kind"] == "auto" and found[0]["t"] == 5 and rhythm in found[0]["reason"]


def test_normal_stream_raises_nothing():
    assert not stream(AutoDetect("C001", ETH), [(t, "heart_rate", 70) for t in range(0, 600, 10)]
                      + [(t, "systolic_bp", 120) for t in range(5, 600, 10)])


@pytest.mark.parametrize("hr", [170, 30])
def test_sustained_extreme_heart_rate_with_low_pressure_raises_a_trigger(hr):
    readings = [(0, "systolic_bp", 80)] + [(t, "heart_rate", hr) for t in range(0, 121, 10)]
    found = stream(AutoDetect("C001", ETH), readings)
    assert len(found) == 1 and found[0]["t"] == 60  # sustained for sustain_s, then once only


def test_brief_extreme_heart_rate_is_not_enough():
    readings = [(0, "systolic_bp", 80), (0, "heart_rate", 170), (30, "heart_rate", 170), (40, "heart_rate", 80),
                (70, "heart_rate", 170), (100, "heart_rate", 170)]
    assert not stream(AutoDetect("C001", ETH), readings)


def test_extreme_heart_rate_with_normal_pressure_is_not_enough():
    readings = [(0, "systolic_bp", 120)] + [(t, "heart_rate", 170) for t in range(0, 121, 10)]
    assert not stream(AutoDetect("C001", ETH), readings)


def test_manual_and_auto_triggers_have_the_same_shape():
    auto = stream(AutoDetect("C001", ETH), [(5, "rhythm", "VF")])[0]
    manual = manual_trigger("C001", 5, "Emergency button")
    assert set(auto) == set(manual) == {"kind", "crew", "t", "reason", "confirmed"}
    assert manual["kind"] == "manual" and manual["confirmed"] is None


# --- Ticket 08: likely causes ---------------------------------------------------------------

ANCHOR = {"resting_hr": {"mean": 60.0, "sd": 2.0}, "sleep_h": {"mean": 7.0, "sd": 0.5},
          "systolic_bp": {"mean": 115.0, "sd": 6.0}, "temp_c": {"mean": 36.6, "sd": 0.2}}
TH = Thresholds(cusum_k=0.5, drift_amber=5.0, drift_red=10.0, acute_amber=3.5, acute_red=4.5, min_window=7)


def drifted_crew() -> BaselineA:
    """Last 9 days: heart rate +6 bpm (3 sd), sleep -1 h (2 sd), blood pressure +3 (0.5 sd), temperature normal."""
    a = BaselineA("C001", ANCHOR, TH, {})
    for d in range(69):
        drifting = d >= 60
        for ind, unit, normal, off in (("resting_hr", "bpm", 60.0, 6.0), ("sleep_h", "h", 7.0, -1.0),
                                       ("systolic_bp", "mmHg", 115.0, 3.0), ("temp_c", "C", 36.6, 0.0)):
            a.process(ind, normal + (off if drifting else 0.0), unit, d * DAY)
    return a


def test_likely_causes_rank_contributors_from_history():
    causes = likely_causes(drifted_crew(), min_sigma=1.0)
    assert [c["indicator"] for c in causes] == ["resting_hr", "sleep_h"]  # largest first; 0.5 sd is left out
    assert [c["direction"] for c in causes] == ["up", "down"]
    assert "resting hr +6 bpm over 9 days" in causes[0]["note"]
    assert all(LIKELY_CAUSE_LABEL in c["note"] for c in causes)
    assert all(set(c) == {"indicator", "direction", "note"} for c in causes)  # no protocol steps chosen here


def test_at_most_three_causes():
    assert len(likely_causes(drifted_crew(), min_sigma=0.1)) == 3


def test_no_deviation_gives_no_causes():
    a = BaselineA("C001", ANCHOR, TH, {})
    for d in range(30):
        a.process("resting_hr", 60.0, "bpm", d * DAY)
    assert likely_causes(a, min_sigma=1.0) == []


def test_emergency_alert_carries_act_now_and_likely_causes():
    a = drifted_crew()
    al = emergency_alert(manual_trigger("C001", 70 * DAY, "Emergency button"), a, min_sigma=1.0)
    assert (al["kind"], al["status"], al["urgency"]) == ("emergency", "red", "ACT_NOW")
    assert al["likely_causes"] and al["likely_causes"] == likely_causes(a, min_sigma=1.0)
    assert set(al) == {"id", "kind", "crew", "indicator", "deviation", "status", "urgency", "likely_causes", "t"}
