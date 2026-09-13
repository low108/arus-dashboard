# Implemented vs planned

| Capability | Status | Notes |
|---|---|---|
| Dashboard views | Implemented | Backend-aware with explicit real/synthetic labels; responsive and keyboard accessible |
| Integration status | Implemented | Safe backend status mirrored in Settings → Integrations |
| Manual import UI | Implemented | Multipart POST body, password input, honest error states |
| Transactions workspace | Implemented | Search, filters, sort, pagination, category correction, provenance, CSV |
| Encrypted PDF processing | Implemented | Local pikepdf + pdfplumber, temp cleanup |
| OpenRouter client | Implemented | Strict schema, timeout, retries, safe health |
| Ledger guard | Implemented | Exact Decimal reconciliation and validation |
| SQLite records | Implemented | Extraction, accepted records, corrections stored separately |
| Synthetic Gmail adapter | Implemented | Clearly labelled development flow |
| Mock Gmail/OpenRouter | Implemented | Automated tests |
| Live Gmail API | Implemented, unconnected | Read-only OAuth and attachment discovery; needs credentials and authorization |
| Hosted processing API | Local-only | FastAPI is the runnable processing backend; hosted Site is the demo UI |
| Password retry | Manual re-submit | Same hash can be retried after `needs_password` without duplication |
| Google Sheets | Not implemented | Clearly labelled “Coming next”; CSV remains functional |
| Exa, OpenAI briefing, Gemma | Not implemented | Intentionally deferred until core integration is complete |
