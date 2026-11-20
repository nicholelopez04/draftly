# AI workflow

I used ChatGPT to structure the assignment into a working editor, sharing and imports, then deployment and bug fixes. I used Codex to inspect the repository, implement changes in place, iterate on code and tests, and run verification commands. This shortened the feedback loop across React, FastAPI, and the database while keeping each change tied to an observable behavior.

I confirmed the Phase 1 create, rename, edit, save, refresh, and reopen flow with formatting preserved. I also reported two issues observed in production. Codex traced those reports through the code, made scoped changes, and ran automated checks. Final hosted browser verification is a separate step.

| Production issue | What the AI-assisted iteration did |
| --- | --- |
| Bullet and numbered lists indented text but showed no markers | Codex traced the TipTap commands, inspected Tailwind's reset and the compiled CSS, and moved explicit marker styles onto TipTap list items. The reset was confirmed in the build. The exact production cascade was not inspected. |
| A Jordan document link opened in a new tab returned `404` | Codex traced the tab-scoped `sessionStorage` preference to the Alex fallback and request header. It switched persistence to `localStorage`, migrated legacy selections when available, and added request-level tests for restoration, retry, and inaccessible documents. |
