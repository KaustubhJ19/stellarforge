# Backup demo recording (ticket 09)

**Video:** [`docs/media/backup-demo-2026-11-15.webm`](media/backup-demo-2026-11-15.webm) (recorded 2026-11-15, 8.8 MB).

A one-take screen recording of the real app with real content, in case the live demo fails:
home screen → collapse → guidance → ground report → delayed ground reply.

- **Content:** protocol `microgravity-cpr`, profile `mars_transit`, crew A–D from `replay/crew-records.json`.
- **Collapse:** Spec 3 detection run over Spec 1's crew B emergency replay. It raises an auto Trigger at the unstable ventricular tachycardia and an emergency Alert (ACT NOW, no likely causes). `tools/demo/demo_collapse.py` saves those two messages, and the recording posts them to the Spec 4 app.
- **Offline:** the explainer is off, so "Why this step?" shows the recorded answer. The browser contacts only 127.0.0.1.
- **On screen:** each scene has a caption that says what is happening and where it comes from.

## Re-record (macOS or Linux)

Needs `frontend/node_modules` (`cd frontend && npm ci && npx playwright install chromium`), a built app (`npx vite build` in `frontend/`) and `.venv` with the backend packages.

```bash
mkdir -p out
.venv/bin/python tools/demo/demo_collapse.py out/collapse.json
cd frontend && SF_PROTOCOL=microgravity-cpr SF_PROFILE=mars_transit SF_RECORDS=$PWD/../replay/crew-records.json SF_OLLAMA_URL=http://127.0.0.1:9 ../.venv/bin/python -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8771 &
cd .. && node tools/demo/record_demo.mjs http://127.0.0.1:8771 out/collapse.json out
```

The video (`out/page@*.webm`, about 2 minutes, 1280×800) and one screenshot per scene (`out/s01.png` …) land in `out/`.
