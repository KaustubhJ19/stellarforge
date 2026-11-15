"""Service: the "habitat network" (Spec 1 task 1.8).

Plays replay files on the Mission clock, accepts manual Readings, Triggers, Labels
and ground replies, pushes events to three windows (patient, rescuer, ground) and
holds all Crew records. Everything is stored in SQLite so a restart resumes.

Event messages pushed to windows: {"t": <mission seconds>, "type": <str>, "payload": <obj>}.
Replay events of type "reading" or "trigger" are checked against the Reading or
Trigger contract; their payload takes the replay file's schema_version if it has none.

Transport: Server-Sent Events over the Python standard library (no extra dependencies).
  GET  /events?window=patient|rescuer|ground   event stream
  GET  /clock                                  {"t", "speed", "label"}
  GET  /crew/<id>?requester=<id>[&emergency=1] crew record (others' only in emergency, logged)
  GET  /hot_summary/<crew>                     Spec 2 HotSummary snapshot (needs the daily loop as detection)
  POST /reading /trigger /label /ground_reply  JSON body
  POST /form /location                         Spec 2 provisional shapes (backend/crew_data.py)
  POST /clock/speed {"speed": 1|60}            POST /clock/skip

Run: python backend/service.py --db habitat.sqlite --replay replay/a.json --crew crew.json
"""
import argparse
import copy
import hashlib
import json
import logging
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))
from mission_clock import MissionClock  # noqa: E402
from crew_data import PROVISIONAL, validate_provisional  # noqa: E402
from store import Store  # noqa: E402
from validate import validate  # noqa: E402

WINDOWS = ("patient", "rescuer", "ground")
EVENT_CONTRACTS = {"reading": "Reading", "trigger": "Trigger"}


