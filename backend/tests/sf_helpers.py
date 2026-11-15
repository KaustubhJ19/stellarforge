"""Shared test data builders (Spec 1 contract shapes)."""
SV = "1.0.0"


def alert(crew="cmdr", urgency="ACT_NOW", causes=("STUB cause 1", "STUB cause 2", "STUB cause 3", "STUB cause 4"), t=0):
    return {"schema_version": SV, "id": f"al-{crew}-{urgency}", "kind": "emergency", "crew": crew, "indicator": "STUB-indicator",
            "deviation": {"sigma": 4.0}, "status": "red", "urgency": urgency,
            "likely_causes": [{"indicator": "STUB_indicator", "direction": "down", "note": c} for c in causes], "t": t}


def trig(crew="cmdr", kind="manual", t=0, reason="button"):
    return {"schema_version": SV, "kind": kind, "crew": crew, "t": t, "reason": reason}
