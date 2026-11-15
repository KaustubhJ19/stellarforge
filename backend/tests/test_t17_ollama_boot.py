"""Auto-start of a local Ollama server, so live explainer answers need no manual step."""
from app.ollama_boot import ensure_ollama

LOCAL = "http://127.0.0.1:11434"


class FakeProc:
    def __init__(self):
        self.terminated = False

    def terminate(self):
        self.terminated = True


def run(url=LOCAL, up_after=None, binary="/usr/local/bin/ollama", autostart="1", env=None):
    """up_after: how many reachability checks fail before the server answers (None: already up)."""
    checks = {"n": 0}
    started = []

    def reachable(_url):
        checks["n"] += 1
        return up_after is None or checks["n"] > up_after

    result = ensure_ollama(
        url, reachable=reachable, which=lambda _name: binary,
        spawn=lambda cmd: started.append(cmd) or FakeProc(),
        wait_s=1.0, sleep=lambda _s: None, env={"SF_OLLAMA_AUTOSTART": autostart, **(env or {})},
    )
    return result, started


def test_already_running_is_left_alone():
    result, started = run(up_after=None)
    assert result.status == "running" and started == [] and result.proc is None


def test_not_running_is_started_and_waited_for():
    result, started = run(up_after=3)
    assert result.status == "started" and started == [["/usr/local/bin/ollama", "serve"]]
    assert isinstance(result.proc, FakeProc)


def test_never_comes_up_is_reported_not_raised():
    result, _ = run(up_after=10_000)
    assert result.status == "unavailable" and "did not answer" in result.detail


def test_ollama_not_installed_is_reported():
    result, started = run(up_after=10_000, binary=None)
    assert result.status == "unavailable" and "not installed" in result.detail and started == []


def test_remote_host_is_never_started():
    result, started = run(url="http://gpu-box:11434", up_after=10_000)
    assert result.status == "remote" and started == []


def test_non_default_local_port_is_never_started():
    result, started = run(url="http://127.0.0.1:9", up_after=10_000)  # e2e points at a closed port on purpose
    assert result.status == "unavailable" and started == []


def test_can_be_switched_off():
    result, started = run(up_after=10_000, autostart="0")
    assert result.status == "unavailable" and "switched off" in result.detail and started == []
