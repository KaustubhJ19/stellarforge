"""Spike C (ticket 01): does a small local model answer a short question in under 5 s?

Usage: python tools/spike_ollama.py [--model llama3.2:3b] [--runs 5]
Talks only to the local Ollama server (http://localhost:11434).
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time

import httpx

URL = "http://localhost:11434"
TARGET_S = 5.0
# Non-clinical question shaped like a "Why this step?" call.
PROMPT = (
    "Answer in one sentence using only this excerpt.\n"
    "Excerpt: STUB excerpt for step 2. Placeholder text explaining why stub equipment A is used.\n"
    "Question: Why this step?"
)


def ask(client: httpx.Client, model: str, keep_alive="5m") -> tuple[float, str]:
    t0 = time.perf_counter()
    r = client.post(f"{URL}/api/generate", json={
        "model": model, "prompt": PROMPT, "stream": False, "keep_alive": keep_alive,
        "options": {"temperature": 0, "num_predict": 60},
    })
    r.raise_for_status()
    return time.perf_counter() - t0, r.json().get("response", "").strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="llama3.2:3b")
    p.add_argument("--runs", type=int, default=5)
    a = p.parse_args()
    with httpx.Client(timeout=120) as c:
        version = c.get(f"{URL}/api/version").json()["version"]
        c.post(f"{URL}/api/generate", json={"model": a.model, "keep_alive": 0})  # unload -> true cold start
        time.sleep(1)
        cold, sample = ask(c, a.model)
        warm = [ask(c, a.model)[0] for _ in range(a.runs)]
    med = statistics.median(warm)
    result = {
        "model": a.model, "ollama": version, "host": platform.platform(),
        "cold_s": round(cold, 2), "warm_s": [round(w, 2) for w in warm],
        "warm_median_s": round(med, 2), "warm_max_s": round(max(warm), 2),
        "target_s": TARGET_S, "decision": "GO" if max(warm) < TARGET_S else "NO-GO",
        "cold_under_target": cold < TARGET_S, "sample_answer": sample,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
