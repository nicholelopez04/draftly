# Ajaia LLC assignment submission

**Project** — Draftly, a rich-text document workspace with persistent storage, demo-user switching, read-only sharing, and text and Markdown imports.

- [GitHub repository](https://github.com/nicholelopez04/draftly)
- [Live application](https://draftly-weld-rho.vercel.app)
- [API health endpoint](https://draftly-api-7im4.onrender.com/health)
- Google Drive folder — `<GOOGLE_DRIVE_FOLDER_URL>`
- Walkthrough video — `<WALKTHROUGH_VIDEO_URL>`

## Deliverables checklist

- [ ] Working deployment. The frontend home page and API health endpoint returned HTTP 200. Confirm the full hosted browser flow on the submission revision.
- [x] At least one meaningful automated test. The backend suite covers persistence, sharing and revocation, import validation, and configuration. The frontend suite covers identity restoration and direct document requests.
- [x] Short [architecture note](ARCHITECTURE.md).
- [x] Short [AI workflow note](AI_WORKFLOW.md). Confirm the personal review and testing details flagged there.
- [ ] Record and link a **3–5 minute walkthrough video**.
- [ ] Share **one Google Drive folder** containing the source code, README, architecture note, AI workflow note, submission checklist, and walkthrough video. Verify reviewer access to the folder and video.

## Reviewer walkthrough

1. Open the live app. Select **Alex Morgan** under **Switch demo user**. Create a synthetic document, rename it, apply formatting, and wait for **Saved**. Refresh to check the saved document.
2. Select **Share** and grant **Jordan Lee** access. Return to the dashboard, switch to Jordan, and open **Shared With Me**. Confirm the document shows **Read Only**. Open its URL in a new tab while Jordan is selected.
3. Switch back to Alex and revoke Jordan's access. Switch to Jordan and reload the link to confirm access is gone.
4. Under **My Documents**, choose **Import Document** and import a small synthetic UTF-8 `.txt` or `.md` file. The file limit is 1 MB (1,048,576 bytes). Markdown supports two heading levels, simple bold and italic, and flat bullet and numbered lists.

## Verification and limits

The backend suite passed 28 tests, including formatted document persistence, recipient read-only access and revocation, and valid and invalid imports. The two frontend tests passed with mocked API responses. Frontend build and lint also passed. HTTP reachability was checked separately. The full hosted browser walkthrough and live PostgreSQL behavior remain to be confirmed.

Demo-user switching is not secure authentication. Use synthetic data only. Sharing provides read-only access for recipients and does not support real-time simultaneous collaboration. The Markdown importer supports a limited subset. See the [README for local setup, configuration, and deployment](README.md).
