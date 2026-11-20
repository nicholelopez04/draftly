# Draftly

Draftly is a lightweight rich-text editor with a React and TipTap frontend and a FastAPI backend. It uses SQLite locally and hosted PostgreSQL on Render.

**Use synthetic data only.** Demo-user switching is not real authentication. Anyone who can reach the API can impersonate Alex or Jordan by setting the demo-user header and can read or change data as that user. CORS controls which browser origins can read API responses, and direct API clients can still reach the service.

## Windows PowerShell setup

Use Python 3.13 and Node.js 22.12 or newer. Run the following commands from the repository root in two separate PowerShell terminals.

### Backend

```powershell
Set-Location .\backend
if (-not (Test-Path .\.venv\Scripts\python.exe)) { py -3.13 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API runs at http://localhost:8000. FastAPI serves the interactive API documentation at http://localhost:8000/docs. With `DATABASE_URL` unset, startup creates `backend/draftly.db` if needed and seeds Alex Morgan (ID 1) and Jordan Lee (ID 2). For an existing Phase 1 database, startup adds the sharing table and Jordan's user row in place. Alex keeps ownership of existing documents.

For optional backend overrides, set `$env:DATABASE_URL` and/or `$env:CORS_ALLOWED_ORIGINS` in the backend PowerShell terminal before starting Uvicorn. The plain Uvicorn command above reads the process environment. Use `backend/.env.example` as a template for the variable names.

### Frontend

```powershell
Set-Location .\frontend
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    $env:Path = "C:\Program Files\nodejs;$env:Path"
}
npm.cmd ci
npm.cmd run dev
```

Open http://localhost:5173. The frontend defaults to http://localhost:8000. To override it, copy `frontend/.env.example` to `frontend/.env.local` and edit `VITE_API_BASE_URL` before starting Vite. The previous `VITE_API_URL` variable still works as a fallback. Real `.env` files are gitignored.

## Deploy the hosted demo

### Render API and PostgreSQL

1. Create an empty Render PostgreSQL database and a Python Web Service in the same account and region. Connect the web service to this repository.
2. Configure the web service as follows.

   | Setting | Value |
   | --- | --- |
   | Runtime | Python 3 |
   | Root Directory | `backend` |
   | Build Command | `python -m pip install -r requirements.txt` |
   | Start Command | `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Health Check Path | `/health` |
   | `PYTHON_VERSION` | `3.13.17` |
   | `DATABASE_URL` | The database's Internal Database URL, stored in Render's Environment settings |
   | `CORS_ALLOWED_ORIGINS` | The exact Vercel production origin, for example `https://your-draftly.vercel.app` |

3. Deploy the web service and record its public HTTPS URL. If the Vercel domain is assigned later or changes, update the allowed origins and redeploy the API. Use a comma-separated list for additional exact origins, such as a custom domain or a specific preview URL.

Render supplies `RENDER=true` and `PORT`. On Render, invalid or missing database or CORS configuration stops startup. For a PostgreSQL provider outside Render, use its connection URL and retain its TLS options. The database role needs permission to create the initial tables and indexes in its target schema.

[Render FastAPI setup](https://render.com/docs/deploy-fastapi) · [Render PostgreSQL connection details](https://render.com/docs/postgresql-creating-connecting) · [Render health checks](https://render.com/docs/health-checks)

### Vercel frontend

1. Import the same repository into Vercel. Set **Root Directory** to `frontend` and **Framework Preset** to **Vite**.
2. Set **Node.js Version** to **22.x**, **Install Command** to `npm ci`, **Build Command** to `npm run build`, and **Output Directory** to `dist`.
3. Set `VITE_API_BASE_URL` in the Production environment to the Render public HTTPS URL, for example `https://your-draftly-api.onrender.com`. Vite embeds this public URL at build time. Redeploy the frontend after changes and keep database credentials on Render.
4. Deploy and confirm the actual Vercel domain matches an allowed Render origin. The project rewrite in `frontend/vercel.json` serves the app when a document link is opened directly or refreshed.

[Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)

### Schema bootstrap and future migrations

For the first deploy, use a dedicated, empty PostgreSQL database. Startup runs SQLModel `create_all` and seeds both demo users in a PostgreSQL transaction. A transaction-scoped advisory lock coordinates concurrent Draftly startups. Seed inserts preserve existing user rows, and startup does not run any drop operations.

`create_all` can create missing tables, but it cannot upgrade existing columns, indexes, or constraints or transfer rows from SQLite. For an existing target database, back it up and verify its schema against the models before deploying. Apply a reviewed, versioned migration for any schema difference. Test future migrations against a restored copy before running them on the hosted database. Keep the local SQLite file separate from deployment.

### Hosted verification

In PowerShell, substitute the deployed URLs and run:

```powershell
$api = 'https://your-draftly-api.onrender.com'
$web = 'https://your-draftly.vercel.app'
Invoke-RestMethod "$api/health"
Invoke-RestMethod "$api/demo-users" -Headers @{ 'X-Demo-User-Id' = '1' }
Invoke-WebRequest "$api/documents" -Method Options -Headers @{
    Origin = $web
    'Access-Control-Request-Method' = 'GET'
    'Access-Control-Request-Headers' = 'X-Demo-User-Id'
}
```

Expect health status `ok`, both demo users, and a 200 preflight with `Access-Control-Allow-Origin` matching the frontend origin. Health checks only process liveness after startup. The demo-user request verifies live database access. In the browser, create and save a synthetic document as Alex, refresh its direct link, share it with Jordan, confirm read-only access as Jordan, revoke access as Alex, and import a synthetic text or Markdown file.

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

git diff --check
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

Demo switching uses the `X-Demo-User-Id` request header. Access is checked on every API request, so after revocation the recipient loses access on the next request. Content they already loaded may remain visible in their open tab until they leave or reload.

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
