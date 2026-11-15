"""Investigator model comparison and ship gate (Spec 3, ticket 14).

Usage: PYTHONPATH=backend python tools/eval_investigator.py [--models qwen2.5:3b llama3.2:3b] [--write]
Runs the fixed fake-fixture question set against local Ollama models only. `--write` stores the measured numbers in
content/copilot/investigator-eval.json; it never edits the config, so a person decides `enabled`.
A model that is not installed is reported and skipped, never invented.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.explainer import ollama_transport  # noqa: E402
from copilot.investigator import SYSTEM, TIME_BOX_S  # noqa: E402
from copilot.investigator_eval import RESULTS_PATH, evaluate, gate_passes, pick_model  # noqa: E402

URL = "http://127.0.0.1:11434"


def installed() -> set[str]:
    return {m["name"] for m in httpx.get(f"{URL}/api/tags", timeout=5).json()["models"]}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=["qwen2.5:3b", "llama3.2:3b"])
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    try:
        have = installed()
    except httpx.HTTPError as err:
        print(f"Ollama unreachable at {URL}: {err}. Nothing measured.")
        return 2
    results, skipped = [], []
    for model in a.models:
        if model not in have:
            skipped.append(model)
            print(f"{model}: not installed, skipped")
            continue
        t = ollama_transport(model, URL, timeout=TIME_BOX_S, system=SYSTEM, num_predict=400, json_mode=True)
        try:  # warm-up so model load time is not charged to the 20 s time box
            httpx.post(f"{URL}/api/generate", timeout=120, json={"model": model, "keep_alive": "30m"})
        except httpx.HTTPError as err:
            print(f"{model}: warm-up failed ({err}), skipped")
            skipped.append(model)
            continue
        r = evaluate(t)
        results.append(r)
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}))
    best = pick_model(results)
    out = {"picked": best["model"] if best else None, "skipped_not_measured": skipped,
           "gate": {r["model"]: gate_passes(r) for r in results}, "results": results}
    print("picked:", out["picked"], "| gate:", out["gate"])
    if a.write:
        RESULTS_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
