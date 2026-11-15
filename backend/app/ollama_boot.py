"""Start a local Ollama server when the explainer needs one and none is running.

Only ever for the default local address (127.0.0.1:11434). A remote host, another port
or SF_OLLAMA_AUTOSTART=0 is left alone. Failure is reported, never raised: the explainer
falls back to the recorded answers, so a missing Ollama must not stop the service.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_PORT = 11434
WAIT_S = 15.0
POLL_S = 0.3


@dataclass(frozen=True)
class OllamaStatus:
    status: str  # running | started | remote | unavailable
    detail: str = ""
    proc: object | None = None  # the process we started, so the service can stop it on exit


def is_reachable(url: str) -> bool:
    try:
        return httpx.get(f"{url}/api/tags", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


def _spawn(cmd: list[str]) -> subprocess.Popen:
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def ensure_ollama(
    url: str,
    reachable: Callable[[str], bool] = is_reachable,
    which: Callable[[str], str | None] = shutil.which,
    spawn: Callable[[list[str]], object] = _spawn,
    wait_s: float = WAIT_S,
    sleep: Callable[[float], None] = time.sleep,
    env: Mapping[str, str] = os.environ,
) -> OllamaStatus:
    if reachable(url):
        return OllamaStatus("running")
    parsed = urlparse(url)
    if parsed.hostname not in LOCAL_HOSTS:
        return OllamaStatus("remote", f"{url} is not local; start Ollama there yourself")
    if (parsed.port or DEFAULT_PORT) != DEFAULT_PORT:
        return OllamaStatus("unavailable", f"{url} is not the default local port; not starting Ollama")
    if env.get("SF_OLLAMA_AUTOSTART", "1") == "0":
        return OllamaStatus("unavailable", "auto-start is switched off (SF_OLLAMA_AUTOSTART=0)")
    binary = which("ollama")
    if not binary:
        return OllamaStatus("unavailable", "Ollama is not installed; using recorded answers")
    proc = spawn([binary, "serve"])
    waited = 0.0
    while waited < wait_s:
        if reachable(url):
            return OllamaStatus("started", proc=proc)
        sleep(POLL_S)
        waited += POLL_S
    return OllamaStatus("unavailable", f"Ollama did not answer within {wait_s:.0f} s; using recorded answers", proc)
