# Security

This pilot exposes read-only accounting tools. Do not add Fiken write operations
or credentials to issues, fixtures, logs or documentation. Only synthetic test
data belongs in the repository.

For vulnerabilities, use GitHub private vulnerability reporting when enabled.
If unavailable, open an issue requesting a private reporting channel without
including exploit details, tokens or accounting data.

Supported release: 0.2.x pilot. OAuth uses macOS Keychain; no plaintext fallback.
Local logout does not revoke Fiken consent. Revoke the app in Fiken as well.
