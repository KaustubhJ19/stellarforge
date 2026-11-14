# Spike C — local explainer model latency (ticket 01)

Decision: **GO** (live model), measured 2026-11-15 on the dev laptop (Windows 11, RTX 4060 Laptop 8 GB).

| Item | Value |
|---|---|
| Runtime | Ollama 0.40.16, local HTTP API on localhost:11434 |
| Model | llama3.2:3b (2.0 GB, 100% GPU) |
| Cold start (model unloaded) | 4.35 s |
| Warm, 5 runs | 0.31, 0.30, 0.30, 0.30, 0.31 s (median 0.30 s) |
| Target | < 5 s → met warm and cold |

Re-run: `backend/.venv/Scripts/python tools/spike_ollama.py --runs 5`

Notes
- Cold start is close to the limit (4.35 s): the backend pre-loads the model at start-up (ticket 14) so the first "Why?" press is warm.
- **Network-off not physically tested**: the spike only calls `localhost`; a run with Wi-Fi off must be done on the rehearsal machine (ticket 16).
- The sample answer added claims not in the excerpt ("temporary solution…"). This confirms the explainer must check model output against the retrieved text in code, and fall back to "Not covered, ask ground." when it doesn't hold (ticket 11).
- Fallback if this ever regresses: pre-written answers labelled "recorded answer" (spec, Spike go/no-go).
