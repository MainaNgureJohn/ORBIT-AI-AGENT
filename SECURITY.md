# Security policy

ORBIT handles exchange metadata and optional account balances, so credential hygiene is part of the product boundary.

## Reporting a vulnerability

Do not open a public issue containing an API key, secret, private portfolio data, or an exploitable vulnerability. Use GitHub private vulnerability reporting when available, or contact the repository owner privately through their GitHub profile.

Include the affected component, reproduction steps with placeholder data, expected impact, and a proposed mitigation if known.

## Credential rules

- Use a dedicated Binance API key with reading enabled and every trading, transfer, and withdrawal capability disabled.
- Apply an IP restriction at Binance whenever practical.
- Keep Binance and LLM keys in process environment variables or a trusted deployment secret store.
- Never place real values in `.env.example`, source files, tests, screenshots, logs, issues, or commits.
- Rotate a credential immediately if it is exposed, even if the exposure was brief or the Git commit was later deleted.

The repository ignores common environment, key, certificate, log, database, dependency, and build-output files. This is defense in depth, not a substitute for reviewing staged changes before every push.

## Product safety invariants

Changes must preserve all of the following:

- No order creation, cancellation, confirmation, or execution.
- No deposits, withdrawals, transfers, or trading permissions.
- Account data is rejected unless Binance reports a strictly read-only permission set.
- Credentials remain server-side and are absent from responses and logs.
- Missing or stale data is disclosed rather than fabricated.
- LLM output is informational and grounded in validated input.
