# Integration audit

Audited 13 September 2026.

| Area | Finding |
|---|---|
| Frontend | `http://localhost:5173` via `cd frontend && npm run dev` |
| Backend | `http://127.0.0.1:8000` via `cd backend && .venv/bin/uvicorn app.main:app --reload` |
| Frontend data before audit | Static typed data from `frontend/lib/mock-data.ts`; no backend calls |
| Frontend data after audit | Integration status, statements, transactions, overview, sync, import, activity and verification call the backend; empty results fall back to labelled synthetic demo data |
| Gmail OAuth before audit | Not implemented |
| Gmail OAuth after audit | Start/callback/disconnect routes implemented with Gmail read-only scope; no token exists until the user authorizes |
| Gmail attachment retrieval | Real API adapter retrieves supported PDF attachment bytes and metadata without retaining email bodies |
| PDF upload | Multipart backend route plus visible frontend import dialog |
| PDF decryption | Local pikepdf decryption, pdfplumber extraction, explicit `finally` cleanup |
| OpenRouter | Real client and minimal verification route implemented; no genuine request succeeded because the key is not available |
| Model | `OPENROUTER_MODEL`, falling back locally to `openai/gpt-4.1-mini` |
| Displayed finances | Synthetic demo until a real statement is successfully imported and reconciled |
| Exa | Not implemented |
| Google Sheets | Not implemented; CSV export is working |

## OAuth redirect URI

Register this exact authorized redirect URI for the local backend route:

`http://127.0.0.1:8000/api/auth/google/callback`

Set `GOOGLE_REDIRECT_URI` to the identical value. Gmail and Sheets permissions are intentionally separate; this callback currently requests Gmail read-only access only.

## Current blockers

- No workspace-root `.env` is present, although `.env` is correctly ignored.
- No `OPENROUTER_API_KEY` is available, so the minimal real verification cannot reach OpenRouter.
- No Google OAuth client ID/secret or local `backend/token.json` exists, so Gmail cannot connect or discover a real attachment.
- No `fixtures/sample_statement_202609.pdf` exists, so that named fixture cannot be tested.
- `DEMO_PDF_PASSWORD` is unavailable, so no Gmail-retrieved encrypted demo attachment can be decrypted automatically.
- Google Sheets export is intentionally not exposed as functional; it needs a separate user-approved permission flow.
