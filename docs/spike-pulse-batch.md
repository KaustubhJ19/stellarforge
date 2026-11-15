# Spike: Pulse batch runs (Collapse Copilot ticket 03)

Decision: **GO on macOS**. Pulse built from source and ran here, from the Python API, with no paid tools. Measured 2026-11-15 on one Mac (Apple M5, 10 cores = 4 performance + 6 efficiency, 16 GB, macOS 27.0.1 arm64).

Not yet checked: the Windows dev laptop (RTX 4060, the Spike C machine). Pulse supports Windows, but nothing below was measured there. Re-run `tools/spike_pulse.py` on it before fixing run counts.

## What was installed

| Item | Value |
|---|---|
| Pulse | 4.4.0 (tag `REL_4_4_0`), Apache-2.0, from `gitlab.kitware.com/physiology/engine` |
| Python API | Built in (`PyPulse`, `PulseEngine`, `PulseScenarioExec`); runs under Python 3.12 only (the build links the interpreter it was configured with, so the repo's Python 3.13 cannot import it) |
| Extra tools (all free) | `brew install cmake openjdk ninja`; `uv venv --python 3.12` |
| Build | CMake superbuild, Release, `-DPulse_PYTHON_API=ON -DPulse_JAVA_API=ON -DPulse_GEN_DATA=ON`; 288 s wall, install is 479 MB |
| Where | Scratch directory outside the repo. No Pulse files are committed. |

Pulse is **not on PyPI**: `pip index versions` found no `pulse-engine`, `pulse-physiology` or similar. It has to be built from source. Releases on GitLab carry source only.

Build recipe that worked:

```bash
curl -L -o engine.tar.gz https://gitlab.kitware.com/physiology/engine/-/archive/REL_4_4_0/engine-REL_4_4_0.tar.gz
mkdir src && tar xzf engine.tar.gz -C src --strip-components=1
uv venv --seed --python 3.12 .venv && .venv/bin/pip install -r src/requirements.txt
export JAVA_HOME=/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home PATH=$JAVA_HOME/bin:$PATH VIRTUAL_ENV=$PWD/.venv
cmake -S src -B build -DCMAKE_BUILD_TYPE=Release -DPulse_PYTHON_HOME_DIR=$PWD/.venv \
  -DPython3_FIND_VIRTUALENV=ONLY -DPulse_JAVA_API=ON -DPulse_PYTHON_API=ON -DPulse_GEN_DATA=ON
cmake --build build -j 10          # Python API ends up in build/install/{bin,python}
```

Gotchas: Pulse needs CMake 3.31 or newer (its `CMakeLists.txt` says so; the README's "3.12" is stale). Homebrew's JDK is keg-only, so `JAVA_HOME` must point at `libexec/openjdk.jdk/Contents/Home` or CMake fails with "Could NOT find JNI".

## One scenario, end to end

`tools/spike_pulse.py` loads a pre-stabilized patient state, applies a RightLeg hemorrhage (severity 0.8, as in Pulse's `HowTo_Hemorrhage`), and advances 600 simulated seconds. Sanity check on StandardMale: heart rate 72.0 to 107.1 /min, mean arterial pressure 95.3 to 84.1 mmHg. So the runs are real physiology, not no-ops.

## Measured timings (600 s simulated, hemorrhage, fresh process per worker)

| Workers | Scenarios | Per-scenario wall (min / median / max) | Batch wall | Throughput |
|---|---|---|---|---|
| 1 | 3 | 12.79 / 12.96 / 13.17 s | 39.2 s | 13.06 s per scenario |
| 4 | 12 | 13.88 / 15.71 / 15.96 s | 46.5 s | 3.87 s per scenario |
| 8 | 24 | 22.08 / 22.68 / 23.37 s | 69.9 s | 2.91 s per scenario |

Other measured pieces:

- Loading a stabilized state: 0.04 s.
- Creating a **new** patient (custom age and weight, `initialize_engine`, includes stabilization): 8.6 s and 7.6 s (n = 2, single process, idle machine).
- A 60 s simulation took about 1.3 s (n = 2).

Reading the table: going from 4 to 8 workers gained only about 33 % throughput, because per-scenario time rose from about 16 s to about 23 s. The M5 has 4 fast and 6 slow cores, so more workers than fast cores helps less. The team's Windows laptop will differ.

## Run counts (arithmetic on the measured numbers above)

If Pulse generation gets about 30 minutes of the 1 to 2 hour pipeline (a team choice, not measured):

| Setup | Scenarios in 30 min |
|---|---|
| 4 workers, 3.87 s each | about 465 |
| 8 workers, 2.91 s each | about 618 |

Recommendation: plan for **about 400 scenarios** of 600 simulated seconds as the default Pulse set, which leaves headroom on this machine, and scale to the 500 to 600 range only after re-timing on the machine that will run the pipeline. That is small for the spec's wide parameter sweep, which is why the next points matter.

## What was not measured (do not quote numbers for these)

- **Parallel cost of new patients.** The table uses pre-stabilized states. The spec varies sex, age, weight, height, resting HR and BP, so many scenarios need their own patient. Each new patient costs about 8 s serial (n = 2); how that behaves with 8 workers running was not measured. Mitigation: stabilize each patient once, save the state with `SESerializeState`, then branch several severities and onsets from it.
- **Other conditions.** Only hemorrhage was timed. Other simulatable conditions (for example tension pneumothorax, sepsis, arrhythmia) may be slower or faster, and some may fail to stabilize at extreme parameters.
- **ScenarioDriver.** `PulseScenarioDriver` was built (`build/install/bin`) but not timed. The Python `PulseScenarioExec` batch path from `HowTo_BatchRun.py` was also not timed. The per-process Python API above is enough for the ticket; the batch executor may be faster or easier to resume.
- **Windows and Linux.** Not tried.
- Build time (288 s) comes from the machine clock around one build; one run only.

## Fallback options if Pulse cannot run on the pipeline machine

Not needed on this Mac, but the team machine is unproven.

1. **Build on one machine, share the install.** Only one teammate needs the toolchain. Run the batch there and commit or share only the output rows plus the dataset manifest (spec step 6 already records Pulse version and file hashes).
2. **Docker.** Pulse ships a `Dockerfile` in its source; `docker` is present on this Mac but was not tried.
3. **Pulse's own prebuilt Windows PulseExplorer bundle** (what the team uses today) for fewer, hand-driven runs. Not scriptable at batch scale.
4. **Drop to "priors and cited signs only"** for the affected conditions, labelled as the spec already requires for conditions Pulse cannot simulate (user story 24). This is the safe floor if no machine can run Pulse.

## Re-run

```bash
python3.12 tools/spike_pulse.py --install-dir /path/to/pulse/build/install --runs 3 --sim-seconds 600 --workers 1,4,8
```

Use the same Python version Pulse was built with.
