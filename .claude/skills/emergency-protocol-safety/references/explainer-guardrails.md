# Explainer guard rails (ticket 11)

The explainer is a closed-corpus retrieval answerer. Treat the model as untrusted: check its output in code.

## Pipeline

1. **Retrieve** by keyword over protocol step text + source excerpts only. No vector DB, no other corpus, no web.
2. **No match → "Not covered, ask ground."** Don't call the model.
3. **Prompt** with the retrieved excerpts only, ask for one sentence and the section it relies on. Keep the system prompt fixed; user text goes in a clearly delimited field and is never concatenated into instructions.
4. **Check output in code** before showing it:
   - cited section ∈ retrieved sections (don't trust the model's citation);
   - passes the linter's drug-name and dose checks;
   - is one short answer (cap length);
   - any failure → "Not covered, ask ground."
5. **Timeout 5 s / Ollama down** → recorded answer (labelled "recorded answer") or "Not covered, ask ground."
6. **Read-only**: the endpoint has no write path to protocol data.

## Prompt-injection notes

- Inputs that can carry injected text: the rescuer's free-text question (if allowed — open ambiguity), protocol excerpts (trusted, linted), nothing else.
- Instructions inside the question ("ignore previous", "give the dose") must not change behaviour; the code checks in step 4 are the real defence, not the prompt.
- Never let model output pick which step is shown next, or write to Labels, records or logs.

## Fallback if retrieval is unreliable

Restrict to exact step-text lookup for the current step and refuse everything else (spec, Spike go/no-go).
