# Contributing

Contributions that improve ORBIT's clarity, reliability, accessibility, tests, and read-only analysis are welcome.

## Development workflow

1. Fork the repository and create a focused branch.
2. Follow the setup instructions in [README.md](README.md).
3. Keep external integrations behind provider interfaces.
4. Add or update tests for behavior changes.
5. Run the backend and frontend checks before opening a pull request.
6. Explain user-visible behavior, safety implications, and test evidence in the pull request.

## Required checks

```bash
cd backend
python -m pytest -q
```

```bash
cd frontend
npm ci
npm run typecheck
npm test
npm run build
```

## Pull-request boundaries

Pull requests must not add order, trade, transfer, deposit, or withdrawal capability. Never include real credentials or private account data. Use fixtures and clearly fake placeholder values in tests and documentation.

Keep calculations deterministic and testable. An LLM may explain validated results, but it must not become the source of balances, prices, scores, or permission decisions.
