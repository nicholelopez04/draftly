# Draftly

Draftly is a lightweight rich-text editor with a React and TipTap frontend and a FastAPI and SQLite backend.

## Windows PowerShell setup

Use Python 3.13 and Node.js 22.12 or newer. Run the following commands from the repository root in two separate PowerShell terminals.

### Backend

```powershell
Set-Location .\backend
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -3.13 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API runs at http://localhost:8000. FastAPI serves the interactive API documentation at http://localhost:8000/docs. Startup creates `backend/draftly.db` if needed and seeds Alex Morgan (ID 1) and Jordan Lee (ID 2). For an existing Phase 1 database, startup adds the sharing table and Jordan's user row in place. Alex keeps ownership of existing documents.

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
npm.cmd run lint
Pop-Location
```

The API tests use temporary SQLite databases. The frontend build outputs to `frontend/dist`.

## Using Draftly

1. Open **My Documents** and create a document, or open an existing one.
2. Select **Share** and give the other demo user read-only access.
3. Return to the dashboard, use **Switch demo user** in the sidebar, then open **Shared With Me**. The list and editor show the owner and a **Read Only** indicator.
4. To revoke access, switch back to the owner, reopen the document, and select **Share** → **Revoke access**.

The editor autosaves after a short pause. In-app navigation waits for pending changes to save. A failed save leaves the draft in the editor so you can retry. Blank titles save as “Untitled document.”

### Importing documents

Under **My Documents**, select **Import Document** and choose a UTF-8 `.txt` or `.md` file up to 1 MB (1,048,576 bytes). Draftly opens a new editable document owned by the active demo user and takes the title from the filename stem, trimming surrounding whitespace. Plain text keeps its line breaks. Markdown supports `#` and `##` headings, simple bold and italic spans, and flat bulleted and numbered lists. Imported HTML is kept as text. Advanced Markdown features such as tables, nested lists, and links have no special handling.

### Demo identity and access

Demo switching simulates identity using the `X-Demo-User-Id` request header. The backend validates that the ID belongs to a seeded demo user, but any client that can reach the API can supply either ID and act as that user. Run this demo locally with sample data. Access is checked on every API request, so after revocation the recipient loses access on the next request. Content they already loaded may remain visible in their open tab until they leave or reload.

## API

Send `X-Demo-User-Id: 1` or `X-Demo-User-Id: 2` on all requests below except `GET /health`.

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Check API availability. |
| `GET /demo-users` | List seeded demo users. |
| `GET /documents` | List owned and shared document summaries by most recent edit. |
| `POST /documents` | Create a document for the active user with an optional JSON title. |
| `POST /documents/import?filename=notes.md` | Import the raw file bytes with `Content-Type: application/octet-stream`. |
| `GET /documents/{id}` | Read metadata and TipTap JSON as the owner or a recipient. |
| `PATCH /documents/{id}` | Update the title, content, or both as the owner. |
| `GET /documents/{id}/shares` | List recipients as the owner. |
| `POST /documents/{id}/shares` | Grant read-only access as the owner with a JSON `user_id`. |
| `DELETE /documents/{id}/shares/{user_id}` | Revoke a recipient's access as the owner. |
