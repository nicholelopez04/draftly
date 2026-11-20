# Draftly

Draftly is a lightweight rich-text editor with a React and TipTap frontend and a FastAPI and SQLite backend. The local workspace is seeded for Alex Morgan.

## Windows PowerShell setup

Use Python 3.13 and Node.js 22.12 or newer. Run the following commands from the repository root in two separate PowerShell terminals.

### Backend

```powershell
Set-Location .\backend
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -3.13 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API runs at http://localhost:8000. FastAPI serves the interactive API documentation at http://localhost:8000/docs. The first startup creates `backend/draftly.db` and seeds Alex Morgan.

### Frontend

```powershell
Set-Location .\frontend
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    $env:Path = "C:\Program Files\nodejs;$env:Path"
}
npm.cmd ci
npm.cmd run dev
```

Open http://localhost:5173. Use this hostname for CORS. The frontend defaults to http://localhost:8000. Set `VITE_API_URL` before starting Vite if you change the API URL.

## Verification

From the repository root:

```powershell
Push-Location .\backend
.\.venv\Scripts\python.exe -m pytest
Pop-Location

Push-Location .\frontend
npm.cmd run build
Pop-Location
```

The API tests use temporary SQLite databases. The frontend build outputs to `frontend/dist`.

## API and editor behavior

- `GET /health` checks API availability.
- `GET /documents` lists document summaries by most recent edit.
- `POST /documents` accepts an empty JSON object or an optional title and creates an empty document.
- `GET /documents/{id}` returns document metadata and TipTap JSON.
- `PATCH /documents/{id}` accepts a title, content, or both.

The editor autosaves after a short pause. In-app navigation waits for pending changes to save. A failed save leaves the draft in the editor so you can retry. Blank titles save as “Untitled document.”

Phase 1 uses a single demo identity without authentication. Sharing, uploads, live collaboration, and cross-tab conflict resolution are outside this phase.