class HabitatService:
    def __init__(self, db_path, replays, crew_records, monotonic=time.monotonic, detection=None):
        self.detection = detection  # Spec 3 backend/detection.py; None runs without detection
        self._lock = threading.RLock()
        self._subscribers = {}  # token -> callback
        self._sub_changed = threading.Condition(self._lock)
        self._crew = {}
        for record in crew_records:
            validate("CrewRecord", record)
            if record["id"] in self._crew:
                raise ValueError(f"Duplicate crew record id {record['id']!r}")
            self._crew[record["id"]] = copy.deepcopy(record)

        self._queue = []
        for r_index, rp in enumerate(replays):
            validate("ReplayFile", rp)
            for e_index, event in enumerate(rp["events"]):
                payload = event["payload"]
                if event["type"] in EVENT_CONTRACTS:
                    payload = {"schema_version": rp["schema_version"], **payload}
                    validate(EVENT_CONTRACTS[event["type"]], payload)
                elif event["type"] in PROVISIONAL:  # Spec 2: form, location
                    payload = validate_provisional(event["type"], {"schema_version": rp["schema_version"], **payload})
                self._queue.append((event["t"], r_index, e_index, {"t": event["t"], "type": event["type"], "payload": payload}))
        self._queue.sort(key=lambda item: item[:3])
        fingerprint = hashlib.sha256(json.dumps(replays, sort_keys=True).encode("utf-8")).hexdigest()

        self.store = Store(db_path, check_same_thread=False)
        conn = self.store.conn
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS service_state ("
                         "id INTEGER PRIMARY KEY CHECK (id = 1), fingerprint TEXT, delivered INTEGER, mission_t REAL, speed INTEGER)")
        row = conn.execute("SELECT fingerprint, delivered, mission_t, speed FROM service_state").fetchone()
        if row is None:
            with conn:
                conn.execute("INSERT INTO service_state VALUES (1, ?, 0, 0, 1)", (fingerprint,))
            row = (fingerprint, 0, 0.0, 1)
        if row[0] != fingerprint:
            self.store.close()
            raise ValueError("Stored state belongs to different replay files; use a new database to start fresh")
        self._delivered = row[1]
        self.clock = MissionClock(start=row[2], speed=row[3], monotonic=monotonic)

    # ---- windows -------------------------------------------------------------
    def subscribe(self, window, callback):
        """Register a window callback for every pushed event. Returns an unsubscribe function."""
        if window not in WINDOWS:
            raise ValueError(f"window must be one of {WINDOWS}")
        token = object()
        with self._lock:
            self._subscribers[token] = callback
            self._sub_changed.notify_all()

        def unsubscribe():
            with self._lock:
                self._subscribers.pop(token, None)
        return unsubscribe

    def wait_for_subscribers(self, n, timeout=5):
        with self._lock:
            return self._sub_changed.wait_for(lambda: len(self._subscribers) >= n, timeout)

    def _push(self, message):
        for callback in list(self._subscribers.values()):
            try:
                callback(message)
            except Exception:  # one broken window must not stop the others
                pass

    def _push_and_detect(self, message):
        """Push an incoming event, then the Alerts, Triggers and Reading states detection makes from it."""
        annotate = getattr(self.detection, "annotate", None)  # Spec 2: a Trigger carries the HotSummary
        if annotate is not None:
            try:
                message = annotate(message)
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).exception("annotate failed; pushing the message as it is")
        self._push(message)
        for out in self._detected(self.detection and self.detection.on_message, message):
            self._push(out)

    def _detected(self, hook, arg):
        """What a detection hook makes from arg. A detection bug must never stop the feed: log it, make nothing."""
        if hook is None:
            return []
        try:
            return list(hook(arg))
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).exception("detection failed; continuing without its output")
            return []

    # ---- state -----------------------------------------------------------------
    def _save_state(self, commit=True):
        self.store.conn.execute("UPDATE service_state SET delivered = ?, mission_t = ?, speed = ? WHERE id = 1",
                                (self._delivered, self.clock.now(), self.clock.speed))
        if commit:
            self.store.conn.commit()

    # ---- playing -----------------------------------------------------------------
    def tick(self):
        """Deliver every pending replay event whose time has come, in time order."""
        with self._lock:
            now = self.clock.now()
            start, due = self._delivered, []
            try:
                i = start
                while i < len(self._queue) and self._queue[i][0] <= now:
                    message = self._queue[i][3]
                    if message["type"] == "reading":
                        self.store.add("reading", message["payload"], commit=False)
                    elif message["type"] in PROVISIONAL:
                        self.store.add(message["type"], message["payload"], commit=False)
                    due.append(message)
                    i += 1
                self._delivered = i
                self._save_state(commit=False)
                self.store.conn.commit()  # stored readings and progress land together, once per tick
            except BaseException:
                self.store.conn.rollback()
                self._delivered = start
                raise
            for message in due:
                self._push_and_detect(message)

    def skip(self):
        with self._lock:
            target = self.clock.skip_to_next_event(item[0] for item in self._queue[self._delivered:])
            self._save_state()
            return target

    def clock_status(self):
        with self._lock:
            return {"t": self.clock.now(), "speed": self.clock.speed, "label": self.clock.label}

    def set_speed(self, speed):
        with self._lock:
            self.clock.set_speed(speed)
            self._save_state()

    # ---- manual inputs -------------------------------------------------------------
    def post_reading(self, doc):
        with self._lock:
            self.store.add("reading", doc)
            self._push_and_detect({"t": doc["t"], "type": "reading", "payload": doc})

    def post_trigger(self, doc):
        with self._lock:
            validate("Trigger", doc)
            self._push_and_detect({"t": doc["t"], "type": "trigger", "payload": doc})

    def post_form(self, doc):
        """Spec 2: post-EVA form, meal or crew note (provisional CrewForm)."""
        self._post_provisional("form", doc)

    def post_location(self, doc):
        """Spec 2: a crew member moved to another cabin (provisional CrewLocation)."""
        self._post_provisional("location", doc)

    def _post_provisional(self, kind, doc):
        with self._lock:
            validate_provisional(kind, doc)
            self.store.add(kind, doc)
            self._push_and_detect({"t": doc["t"], "type": kind, "payload": doc})

    def hot_summary(self, crew_id):
        """Spec 2 HotSummary snapshot for one crew member (KeyError if unknown or no daily loop)."""
        with self._lock:
            if crew_id not in self._crew or not hasattr(self.detection, "hot_summary"):
                raise KeyError(crew_id)
            return self.detection.hot_summary(crew_id)

    def post_label(self, doc):
        with self._lock:
            self.store.add("label", doc)
            for out in self._detected(self.detection and self.detection.on_label, doc):
                self._push(out)

    def post_ground_reply(self, report):
        """Store a ground report that carries a reply, and store the reply as a Label."""
        with self._lock:
            validate("GroundReport", report)
            if "reply" not in report or "reply_t" not in report:
                raise ValueError("A ground reply needs reply and reply_t")
            try:  # report and its Label are stored together or not at all
                self.store.add("ground_report", report, commit=False)
                self.store.add("label", {"crew": report["crew"], "t": report["reply_t"], "kind": "ground_reply",
                                         "report": report}, commit=False)
                self.store.conn.commit()
            except BaseException:
                self.store.conn.rollback()
                raise
            self._push({"t": report["reply_t"], "type": "ground_reply", "payload": report})

    # ---- crew records -------------------------------------------------------------
    def crew_ids(self):
        return list(self._crew)

    def open_crew_record(self, crew_id, requester, emergency=False):
        """Own record always; another person's only in emergency mode, and every such opening is logged."""
        with self._lock:
            record = self._crew[crew_id]
            if requester != crew_id:
                if not emergency:
                    raise PermissionError("Another crew member's record opens only in emergency mode")
                self.store.add("access_log", {"crew": crew_id, "t": self.clock.now(), "opened_by": requester, "emergency": True})
            return copy.deepcopy(record)

    def close(self):
        """Save state and close the database. Safe to call more than once."""
        with self._lock:
            if getattr(self, "_closed", False):
                return
            self._save_state()
            self.store.close()
            self._closed = True


