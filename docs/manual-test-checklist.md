# Manual integration test checklist

## Local services

- [ ] Start the backend: `cd backend && .venv/bin/uvicorn app.main:app --reload`.
- [ ] Confirm `http://127.0.0.1:8000/health` returns `status: ok`.
- [ ] Start the frontend: `cd frontend && npm run dev`.
- [ ] Open `http://localhost:5173` and confirm the header says **Backend connected**.

## Integration truth

- [ ] Open Settings → Integrations.
- [ ] Confirm Gmail is **Synthetic demo** or **Connected — real**, matching actual OAuth state.
- [ ] Confirm OpenRouter is **Not configured**, **Configured but unverified**, or **Connected — real**.
- [ ] Confirm Exa and Google Sheets are **Not configured**.

## OpenRouter

- [ ] Put `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, and `OPENROUTER_MODEL` in the ignored root `.env`.
- [ ] Restart the backend, then select **Verify real request**.
- [ ] Confirm only provider, model, success/failure, latency, and optional safe request ID appear.
- [ ] Open Agent Activity and confirm a successful run is labelled **REAL**. If the check did not succeed, confirm no completed extraction is shown.

## Manual encrypted PDF

- [ ] Select **Import statement** and choose a synthetic encrypted PDF.
- [ ] Enter a wrong password and confirm **Password needed** without a server error.
- [ ] Re-submit the same file with its correct password; never guess the password for an existing fixture.
- [ ] Confirm the PDF is decrypted and extracted locally, OpenRouter returns schema-valid JSON, and Ledger Guard either accepts or visibly blocks it.
- [ ] Confirm the statement and its source page appear in Statements/Transactions.
- [ ] Import the same PDF again and confirm it is reported as a duplicate.

## Gmail

- [ ] Configure Google OAuth with `http://127.0.0.1:8000/api/auth/google/callback` and Gmail read-only scope.
- [ ] Select **Connect Gmail**, authorize the dedicated test account, and confirm **Connected — real** plus the account address.
- [ ] Configure `GMAIL_ALLOWED_SENDERS` and `DEMO_PDF_PASSWORD` locally.
- [ ] Send a supported encrypted synthetic statement PDF to the test account, then select **Sync now**.
- [ ] Confirm Gmail message/attachment IDs are recorded, unrelated body content is absent, one failed attachment does not block another, and a repeated sync reports duplicates.

## Export and safety

- [ ] Filter Transactions and select **Export filtered CSV**; verify the CSV contains only the filtered rows.
- [ ] Use Overview → Export → Download CSV.
- [ ] Confirm Google Sheets says **Coming next** and is not actionable.
- [ ] Search backend output for credentials, passwords, raw statement text, prompts, authorization headers, tokens, and full account identifiers; none should appear.
- [ ] Run `cd backend && .venv/bin/pytest -q` and confirm all non-credential tests pass; the real integration test may skip only when the key is unavailable.
