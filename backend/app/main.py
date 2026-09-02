from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import AuditEvent, PortfolioSnapshot, PortfolioSuggestion
from app.services.simulation import initial_activity, portfolio_snapshot, portfolio_suggestions, report, snapshot

app = FastAPI(title="ORBIT Read-Only Intelligence API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
activity: list[AuditEvent] = initial_activity()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "simulation", "account_access": "read_only", "order_capability": "disabled"}


@app.get("/api/v1/market/{symbol}")
def market(symbol: str):
    symbol = symbol.upper()
    if symbol not in {"BTC", "ETH", "BNB"}:
        raise HTTPException(status_code=422, detail="Unsupported symbol")
    return snapshot(symbol)


@app.get("/api/v1/analyze/{symbol}")
def analyze(symbol: str):
    symbol = symbol.upper()
    if symbol not in {"BTC", "ETH", "BNB"}:
        raise HTTPException(status_code=422, detail="Unsupported symbol")
    return report(symbol)


@app.get("/api/v1/portfolio", response_model=PortfolioSnapshot)
def get_portfolio():
    activity.append(AuditEvent(request_id="portfolio", stage="account", status="read", summary="Read-only portfolio snapshot retrieved."))
    return portfolio_snapshot()


@app.get("/api/v1/portfolio/suggestions", response_model=list[PortfolioSuggestion])
def get_portfolio_suggestions():
    activity.append(AuditEvent(request_id="suggestions", stage="analysis", status="generated", summary="Portfolio improvement suggestions generated without order capability."))
    return portfolio_suggestions()


@app.get("/api/v1/activity", response_model=list[AuditEvent])
def get_activity():
    return list(reversed(activity))


@app.post("/api/v1/simulation/reset")
def reset():
    activity.clear()
    activity.extend(initial_activity())
    return {"status": "reset", "mode": "simulation", "account_access": "read_only"}
