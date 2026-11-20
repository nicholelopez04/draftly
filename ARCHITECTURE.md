# Draftly architecture

## Request and data flow

The React single-page app runs on Vercel. React Router handles the dashboard and document URLs, and a Vercel rewrite serves the app for direct document links. Before document requests run, the app restores the browser's demo-user preference. The API client sends that identity as `X-Demo-User-Id` to the FastAPI service on Render. FastAPI validates request data and uses SQLModel to read or write SQLite locally and PostgreSQL on Render.

TipTap stores the document body as structured JSON. A document row has a UUID, owner, title, body, and timestamps. The editor waits 650 ms after edits, serializes saves within that editor instance, and sends the title and full body in a PATCH. In-app navigation attempts to flush pending edits, and a failed save leaves the draft in memory for retry. Reopening the document loads the last persisted snapshot. Imports generate TipTap nodes directly from UTF-8 text and use the same document storage path.

## Sharing and authorization

`DocumentShare` links a document to a recipient, with a composite primary key that makes grants idempotent. The backend validates the demo ID and scopes reads to the owner or a recipient. Ownership comes from the request identity when a document is created. Only the owner can edit or change shares. An inaccessible document returns the same `404` as a missing one. The frontend presents shared documents in a read-only editor. Revoking a share blocks subsequent requests, while a recipient may still see a snapshot already loaded in their tab.

## Decisions and tradeoffs

- **Scope.** Establish create, edit, save, and reopen first. Add read-only sharing, bounded imports, and repeatable deployment once the core editor works.
- **Persistence.** TipTap JSON round-trips formatting without converting the document to HTML. Whole-document saves keep the API small, at the cost of larger writes and last-write-wins behavior across multiple owner tabs.
- **Identity.** Two seeded accounts make sharing easy to review. The header is caller-controlled and provides no secure authentication. Use synthetic data only. Real-time simultaneous editing and cross-tab conflict resolution are outside the current scope.
- **Imports and schema.** Imports deliberately support a small Markdown subset and keep HTML as text. SQLModel `create_all` bootstraps missing tables and preserves existing rows. Existing-table schema changes require versioned migrations.

## With another 2–4 hours

I would add a browser regression test covering Jordan's direct document link in a new tab and its behavior after Alex revokes access. I would then add an optimistic-concurrency check so two owner tabs cannot silently overwrite each other's edits, with a clear conflict message and a way to keep the unsaved draft. Secure authentication would be a separate milestone before using real data.
