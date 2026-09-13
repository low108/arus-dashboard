# Security

- PDF passwords and provider credentials come only from environment variables or password form bodies. They are never persisted, placed in URLs, or sent to models.
- The encrypted PDF is hashed before processing. Decryption and text extraction occur in an isolated temporary directory removed when processing exits, including failure paths.
- OpenRouter receives only the minimum locally extracted text, never a PDF file or password. Statement text is marked untrusted and cannot change system instructions.
- Logs and Agent Activity contain operational metadata only: stage, provider, configured model, status, duration, counts, retries, timestamp, and a safe error class.
- Prompts, raw statement text, complete account identifiers, OAuth tokens, API keys, and chain-of-thought are not stored.
- Gmail scope must be `gmail.readonly`; sender allowlists and date windows reduce collection. Email bodies are not retained.
- Exact `Decimal` money rules, field/date/currency/direction validation, duplicate IDs, and a one-minor-unit maximum tolerance prevent model output from becoming financial truth.
- Only synthetic fixtures are committed. `.gitignore` excludes local credentials, databases, uploads, decrypted data, and logs.

Arus reports statement balances with “as of” dates. It does not describe them as live, available, or safe to spend.
