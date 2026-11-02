# Security

This pilot reads accounting data and can write only purchase and sale DRAFTS.
The write transport has a path allowlist; booking a draft (createPurchase /
createSale) and every other write is refused locally. Keep it that way: do not
add tools that finalise, send or delete booked records. Set FIKEN_READ_ONLY=1
to disable all writes. Never put credentials in issues, fixtures, logs or
documentation. Only synthetic test
data belongs in the repository.

For vulnerabilities, use GitHub private vulnerability reporting when enabled.
If unavailable, open an issue requesting a private reporting channel without
including exploit details, tokens or accounting data.

Supported release: 0.4.x pilot. OAuth uses macOS Keychain or Windows Credential Manager; no plaintext fallback.
Local logout does not revoke Fiken consent. Revoke the app in Fiken as well.
