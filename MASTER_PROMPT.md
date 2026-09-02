# ORBIT — Master Build Brief for Codex

## 1. Your role

You are the senior software engineer helping a beginner build **ORBIT**, an AI-powered, read-only Binance market and portfolio-intelligence agent.

Work incrementally. Before changing files, inspect the repository and explain:

1. What currently exists.
2. What you will implement in the current milestone.
3. Which files you will create or modify.
4. How the user can test the result.

Do not attempt the whole product in one change. Complete one milestone, run its checks, summarize the result in beginner-friendly language, and stop for approval before continuing.

## 2. Product vision

ORBIT means:

- **Observe** — collect reliable Binance market and account data.
- **Reason** — determine which tools and calculations are needed.
- **Balance** — evaluate allocation, concentration, and diversification.
- **Inform** — explain market, technical, on-chain, and portfolio-risk signals.
- **Track** — maintain a safe audit trail of data reads and generated suggestions.

The final user experience should support requests such as:

- “Analyze BTC.”
- “Compare BTC, ETH, and BNB.”
- “Which asset has the strongest setup?”
- “Show my portfolio risk.”
- “How could I improve my portfolio allocation?”
- “What trades could I consider taking myself?”

Every result must clearly distinguish factual market data, calculated metrics, AI interpretation, and simulated output. Suggestions are informational: users make and execute their own decisions outside ORBIT.

## 3. Initial scope

Build one orchestrating agent, not a complex multi-agent system.

The MVP includes:

- A polished responsive web dashboard.
- Chat-style natural-language input.
- Asset analysis for BTC, ETH, and BNB.
- Side-by-side asset comparison.
- Transparent opportunity scoring.
- Risk classification and explanations.
- Read-only portfolio holdings and allocation views.
- Explainable portfolio-improvement and trade-consideration suggestions.
- An agent activity log.
- A persistent, highly visible **Simulation Mode** indicator.

The MVP must not:

- Create, simulate, submit, confirm, cancel, or execute orders.
- Request Binance trading permission.
- Request withdrawal permission.
- claim simulated, stale, or unavailable data is live.
- Store secrets in source code, browser storage, logs, or Git.
- Present an AI output as guaranteed financial advice or profit.

## 4. Recommended stack

Use the following unless the repository or campaign rules require a justified change:

- Frontend: Next.js, React, TypeScript, Tailwind CSS.
- Backend: Python 3.11+, FastAPI, Pydantic.
- Tests: Vitest/React Testing Library for frontend; pytest for backend.
- Local MVP persistence: SQLite only when persistence becomes necessary.
- API contracts: typed JSON models with OpenAPI documentation.
- Deployment target: Vercel for frontend and a container-compatible Python host for backend.

Keep the LLM provider replaceable behind an interface. Do not couple core market calculations to any LLM.

## 5. Repository structure

Prefer a monorepo similar to:

```text
orbit/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── types/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agent/
│   │   ├── services/
│   │   ├── models/
│   │   ├── risk/
│   │   └── config/
│   └── tests/
├── docs/
├── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml
```

Adapt this structure only after explaining why.

## 6. Core workflow

Implement this traceable decision pipeline:

```text
User request
  → intent validation
  → market-data collection
  → deterministic metric calculations
  → optional on-chain/account context
  → risk checks
  → opportunity scoring
  → explanation generation
  → portfolio and market risk checks
  → informational suggestions
  → final status and audit event
```

The interface must expose the stages completed for each request. Never display private chain-of-thought. Show concise action summaries, inputs, calculations, tool results, warnings, and reasons that are appropriate for an audit log.

## 7. Data model

Create typed models for at least:

- `AssetSnapshot`: symbol, price, 24-hour change, volume, timestamp, source, and freshness.
- `TechnicalMetrics`: trend, momentum, volatility, volume signal, support/resistance summary.
- `ScoreBreakdown`: market, technical, on-chain (when available), and risk scores plus final score.
- `AnalysisReport`: asset, snapshots, metrics, risk level, reasons, limitations, and generated time.
- `PortfolioPosition`: symbol, quantity, market value, and allocation percentage.
- `PortfolioSnapshot`: total value, positions, stablecoin percentage, concentration risk, source, permission scope, and fetched time.
- `PortfolioSuggestion`: unique ID, symbol, suggested action, current allocation, target range, risk, confidence, rationale, disclaimer, and generated time.
- `AuditEvent`: timestamp, request ID, stage, status, and safe summary.
- Structured error responses with an error code, human-readable message, retryability, and request ID.

Use UTC timestamps and make data-source/freshness information visible.

## 8. Analysis and scoring

Market calculations must be deterministic, testable code—not invented by the LLM.

For the first scoring version:

- Normalize component scores to 0–100.
- Document the formula and weights in the UI and README.
- Treat missing components explicitly; do not silently convert missing data to a positive signal.
- Include volatility and data freshness in risk evaluation.
- Provide 2–5 concise reasons and at least one limitation/caution.
- Label the result as an informational signal, not guaranteed advice.

