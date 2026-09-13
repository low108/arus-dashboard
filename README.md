# Arus

Arus combines two hackathon workstreams in one repository:

- `frontend/` + `backend/`: a Gmail-native financial statement agent using real read-only Gmail OAuth, local encrypted-PDF processing, real OpenRouter extraction, deterministic ledger reconciliation, transaction provenance, CSV export, and editable financial goals.
- Root web app: the Google Sheets, financial-health metrics, and Exa research dashboard contributed from `low108/arus-dashboard`.
- `agent/`: the imported Maybank/card parsers, deterministic spending consolidator, OpenRouter merchant sorter, and optional Telegram report flow from `arus-combined` (without its synthetic fixtures).

Secrets belong only in ignored local environment files. Never commit OAuth credentials, access tokens, PDF passwords, or API keys.

## Run the Gmail and statement demo

```bash
cp .env.example .env
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Add `http://127.0.0.1:8000/api/auth/google/callback` to the OAuth web client's authorized redirect URIs.

## Verify

```bash
cd backend && .venv/bin/pytest
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```

The dashboard never substitutes fabricated financial values when a real integration is unavailable.
