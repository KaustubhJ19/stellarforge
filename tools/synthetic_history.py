"""Synthetic glucose, meal, EVA and location timelines for demos and tests (Spec 2; shared with Spec 3).

Label: "synthetic history, estimate". Not measured on anyone. Shapes: glucose Readings (source "sim"),
CrewForm events (meal, note, post_eva) and CrewLocation events (contracts/provisional/), so they play through
the habitat service like any replay. Seeded, so the same arguments always give the same events.

  python tools/synthetic_history.py --crew A --days 30 --out replay/generated/synthetic-A.json
"""
import argparse
import json
import random
from pathlib import Path

LABEL = "synthetic history, estimate"
DAY, HOUR = 86_400, 3_600
SCHEMA_VERSION = "1.0.0"
MEALS = [("breakfast", 7, 450), ("lunch", 12, 700), ("dinner", 18, 650)]  # demo pattern, not a diet


def events(crew, days, seed=0, start_day=0, eva_every_days=10, glucose_per_day=2):
    rng = random.Random(f"{crew}-{seed}")
    out = [{"t": start_day * DAY, "type": "location", "payload": {"crew": crew, "cabin": "habitat", "t": start_day * DAY}}]
    for d in range(start_day, start_day + days):
        base = d * DAY
        for name, hour, kcal in MEALS:
            t = base + hour * HOUR + rng.randint(0, 1800)
            out.append({"t": t, "type": "form", "payload": {"crew": crew, "form": "meal", "t": t,
                                                             "answers": {"description": f"{name} ({LABEL})", "kcal": kcal + rng.randint(-80, 80)}}})
        for k in range(glucose_per_day):
            t = base + (6 + 8 * k) * HOUR + rng.randint(0, 900)
            out.append({"t": t, "type": "reading", "payload": {"crew": crew, "indicator": "glucose", "value": round(rng.gauss(95, 8), 1),
                                                                "unit": "mg/dL", "t": t, "source": "sim", "confidence": 0.5, "state": "released"}})
        if eva_every_days and d > start_day and (d - start_day) % eva_every_days == 0:
            out_t, end_t = base + 9 * HOUR, base + 15 * HOUR
            out.append({"t": out_t, "type": "location", "payload": {"crew": crew, "cabin": "eva", "t": out_t}})
            out.append({"t": end_t, "type": "location", "payload": {"crew": crew, "cabin": "habitat", "t": end_t}})
            t = end_t + HOUR
            out.append({"t": t, "type": "form", "payload": {"crew": crew, "form": "post_eva", "t": t,
                                                             "answers": {"eva_end_t": end_t, "fatigue": rng.randint(1, 5), "note": LABEL}}})
    return sorted(out, key=lambda e: e["t"])


def replay(crew, days, profile="mars_transit", **kw):
    return {"schema_version": SCHEMA_VERSION, "crew": crew, "profile": profile, "label": LABEL, "events": events(crew, days, **kw)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--crew", required=True)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(replay(a.crew, a.days, seed=a.seed), indent=1), encoding="utf-8")
    print(f"wrote {a.out} ({LABEL})")


if __name__ == "__main__":
    main()