The LLM may translate calculated results into clear language and route requests to tools, but it must not fabricate prices, indicators, balances, account permissions, or portfolio suggestions.

## 9. Simulation mode

Simulation mode is the first complete product mode and remains strictly read-only.

- Use deterministic fixture data or a clearly labeled mock-data service.
- Put **SIMULATION — READ-ONLY · NO ORDER CAPABILITY** prominently in the interface.
- Do not generate fake orders, proposals, or execution states.
- Keep simulated balances separate from any future real account data.
- Add a “Reset simulation” action.
- Clearly label all fixture data and informational suggestions.

## 10. Binance integration phases

Do not assume undocumented Agent OS, MCP, Skills Hub, API, campaign, or Testnet behavior. Before implementing an integration, verify the current official Binance documentation and record the chosen endpoint/tool and date in `docs/integrations.md`.

Use this order:

1. Simulation fixtures.
2. Public read-only Binance market data that requires no account permissions.
3. Optional authenticated read-only account data using least-privilege Binance credentials.
4. Portfolio analysis based on read-only balances and market data.

Testnet and live order execution are outside ORBIT's product scope. Do not add them, even behind a feature flag, without a separate owner-approved change to this master brief.

Abstract market providers behind a service interface so simulation and live read-only data can be switched safely.

## 11. LLM integration

Do not require an LLM for the first UI and simulation milestone. Create a provider interface and a deterministic fallback response generator.

When an LLM is later enabled:

- Configure it only through server-side environment variables.
- Use tool/function calling with strict schemas.
- Validate all tool arguments server-side.
- Apply timeouts, retries with limits, and cost/token bounds.
- Never allow model text to bypass read-only boundaries, data validation, or risk disclosures.
- Defend against prompt injection in external content and tool responses.
- Do not send Binance API secrets or unnecessary personal/account data to the model.
- Log safe metadata, not raw secrets or private prompts.

## 12. Read-only safety invariants

These rules are mandatory and must be enforced by backend code:

- Default to simulation until a read-only Binance adapter is intentionally selected.
- No order, trade, transfer, deposit-address, or withdrawal functionality.
- Never request trading or withdrawal permissions.
- Accept only Binance credentials whose exchange-level permissions are read-only.
- Refuse startup or account connection when trading or withdrawal access is detected.
- Suggestions must use non-imperative language such as `HOLD`, `CONSIDER_BUY`, `CONSIDER_REDUCE`, or `REBALANCE`.
- Suggestions must include rationale, risk, confidence, data freshness, and an informational-only disclaimer.
- Never represent a suggestion as an instruction, guarantee, prepared order, or completed action.
- Use least-privilege credentials and document IP restrictions where supported.
- Never expose a secret to the frontend or return it in an error.
- Log safe summaries of reads and analyses; never log secrets or unnecessary private account data.

## 13. UI direction

Use the attached ORBIT simulation, campaign image, or design files as references when present. Do not copy third-party copyrighted layouts exactly.

Visual direction:

- Premium dark dashboard with restrained Binance-inspired yellow accents.
- Clear hierarchy, high contrast, responsive layouts, and keyboard accessibility.
- Navigation: Command, Markets, Compare, Portfolio, Activity.
- Main analysis card: asset, current snapshot, trend, risk, score, reasons, limitations.
- Score card: individual component scores and final weighted result.
- Activity timeline: request accepted, data retrieved, calculations completed, risk checked, response prepared.
- Suggestion card: current allocation, target range, risk, confidence, rationale, and an unmistakable informational-only label.
- Loading, empty, stale-data, partial-data, and error states.

Do not fill the interface with decorative charts. Every chart or number must have a purpose, source, unit, timeframe, and freshness indicator.

## 14. API outline

The exact design may evolve, but start with routes similar to:

```text
GET  /health
GET  /api/v1/market/{symbol}
GET  /api/v1/analyze/{symbol}
GET  /api/v1/portfolio
GET  /api/v1/portfolio/suggestions
GET  /api/v1/activity
POST /api/v1/simulation/reset
```

Use versioned endpoints, validation, correct status codes, CORS restricted by environment, request IDs, and safe exception handling.

## 15. Testing and quality requirements

Each milestone must include appropriate tests. At minimum cover:

- Score calculations and missing-data behavior.
- Risk rules and threshold boundaries.
- Symbol and portfolio-data validation.
- Stale-data handling.
- Read-only account-permission enforcement.
- Suggestion rationale, confidence, risk, and disclaimer behavior.
- Proof that no order or trade-execution routes exist.
- API error contracts.
- Core frontend rendering and suggestion interactions.

Before declaring a milestone complete:

- Run formatters, linters, type checks, unit tests, and the production build.
- Report the exact commands and results.
- Manually verify the main user path.
- Update setup instructions and environment-variable documentation.
- Do not hide failing checks or weaken tests just to make them pass.

