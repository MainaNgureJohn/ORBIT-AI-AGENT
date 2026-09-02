# ORBIT

ORBIT is a read-only Binance market and portfolio intelligence dashboard. It reads account and market data, explains portfolio risk, and suggests possible portfolio improvements for the user to evaluate and perform independently.

ORBIT does not create, simulate, submit, confirm, cancel, or execute orders. It never requests trading or withdrawal permissions.

## Milestone 1

This first milestone includes:

- Dark responsive dashboard for BTC, ETH, and BNB.
- Analyze, Compare, Portfolio Risk, and Portfolio Suggestions demo views.
- Deterministic mock market snapshots and weighted opportunity scores.
- Activity timeline with safe audit summaries.
- Read-only portfolio fixture with explainable allocation suggestions.
- FastAPI health, market, portfolio, and suggestion endpoints.

## Run locally

### Backend

From `backend/`, create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`, with documentation at `/docs`.

### Frontend

From `frontend/`, install and start the dashboard:

```powershell
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`.

## Read-only simulation demo

Try the asset tabs, ask ORBIT to compare assets, review portfolio risk, or request portfolio improvement ideas. The demo uses local fixture data and contains no order workflow. Use “Reset” to restore the fixture state.

## Scoring and safety

Scores and suggestions are informational only and are not financial advice or profit forecasts. The current score is a weighted average: market 30%, technical 35%, on-chain 15%, and risk 20%. On-chain is explicitly marked unavailable in simulation data; it contributes zero rather than being treated as a positive signal.

Simulation mode is always visible and uses no real exchange credentials. A future Binance connection must use API credentials with read-only access; trading and withdrawals must remain disabled at the exchange level.
