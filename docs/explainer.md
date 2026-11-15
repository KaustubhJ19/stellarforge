# "Why this step?" — how the language model is used

For the write-up (Spec 5): **the language model only explains; published steps decide.**

- Steps come from a fixed, cited protocol file. The model never writes, edits or orders steps; the explainer has no write path to protocol data, and a test checks step text is unchanged after every call.
- The model sees only the current step and its source excerpts (keyword retrieval, no vector database, no web). The rescuer's question is passed as data, not instructions.
- Every answer is checked in code before it is shown: no drug names or doses, one short sentence, and most of its words must come from the retrieved text. The citation is attached by code, not by the model.
- If anything fails (no match, unsafe or ungrounded output, model slower than 5 s or not running) the screen shows a pre-written answer labelled "recorded answer", or "Not covered, ask ground."
- Model: llama3.2:3b on Ollama, local and offline. Measured: warm answer 0.3 s, cold start 4.35 s (`docs/spike-c.md`).

## Run it locally

The explainer needs a local Ollama server, and the backend starts one for you. On launch it checks `127.0.0.1:11434`; if nothing answers and `ollama` is installed, it runs `ollama serve`, waits for it, loads the model, and stops it again on exit (only if it started it). Without Ollama installed, "Why this step?" still works and shows the recorded answers.

```bash
ollama pull llama3.2:3b     # about 2 GB, once
python -m uvicorn app.main:app --app-dir backend --port 8000   # the log shows "Ollama: running" or "Ollama: started"
```

Auto-start applies only to the default local address. It is skipped for a remote `SF_OLLAMA_URL`, another port, or `SF_OLLAMA_AUTOSTART=0`.

Other models: `SF_OLLAMA_MODEL=llama3.1:8b` (any model you have pulled). Another host: `SF_OLLAMA_URL=http://host:11434`. Checked on 2026-11-15 with the real CPR protocol: warm answers in 0.6 to 0.8 s with `llama3.2:3b`, a question outside the protocol is refused without calling the model, and an ungrounded model answer falls back to the recorded answer.