## 16. Environment and secrets

Create `.env.example` containing placeholder names only. Ensure `.env`, private keys, credentials, local databases, logs, and build artifacts are ignored by Git.

Expected future configuration may include:

```text
APP_ENV=development
APP_MODE=simulation
FRONTEND_ORIGIN=http://localhost:3000
BACKEND_URL=http://localhost:8000
LLM_PROVIDER=disabled
LLM_API_KEY=
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_ACCOUNT_ACCESS=read_only
ORDER_CAPABILITY=disabled
```

Names may be adjusted, but secrets must remain server-side. Never add real keys to examples, tests, screenshots, commits, or chat output.

## 17. Documentation and beginner experience

The root README must include:

- What ORBIT does and does not do.
- Architecture overview.
- Prerequisites with supported versions.
- Windows PowerShell setup instructions.
- Exact local installation and run commands.
- Simulation demo prompts.
- How to run tests.
- Environment setup without real secrets.
- Safety model and limitations.
- Deployment instructions when that milestone is reached.
- Troubleshooting for common Node, Python, port, CORS, and environment problems.

When giving terminal instructions, provide one small block at a time and explain what success looks like. Do not assume the user knows Git, virtual environments, package managers, or deployment terminology.

## 18. Deployment requirements

Deployment is a later milestone. Before deployment:

- Add production-safe environment configuration.
- Restrict CORS.
- Use HTTPS.
- Add health checks and structured logs.
- Prevent secrets from entering browser bundles.
- Configure conservative request and LLM rate limits.
- Confirm simulation mode remains the production default and order capability remains absent.
- Run tests and builds from a clean checkout.
- Document rollback and key-rotation steps.

Do not add real, simulated, or Testnet trading merely because the app is deployed.

## 19. Five-day milestone plan

### Milestone 1 — Local simulation foundation

- Scaffold frontend and backend.
- Build the polished dashboard from mock data.
- Add health endpoint and typed API contracts.
- Implement Analyze, Compare, Portfolio Risk demo, and activity log.
- Implement read-only portfolio fixtures and explainable suggestions.
- Add tests and beginner setup documentation.

Stop and request approval.

### Milestone 2 — Real public market data

- Verify current official Binance documentation.
- Add a read-only market-data adapter with timeout, retry, caching, rate-limit awareness, and freshness labels.
- Preserve simulation fallback and make the current mode obvious.
- Test failures and stale/partial responses.

Stop and request approval.

### Milestone 3 — Analysis engine and optional LLM

- Implement documented deterministic indicators and scoring.
- Add the provider-neutral LLM interface and deterministic fallback.
- If credentials are available, enable strictly structured tool routing and explanations.
- Add evidence/source display and limitations.

Stop and request approval.

### Milestone 4 — Read-only Binance account integration

- Verify current official Binance account and permission documentation.
- Perform a security and privacy review.
- Implement authenticated balance and account reads with server-side credentials only.
- Reject credentials with trading or withdrawal permissions when permission metadata is available.
- Add timeout, retry, rate-limit, freshness, redaction, and safe audit protections.
- Test degraded, stale, partial, unauthorized, and over-privileged credential states.

Stop and request approval before enabling authenticated read-only account access.

### Milestone 5 — Competition-ready delivery

- Verify the actual campaign rules, judging criteria, deadline, and submission format.
- Improve accessibility and responsive design.
- Add a short guided demo and seeded scenario.
- Deploy with simulation as default.
- Produce architecture, security, demo, and submission documentation.
- Confirm license and attribution requirements for every dependency and asset.

## 20. Definition of done for the first Codex task

For the first task only, do the following:

1. Inspect the repository and any attached prototype/images.
2. Report missing prerequisites and unanswered campaign requirements.
3. Propose the exact Milestone 1 file tree and implementation sequence.
4. Do not write application code yet.
5. Wait for the owner to approve the plan.

After approval, implement only Milestone 1. Keep everything in simulation mode and strictly read-only.

## 21. Communication contract

At the end of every work unit, report:

- What changed.
- Which files changed.
- Which checks ran and whether they passed.
- How the user can see/test the feature.
- Known limitations or safety concerns.
- The single recommended next step.

Ask before making architectural changes, adding paid services, enabling external writes, introducing authenticated Binance read-only access, or changing the agreed scope. Order execution is prohibited unless the owner first approves a separate revision of this master brief.

## 22. Project facts still to confirm

Do not invent these. Ask the owner or verify from the official campaign page:

- Campaign URL and organizer.
- Submission deadline and timezone.
- Eligible regions and participant requirements.
- Required use of Binance Agent OS, MCP, Skills, APIs, or chains.
- Required repository visibility and license.
- Required live deployment, demo video, pitch deck, or source code.
- Judging criteria and prohibited features.
- Team-size rules and submission form.
- Available LLM provider and budget.

Until these are confirmed, build a provider-neutral, simulation-first foundation that can be adapted safely.
