# ORBIT

[![CI](https://github.com/MainaNgureJohn/ORBIT-AI-AGENT/actions/workflows/ci.yml/badge.svg)](https://github.com/MainaNgureJohn/ORBIT-AI-AGENT/actions/workflows/ci.yml)

ORBIT is a read-only crypto market and portfolio intelligence dashboard. It combines live Binance data, deterministic risk scoring, and optional LLM explanations to help users understand a portfolio without giving the application permission to trade.

> ORBIT is informational software, not financial advice. It cannot place orders, transfer funds, deposit, or withdraw.

## What it does

- Displays live BTC, ETH, and BNB prices from Binance's public market-data API.
- Connects to a Binance account using a verified read-only API key.
- Lists every non-zero portfolio asset, including stablecoins and assets whose public price is unavailable.
- Values supported holdings in USDT using direct or BTC/ETH/BNB bridge markets.
- Produces transparent opportunity scores from deterministic calculations.
- Adds detailed, grounded explanations through Groq or OpenAI when configured.
- Falls back safely when market data, account data, or an LLM is unavailable.
- Records read-only activity summaries without logging credentials.

## Safety boundary

ORBIT deliberately implements observation and analysis only. Before accepting account balances, the backend verifies that the Binance key has reading enabled and supported trading, withdrawal, transfer, margin, futures, options, and portfolio-margin permissions disabled.

Credentials stay in the backend process environment. They are never sent to the browser, written by the application, or included in API responses. The repository contains placeholders only.

## Architecture

```text
Browser
  └── Next.js dashboard (port 3000)
        └── FastAPI service (port 8000)
              ├── Binance public market data
              ├── Binance signed read-only account data
              ├── Deterministic scoring and valuation
              └── Optional Groq or OpenAI explanations
```

See [Architecture](docs/architecture.md), [Analysis](docs/analysis.md), and [Integrations](docs/integrations.md) for implementation details.

## Requirements

- Python 3.11 or newer
- Node.js 20.9 or newer
- npm
- Optional: a Binance read-only API key for portfolio data
- Optional: a Groq or OpenAI API key for detailed explanations

## Quick start: public market mode

Public market mode is the default and needs no API keys.

### 1. Clone the repository

```bash
git clone https://github.com/MainaNgureJohn/ORBIT-AI-AGENT.git
cd ORBIT-AI-AGENT
```

### 2. Start the backend

PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

### 3. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Connect a live Binance account

Create a dedicated Binance API key with reading enabled. Disable spot and margin trading, futures, options, transfers, and withdrawals. Restrict the key to your trusted public IP when possible.

On Windows, stop the public backend and run the secure launcher from the repository root:

```powershell
.\backend\run_live_account.ps1
```

The launcher masks the Binance key and secret, optionally asks for a Groq key, and keeps them only in the backend process environment. Do not paste credentials into chat, source code, `.env.example`, screenshots, issues, or commits.

For another shell or deployment platform, configure these process environment variables:

```text
APP_MODE=binance_account
BINANCE_ACCOUNT_ACCESS=read_only
BINANCE_API_KEY=<read-only-key>
BINANCE_API_SECRET=<secret>
```

Never put real values in `.env.example`. If your deployment platform uses a `.env` file locally, it is already ignored by Git.

## Enable detailed LLM explanations

LLM integration is optional. Deterministic analysis remains available without it.

Groq:

```text
LLM_PROVIDER=groq
GROQ_API_KEY=<secret>
GROQ_MODEL=openai/gpt-oss-20b
```

OpenAI:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-4.1-mini
```

The model receives validated market and portfolio summaries, not exchange credentials. If the provider fails, ORBIT reports the failure state and uses deterministic output.

## API overview

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Runtime mode and sanitized provider status |
| `GET` | `/api/v1/market` | BTC, ETH, and BNB public snapshots |
| `GET` | `/api/v1/market/{symbol}` | One supported public snapshot |
| `GET` | `/api/v1/analyze/{symbol}` | Deterministic score with optional LLM explanation |
| `GET` | `/api/v1/account` | Verified read-only account balances |
| `GET` | `/api/v1/portfolio` | Portfolio valuation and full holding list |
| `POST` | `/api/v1/advice` | Grounded portfolio-improvement explanation |
| `GET` | `/api/v1/activity` | Read-only activity summaries |

There are no order, trade, transfer, deposit, or withdrawal routes.

## Configuration

The application reads configuration from process environment variables. [.env.example](.env.example) documents every supported value and contains no credentials.

Important modes:

| `APP_MODE` | Behavior |
| --- | --- |
| `binance` | Live public market data; no account credentials |
| `binance_account` | Live public data plus verified read-only account data |
| `simulation` | Explicit offline fixtures for tests and development |

The frontend uses `NEXT_PUBLIC_BACKEND_URL` and defaults to `http://localhost:8000`.

## Tests

Backend:

```bash
cd backend
python -m pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run typecheck
npm test
npm run build
```

GitHub Actions runs the same checks for pushes and pull requests.

## Project structure

```text
backend/                 FastAPI API, providers, analysis, and tests
frontend/                Next.js dashboard, API client, types, and tests
docs/                    Architecture and integration documentation
.github/workflows/       Continuous integration
.env.example             Safe configuration reference
```

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report security concerns according to [SECURITY.md](SECURITY.md), and never include real credentials in a public issue.
