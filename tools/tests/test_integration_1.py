"""Ticket 08 (Integration #1): golden end-to-end run on real content, both triggers, offline.

Real code from every stream: Spec 1 habitat service and replay, Spec 3 detection, Spec 4 flow,
Spec 5 protocol, profile and recorded answers. No stubs: protocol microgravity-cpr, profile
mars_transit, crew records and the crew B emergency replay from replay/. The explainer is off,
so "Why this step?" uses the recorded answers (the offline path). Only 127.0.0.1 is contacted.
"""
import json
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "backend", ROOT / "tools"):
    sys.path.insert(0, str(p))

pytest.importorskip("fastapi")
from backend.detection import Detection, load_content  # noqa: E402  (Spec 3)
from service import HabitatService, make_server  # noqa: E402  (Spec 1)
from app import replay  # noqa: E402  (Spec 4)
from app.runtime import build  # noqa: E402  (Spec 4)

RECORDS = ROOT / "replay" / "crew-records.json"
EMERGENCY = ROOT / "replay" / "emergency-crew-B.json"
CPR = json.loads((ROOT / "content/protocols/microgravity-cpr.json").read_text(encoding="utf-8"))
RECORDED = json.loads((ROOT / "content/protocols/microgravity-cpr.recorded.json").read_text(encoding="utf-8"))["answers"]
ARREST_T = 13134960  # first CoarseVentricularFibrillation Reading in the crew B replay


def walk(eng, crew):
    seen = []
    while (v := eng.view(crew))["screen"] == "step":
        seen.append(v["step"]["id"])
        eng.next(crew)
    return seen, v["screen"]


def wait(cond, timeout=90.0):  # 25,740 replay Readings pass through detection first
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


# ---- manual trigger, in-process -------------------------------------------------

@pytest.fixture
def eng():
    return build(protocol="microgravity-cpr", profile="mars_transit", records_path=str(RECORDS), explainer=None)


def to_steps(eng, patient="B", rescuer="A"):
    replay.run(eng, {"id": "t", "events": [{"t": 0, "type": "press_emergency", "data": {"crew": patient}}]}, until=15)
    eng.accept(rescuer)
    eng.observer_answer(rescuer, "no")
    eng.next(rescuer)  # record -> contributors
    eng.next(rescuer)  # contributors -> first step


def test_manual_trigger_reaches_the_real_cited_steps(eng):
    to_steps(eng)
    v = eng.view("A")
    assert v["screen"] == "step" and v["step"]["id"] == CPR["steps"][0]["id"]
    assert v["step"]["text"] == CPR["steps"][0]["text"]
    assert v["step"]["source"]["guideline"].startswith("Hinkelbein")


def test_solo_rescuer_sees_only_one_rescuer_steps_then_the_report(eng):
    to_steps(eng)
    seen, end = walk(eng, "A")
    expected = [s["id"] for s in CPR["steps"] if s["rescuers"] <= 1]
    assert seen == expected and end != "step"
    assert "cpr-8-airway-gate" not in seen and "cpr-11-venous-access" not in seen


def test_why_this_step_answers_offline_from_the_recorded_answer(eng):
    to_steps(eng)
    r = eng.explainer.explain("A")
    assert r["mode"] == "recorded" and r["answer"] == RECORDED[r["step"]]


def test_ground_report_uses_the_mars_transit_delay(eng):
    assert eng.profile["delay_one_way_s"] == 1710
    assert eng.ground.one_way == 1710


# ---- auto trigger: the real replay through Spec 1 and Spec 3 ---------------------

class FakeMonotonic:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def chain(tmp_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    records = json.loads(RECORDS.read_text(encoding="utf-8"))
    records = records if isinstance(records, list) else records["records"]
    cutoffs, bounds = load_content()
    mono = FakeMonotonic()
    svc = HabitatService(str(tmp_path / "h.sqlite"), [json.loads(EMERGENCY.read_text(encoding="utf-8"))], records,
                         monotonic=mono, detection=Detection(records, cutoffs, bounds))
    mono.now += ARREST_T + 30 - svc.clock.now()  # jump the Mission clock to just after the arrest
    httpd = make_server(svc, port=port, tick_interval=0.05)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    eng = build(protocol="microgravity-cpr", profile="mars_transit", records_path=str(RECORDS),
                explainer=None, habitat_url=url)
    eng.habitat.start()
    assert eng.habitat.connected.wait(5)
    yield svc, eng, mono
    eng.habitat.stop()
    httpd.shutdown()
    svc.close()


def test_real_replay_raises_the_auto_trigger_and_reaches_the_real_steps(chain):
    svc, eng, mono = chain
    start = time.time()
    assert wait(lambda: eng.active_for("B") is not None), eng.habitat.errors
    print(f"auto trigger after {time.time() - start:.1f} s")
    trig = next(e for e in eng.events if e["type"] == "trigger")
    assert trig["kind"] == "auto" and trig["crew"] == "B"  # raised by Spec 3 detection from the replay
    assert wait(lambda: eng.view("B").get("urgency") == "ACT_NOW"), eng.alerts
    mono.now += 20  # the patient does not answer for 15 mission seconds -> crew alarm
    assert wait(lambda: (eng.clock.sync(), eng.tick(),
                         eng.view("A")["screen"] == "alarm")[-1]), eng.view("A")
    eng.accept("A")
    eng.observer_answer("A", "no")
    eng.next("A")
    eng.next("A")
    v = eng.view("A")
    assert v["screen"] == "step" and v["step"]["id"] == CPR["steps"][0]["id"]
