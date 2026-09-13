# Architecture

## Vertical slice

```text
Gmail adapter
  -> supported PDF metadata and bytes
  -> SHA-256 idempotency check
  -> isolated local pikepdf decryption
  -> page-aware local pdfplumber extraction
  -> minimum text sent to OpenRouter
  -> strict Pydantic StatementExtraction
  -> deterministic Decimal ledger guard
  -> accepted records or needs_review
  -> overview and safe Agent Activity
```

`frontend/` is a Next.js App Router application. Typed fixture data is isolated behind `lib/mock-data.ts` so API fetchers can replace it without changing the views.

`backend/` is a FastAPI application. `gmail/`, `documents/`, `providers/`, and `ledger/` are independent boundaries. SQLAlchemy models use SQLite locally and avoid SQLite-specific ORM behavior so a PostgreSQL URL can replace it later.

The model proposes structure and categories. `ledger/reconcile.py` alone establishes whether a statement contributes to totals. Invalid statements remain visible but are excluded from overview results.
