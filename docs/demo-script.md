# Demo script

1. Open Overview. Point out the dated cash and card balances, mixed-date warning, and that the password-blocked statement is excluded.
2. Select **Sync Gmail**. State that the shown inbox is a synthetic development adapter, not a live connection.
3. Open Statements. Show masked identifiers, Gmail provenance, page provenance, transaction counts, and reconciliation state.
4. Open Review. Show the password recovery card and explain that the password remains local and is not retained.
5. Open Agent Activity. Walk through Gmail discovery, local decryption, OpenRouter extraction, and deterministic Ledger Guard reconciliation. Emphasize the safe metadata and configured-runtime model label.
6. Run the backend test suite. Then, only when `OPENROUTER_API_KEY` is configured, run the opt-in provider connectivity test. It reports provider, model, status, latency, and safe error type only.

The central story is that Gmail shapes discovery and provenance, while deterministic code—not a model—decides whether figures enter the overview.
