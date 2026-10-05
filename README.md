<div align="center">

# DEVGUARD AI

### Evidence-first autonomous debugging for real repositories

Import a Git repository or ZIP archive, reproduce the failure, collect deterministic evidence, and let Gemini reason over the smallest useful evidence set before proposing a safe fix.

<br />

![Flask](https://img.shields.io/badge/backend-Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Gemini](https://img.shields.io/badge/reasoning-Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)

</div>

---

## Why DEVGUARD AI?

Traditional AI debugging workflows often spend expensive model calls rediscovering facts that deterministic tools can establish immediately. DEVGUARD AI uses a different approach:

1. **Run tests first.**
2. **Extract failures, assertions, expected/actual values, and tracebacks.**
3. **Identify the failing tests and affected source files.**
4. **Prioritize executable evidence over documentation.**
5. **Ask Gemini to reason only after the evidence package is ready.**
6. **Require evidence-backed root-cause claims.**
7. **Keep patch application behind explicit user approval.**

The result is a genuinely autonomous debugging agent with a smaller, higher-value Gemini context and fewer unnecessary API calls.

## Features

- Import repositories from a Git URL or ZIP upload
- Automatic repository metadata detection
- Autonomous or directed investigation modes
- Deterministic test execution before LLM reasoning
- Evidence extraction from failing tests and tracebacks
- High-priority source selection through failing-test imports
- Evidence-aware tool loop with duplicate-read prevention
- Documentation gating for low-value files such as `README.md` and `WORKSHOP.md`
- Gemini function calling through the existing provider abstraction
- Proposed full-file patches without modifying the repository during investigation
- Patch validation after approval
- Diff preview, downloadable patch, and fixed-repository ZIP export
- Generated Markdown investigation reports
- React dashboard for the complete investigation workflow

---

## Architecture

```text
┌──────────────────────┐
│  React + Vite UI     │
│  Repository import   │
│  Investigation view  │
└──────────┬───────────┘
           │ HTTP / JSON
           ▼
┌──────────────────────┐
│  Flask API           │
│  Repository manager  │
│  Validation pipeline │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Deterministic layer  │
│ Tests • files • git  │
│ evidence prioritizer │
└──────────┬───────────┘
           │ structured evidence
           ▼
┌──────────────────────┐
│ Gemini provider      │
│ Reasoning + tools    │
│ JSON investigation   │
└──────────────────────┘
```

### Evidence priority

| Priority | Evidence |
| --- | --- |
| **High** | Failing test files, traceback-referenced files, affected source files, direct imports/functions |
| **Medium** | Git history and diffs when they clarify the failure |
| **Low** | `README.md`, `WORKSHOP.md`, general documentation, unrelated files |

Low-priority documentation is not read merely because it exists. It is considered only when executable evidence cannot resolve an ambiguity or the bug report explicitly references it.

---

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── agent/          # Provider abstraction and investigation loop
│   │   ├── repository/     # Workspace ingestion and metadata detection
│   │   ├── tools/          # Testing, repository, Git, and patch tools
│   │   ├── config.py       # Environment-backed configuration
│   │   └── main.py         # Flask API routes
│   ├── tests/              # Backend test suite
│   ├── requirements.txt
│   └── .env                # Local secrets and runtime configuration
├── frontend/
│   ├── src/
│   │   ├── components/     # Dashboard UI
│   │   └── api/            # Backend API client
│   └── package.json
├── skills/                 # Investigation and reporting guidance
├── docs/                   # Project notes
└── README.md
```

---

## Requirements

- Python 3.13 or newer
- Node.js 20 or newer
- npm
- A Gemini API key

The backend dependencies are pinned in [`backend/requirements.txt`](backend/requirements.txt). The frontend dependencies and scripts are defined in [`frontend/package.json`](frontend/package.json).

---

## Quick start

### 1. Configure the backend

From PowerShell:

```powershell
cd backend
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create `backend\.env` locally:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=replace-with-your-key
GEMINI_MODEL=gemini-1.5-flash
MAX_TOOL_CALLS=6
```

Never commit a real API key. Keep secrets in local environment files or a secret manager.

### 2. Start the Flask API

In the `backend` directory:

```powershell
$env:FLASK_APP = "app:create_app()"
flask run --port 5001
```

The API is available at `http://127.0.0.1:5001`.

### 3. Start the React dashboard

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

The frontend expects the Flask API at `http://127.0.0.1:5001`. If your local frontend configuration uses a different API URL, update the frontend API client accordingly.

---

## Investigation workflow

1. **Import a repository** using a Git URL or ZIP archive.
2. **Select a mode**:
   - **Autonomous**: discover failures and likely causes without a report.
   - **Directed**: investigate a specific bug report.
3. **Run investigation**.
4. DEVGUARD deterministically runs the repository test command.
5. The evidence collector records failures, tracebacks, assertions, and relevant files.
6. Gemini receives the evidence package and may call deterministic tools when ambiguity remains.
7. The result includes a status, confidence, root cause, evidence, and proposed patch.
8. Review the diff and explicitly approve validation.
9. Download the report, patch, or validated repository.

Investigation does not modify the repository. Patch validation is a separate approval step.

---

## API reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health check |
| `POST` | `/repositories/import` | Import a repository from `{ "git_url": "..." }` |
| `POST` | `/repositories/upload` | Upload a `.zip` repository |
| `GET` | `/repositories/<repo_id>/metadata` | Read detected repository metadata |
| `POST` | `/investigate` | Start autonomous or directed investigation |
| `POST` | `/fix/approve` | Validate an approved proposed patch |
| `GET` | `/investigations/<repo_id>/patch` | Download the current patch |
| `GET` | `/investigations/<repo_id>/download` | Download the repository as a ZIP |
| `POST` | `/tools/search` | Search repository contents |
| `POST` | `/tools/test` | Run the detected test command |
| `POST` | `/tools/apply` | Apply a patch through the patching tool |
| `POST` | `/tools/revert` | Revert a previously applied patch |

Example directed investigation:

```powershell
curl.exe -X POST http://127.0.0.1:5001/api/investigate `
  -H "Content-Type: application/json" `
  -d '{ "repository": "ws_example", "mode": "directed", "bug_report": "Orders totals are incorrect for empty carts." }'
```

---

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `gemini` | Selects the configured LLM provider |
| `GEMINI_API_KEY` | — | Gemini API credential |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `MAX_TOOL_CALLS` | `12` | Maximum agent tool-loop iterations |
| `FLASK_ENV` | — | Flask runtime environment |

`MAX_TOOL_CALLS` remains configurable. DEVGUARD does not disable tools or reduce the agent to a mock workflow; it reduces waste by front-loading deterministic evidence and enforcing an evidence budget.

---

## Testing

### Backend

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
```

### Frontend

```powershell
cd frontend
npm run lint
npm run build
```

---

## Safety principles

DEVGUARD AI is designed to make debugging more evidence-based, not less controlled:

- Never claim a root cause without supporting evidence.
- Never claim tests passed without actual test output.
- Never fabricate tool results, files, tracebacks, or Git history.
- Never modify the repository during investigation.
- Keep patch application and validation behind explicit approval.
- Treat API credentials as local secrets.

---

## License

No license file is currently included in this repository. Add a `LICENSE` file before distributing DEVGUARD AI publicly.