# ---- HTTP + SSE ---------------------------------------------------------------------

class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def shutdown(self):
        self.stopping.set()
        super().shutdown()


class _Handler(BaseHTTPRequestHandler):
    server_version = "StellarForgeHabitat/1"

    def log_message(self, *args):
        pass

    def _send(self, status, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _guarded(self, action):
        try:
            self._send(200, action())
        except PermissionError as exc:
            self._send(403, {"error": str(exc)})
        except KeyError as exc:
            self._send(404, {"error": f"not found: {exc}"})
        except ValueError as exc:  # includes ContractError and bad JSON
            self._send(400, {"error": str(exc)})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        svc = self.server.service
        if url.path == "/events":
            return self._stream(query.get("window", [""])[0])
        if url.path == "/clock":
            return self._send(200, svc.clock_status())
        if url.path.startswith("/crew/"):
            crew_id = url.path[len("/crew/"):]
            requester = query.get("requester", [""])[0]
            emergency = query.get("emergency", ["0"])[0] in ("1", "true")
            return self._guarded(lambda: svc.open_crew_record(crew_id, requester, emergency))
        if url.path.startswith("/hot_summary/"):
            crew_id = url.path[len("/hot_summary/"):]
            return self._guarded(lambda: svc.hot_summary(crew_id))
        self._send(404, {"error": "not found"})

    def do_POST(self):
        svc = self.server.service
        routes = {
            "/reading": svc.post_reading, "/trigger": svc.post_trigger, "/label": svc.post_label,
            "/ground_reply": svc.post_ground_reply, "/form": svc.post_form, "/location": svc.post_location,
            "/clock/speed": lambda body: svc.set_speed(body.get("speed")),
            "/clock/skip": lambda body: {"t": svc.skip()},
        }
        path = urlparse(self.path).path
        if path not in routes:
            return self._send(404, {"error": "not found"})
        def action():
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length > 0 else b""
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                raise ValueError("JSON body must be an object")
            return routes[path](body) or {"ok": True}
        self._guarded(action)

    def _stream(self, window):
        if window not in WINDOWS:
            return self._send(400, {"error": f"window must be one of {WINDOWS}"})
        inbox = queue.Queue()
        unsubscribe = self.server.service.subscribe(window, inbox.put)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            while not self.server.stopping.is_set():
                try:
                    message = inbox.get(timeout=0.5)
                    self.wfile.write(f"data: {json.dumps(message)}\n\n".encode("utf-8"))
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            unsubscribe()


def make_server(service, port=8765, tick_interval=0.1):
    """HTTP server on 127.0.0.1 only. With tick_interval set, a background thread plays the replays."""
    httpd = _Server(("127.0.0.1", port), _Handler)
    httpd.service = service
    httpd.stopping = threading.Event()
    if tick_interval:
        def ticker():
            while not httpd.stopping.wait(tick_interval):
                service.tick()
        threading.Thread(target=ticker, daemon=True).start()
    return httpd


def main(argv=None):
    parser = argparse.ArgumentParser(description="StellarForge habitat network service")
    parser.add_argument("--db", required=True)
    parser.add_argument("--replay", action="append", default=[], help="ReplayFile JSON (repeatable)")
    parser.add_argument("--crew", action="append", default=[], help="JSON file: one CrewRecord or a list (repeatable)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
    crew = []
    for path in args.crew:
        doc = load(path)
        crew.extend(doc if isinstance(doc, list) else [doc])
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.daily_loop import build_loop  # Spec 3 detection wrapped by the Spec 2 daily loop
    service = HabitatService(args.db, [load(p) for p in args.replay], crew, detection=build_loop(crew))
    httpd = make_server(service, port=args.port)
    print(f"Habitat network on http://127.0.0.1:{args.port} ({service.clock.label})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()
        service.close()


if __name__ == "__main__":
    main()
