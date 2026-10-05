# DEVGUARD AI Repair Notes

## Root causes found

1. The deterministic test runner was capable of capturing stdout/stderr/exit code, but the investigation path did not make the deterministic evidence a first-class input for both directed and autonomous modes.
2. Directed mode relied too heavily on the Gemini tool loop instead of first collecting the same deterministic repository/test evidence used by autonomous mode.
3. Gemini response parsing only accepted one very specific fenced-JSON format. A valid JSON response without that exact markdown fence could be treated as an incomplete investigation.
4. Provider/API failures could be visually confused with an evidence failure.
5. The frontend used a generic Axios error message and had overly optimistic timeline state.
6. Configuration loading occurred after `Config` was imported, so configuration values could be stale when read at import time.
7. The project archive contained runtime workspaces/virtual environments and a secret-bearing `.env`/example file. These are excluded from the clean distribution.

## Corrected flow

Repository import
→ metadata detection
→ deterministic test execution
→ traceback/failure extraction
→ source/test inspection
→ structured evidence
→ Gemini reasoning
→ evidence-backed root cause
→ user approval
→ patch validation
→ final report/download

A Gemini/API failure is now surfaced as `PROVIDER_ERROR` instead of being disguised as `INSUFFICIENT_EVIDENCE`.

If Gemini cannot produce a valid evidence-backed conclusion, the UI still shows the deterministic test evidence and correctly reports that no root cause/patch was established.

## Local setup

1. Create a backend virtual environment.
2. Install `backend/requirements.txt`.
3. Copy `backend/.env.example` to `backend/.env`.
4. Put your own Gemini API key in `GEMINI_API_KEY`.
5. Keep `LLM_PROVIDER=gemini`.
6. Start the Flask backend using the project's existing startup command.
7. Start the Vite frontend with `npm install` and `npm run dev`.

Never commit or share `backend/.env`.
