"""FastAPI service for the emergency flow. Local only (habitat network stand-in).

Run:  backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import offline
from . import replay as replay_mod
from .clock import MissionClock
from .contracts import ContractError
from .flow import AccessDenied, FlowEngine, FlowError
from .ollama_boot import OllamaStatus, ensure_ollama
from .runtime import REAL_RECORDS, build
from .store import StoreError
from .triage import IntakeError

log = logging.getLogger("uvicorn.error")  # shows in the server output
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class Answer(BaseModel):
    crew: str
    question: str
    choice: str
    emergency: str | None = None

class CrewAction(BaseModel):
    crew: str
    emergency: str | None = None

class Observer(CrewAction):
    choice: str

class IntakeForm(CrewAction):
    intake: dict

class SwitchProtocol(CrewAction):
    protocol: str

class Explain(CrewAction):
    question: str | None = None

class Reply(BaseModel):
    report: str | None = None
    text: str = ""
    scripted: bool = False


def create_app(engine: FlowEngine | None = None, ticker: bool = True) -> FastAPI:
    eng = engine or build(
        # Real content by default; SF_PROTOCOL=stub-protocol SF_PROFILE=stub-mars SF_RECORDS=<stub file> runs the test doubles.
        # Setting SF_PROTOCOL forces that one protocol and turns intent-first routing off.
        routing="SF_PROTOCOL" not in os.environ,
        protocol=os.environ.get("SF_PROTOCOL", "microgravity-cpr"),
        profile=os.environ.get("SF_PROFILE", "mars_transit"),
        records_path=Path(os.environ.get("SF_RECORDS", REAL_RECORDS)),
        db=os.environ.get("SF_DB", ":memory:"),
        clock=MissionClock(speed=float(os.environ.get("SF_CLOCK_SPEED", "1"))),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if ticker:
            async def loop():
                while True:
                    eng.tick()
                    await asyncio.sleep(0.25)
            task = asyncio.create_task(loop())
        booted: dict[str, OllamaStatus] = {}
        transport = getattr(getattr(eng, "explainer", None), "transport", None)
        if hasattr(transport, "url"):  # a real Ollama transport (tests use plain functions)
            def boot_model():
                booted["ollama"] = ensure_ollama(transport.url)  # start Ollama if it is not running
                log.info("Ollama: %s %s", booted["ollama"].status, booted["ollama"].detail)
                eng.explainer.warm_up()
            threading.Thread(target=boot_model, daemon=True).start()
        if eng.habitat:
            eng.habitat.start()
        yield
        if task:
            task.cancel()
        started = booted.get("ollama")
        if started and started.status == "started" and started.proc:
            started.proc.terminate()  # we started it, so we stop it

    app = FastAPI(title="StellarForge emergency flow", lifespan=lifespan)
    app.state.engine = eng

    @app.exception_handler(ContractError)
    async def _contract(_: Request, exc: ContractError):
        return JSONResponse({"error": str(exc)}, status_code=422)

    @app.exception_handler(IntakeError)
    async def _intake(_: Request, exc: IntakeError):
        return JSONResponse({"error": str(exc)}, status_code=422)

    @app.exception_handler(FlowError)
    async def _flow(_: Request, exc: FlowError):
        return JSONResponse({"error": str(exc)}, status_code=409)

    @app.exception_handler(AccessDenied)
    async def _denied(_: Request, exc: AccessDenied):
        return JSONResponse({"error": str(exc)}, status_code=403)

    @app.exception_handler(StoreError)
    async def _store(_: Request, exc: StoreError):
        return JSONResponse({"error": f"refused: {exc}"}, status_code=503)

    # ---- tablets -------------------------------------------------------
    @app.post("/api/trigger", status_code=201)
    def manual_trigger(trig: dict):
        if trig.get("kind") != "manual":
            raise ContractError("trigger: kind: the Emergency button posts kind 'manual'")
        e = eng.trigger(trig)
        if eng.habitat:  # tell the habitat network; the local flow runs either way
            try:
                eng.habitat.post_trigger(trig)
            except Exception as err:  # noqa: BLE001
                eng.emit("habitat_post_failed", what="trigger", error=str(err))
        return {"emergency": e.id}

    @app.get("/api/view")
    def view(crew: str):
        return eng.view(crew)

    @app.post("/api/answer")
    def answer(a: Answer):
        eng.answer(a.crew, a.question, a.choice, a.emergency)
        return eng.view(a.crew)

    @app.post("/api/accept")
    def accept(a: CrewAction):
        return {"role": eng.accept(a.crew, a.emergency)}

    @app.post("/api/join-r2")
    def join_r2(a: CrewAction):
        return {"role": eng.join_r2(a.crew, a.emergency)}

    @app.post("/api/observer")
    def observer(a: Observer):
        eng.observer_answer(a.crew, a.choice, a.emergency)
        return eng.view(a.crew)

    @app.post("/api/intake")
    def intake(a: IntakeForm):
        eng.submit_intake(a.crew, a.intake, a.emergency)
        return eng.view(a.crew)

    @app.post("/api/switch-protocol")
    def switch_protocol(a: SwitchProtocol):
        eng.switch_protocol(a.crew, a.protocol, a.emergency)
        return eng.view(a.crew)

    @app.post("/api/next")
    def nxt(a: CrewAction):
        eng.next(a.crew, a.emergency)
        return eng.view(a.crew)

    @app.post("/api/back")
    def back(a: CrewAction):
        eng.back(a.crew, a.emergency)
        return eng.view(a.crew)

    @app.post("/api/explain")
    def explain(a: Explain):
        if not getattr(eng, "explainer", None):
            raise FlowError("explainer not available")
        return eng.explainer.explain(a.crew, a.question)

    @app.get("/api/record")
    def record(actor: str, subject: str):
        return eng.open_record(actor, subject)

    @app.get("/api/access-log")
    def access_log(crew: str, viewer: str):
        """A crewmate sees who opened their own record (story 9)."""
        if viewer != crew:
            raise AccessDenied("only the record owner can view its access log")
        return eng.store.access_log(subject=crew)

    # ---- stream boundary (Spec 1 / Spec 3 post here) -------------------
    @app.post("/api/stream/alert", status_code=202)
    def stream_alert(alert: dict):
        eng.ingest_alert(alert)
        return {"ok": True}

    @app.post("/api/stream/reading", status_code=202)
    def stream_reading(reading: dict):
        eng.ingest_reading(reading)
        return {"ok": True}

    @app.post("/api/stream/trigger", status_code=201)
    def stream_trigger(trig: dict):
        e = eng.trigger(trig)
        return {"emergency": e.id}

    # ---- ground console ------------------------------------------------
    @app.get("/api/console")
    def console():
        if not eng.ground:
            raise FlowError("ground console not available")
        return eng.ground.console_view()

    @app.post("/api/console/reply")
    def console_reply(r: Reply):
        if not eng.ground:
            raise FlowError("ground console not available")
        return eng.ground.console_reply(r.report, r.text, scripted=r.scripted)

    @app.get("/api/labels")
    def labels(crew: str | None = None):
        return eng.store.labels(crew)

    # ---- demo / simulation (test doubles) ------------------------------
    @app.get("/api/sim/crew")
    def sim_crew():
        return {"crew": eng.crew, "names": {c: eng.name(c) for c in eng.crew},
                "profile": eng.profile["id"], "protocol": eng.protocol.id, "stub": eng.protocol.stub, "t": eng.now()}

    # Demo/test helpers: they reset or move a live emergency, so they exist only when SF_SIM=1.
    if os.environ.get("SF_SIM") == "1":
        @app.post("/api/sim/clock/advance")
        def sim_advance(body: dict):
            eng.clock.advance(float(body.get("seconds", 0)))
            eng.tick()
            return {"t": eng.now()}

        @app.post("/api/sim/reset")
        def sim_reset():
            """Demo/test only: fresh flow state with the same content and settings."""
            fresh = build(protocol=eng.protocol.id, profile=eng.profile["id"], routing=eng.routing,
                          clock=MissionClock(speed=eng.clock.speed), explainer=eng.explainer.transport)
            eng.__dict__.update(fresh.__dict__)
            eng.ground.eng = eng
            eng.explainer.eng = eng
            return {"ok": True}

        @app.post("/api/sim/replay")
        def sim_replay(body: dict):
            replay_mod.run(eng, replay_mod.load(Path(__file__).resolve().parents[2] / "replay" / Path(body["file"]).name))
            return {"t": eng.now()}

    @app.get("/api/offline-bundle")
    def offline_bundle():
        return offline.bundle(eng)

    @app.post("/api/sync")
    def sync(body: dict):
        return offline.sync(eng, body.get("tablet", ""), body.get("items") or [])

    @app.get("/api/health")
    def health():
        return {"ok": True}

    if DIST.exists():
        app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            f = (DIST / path).resolve()
            inside = f.is_relative_to(DIST.resolve())  # never serve a file outside dist
            return FileResponse(f if path and inside and f.is_file() else DIST / "index.html")

    return app


app = create_app() if os.environ.get("SF_NO_APP") != "1" else None
