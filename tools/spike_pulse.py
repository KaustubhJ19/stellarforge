"""Spike (collapse-copilot ticket 03): can Pulse run batches here, and how fast?

Usage (needs a Pulse build with the Python API, see docs/spike-pulse-batch.md):
    python tools/spike_pulse.py --install-dir /path/to/pulse/build/install \
        --runs 5 --sim-seconds 600 --workers 1,4,8

Times one scenario = load a patient state, apply a hemorrhage, advance
`--sim-seconds` of simulated time, in a fresh process per pool worker.
Prints measured wall seconds only; nothing is estimated.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import platform
import statistics
import sys
import time

STATES = ["StandardMale@0s.json", "StandardFemale@0s.json", "Soldier@0s.json", "Jane@0s.json"]
SEVERITY = 0.8  # fraction, RightLeg hemorrhage (as in Pulse's HowTo_Hemorrhage)


def run_one(args: tuple[str, str, int]) -> float:
    install_dir, state, sim_seconds = args
    sys.path[:0] = [os.path.join(install_dir, "python"), os.path.join(install_dir, "bin")]
    os.chdir(os.path.join(install_dir, "bin"))
    from pulse.cdm.engine import SEDataRequest, SEDataRequestManager
    from pulse.cdm.patient_actions import SEHemorrhage, eHemorrhage_Compartment
    from pulse.cdm.scalars import FrequencyUnit, PressureUnit
    from pulse.engine.PulseEngine import PulseEngine

    t0 = time.perf_counter()
    engine = PulseEngine()
    engine.log_to_console(False)
    requests = SEDataRequestManager([
        SEDataRequest.create_physiology_request("HeartRate", unit=FrequencyUnit.Per_min),
        SEDataRequest.create_physiology_request("MeanArterialPressure", unit=PressureUnit.mmHg),
    ])
    if not engine.serialize_from_file(f"./states/{state}", requests):
        raise RuntimeError(f"could not load state {state}")
    hemorrhage = SEHemorrhage()
    hemorrhage.set_compartment(eHemorrhage_Compartment.RightLeg.name)
    hemorrhage.get_severity().set_value(SEVERITY)
    engine.process_action(hemorrhage)
    engine.advance_time_s(sim_seconds)
    return time.perf_counter() - t0


def summarize(label: str, times: list[float]) -> None:
    print(f"{label}: n={len(times)} min={min(times):.2f}s median={statistics.median(times):.2f}s "
          f"max={max(times):.2f}s")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--install-dir", required=True)
    p.add_argument("--runs", type=int, default=5, help="scenarios per worker")
    p.add_argument("--sim-seconds", type=int, default=600)
    p.add_argument("--workers", default="1,4", help="comma-separated process counts to batch with")
    a = p.parse_args()

    print(f"{platform.platform()} {platform.machine()} cpus={os.cpu_count()} python={platform.python_version()}")
    ctx = mp.get_context("spawn")  # fresh interpreter per worker; no shared engine state
    for workers in (int(w) for w in a.workers.split(",")):
        jobs = [(a.install_dir, STATES[i % len(STATES)], a.sim_seconds) for i in range(a.runs * workers)]
        t0 = time.perf_counter()
        with ctx.Pool(workers) as pool:
            per_run = pool.map(run_one, jobs)
        wall = time.perf_counter() - t0
        summarize(f"workers={workers} per-scenario", per_run)
        print(f"workers={workers} batch: {len(jobs)} scenarios in {wall:.1f}s "
              f"= {wall / len(jobs):.2f}s per scenario throughput")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
