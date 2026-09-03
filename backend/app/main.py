from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.models.schemas import AccountSnapshot, AdviceRequest, AdviceResponse, AssetSnapshot, AuditEvent, PortfolioSnapshot, PortfolioSuggestion
from app.services.account_provider import AccountCredentialsError, AccountDataUnavailableError, AccountPermissionError
from app.services.binance_account import create_binance_account_provider_from_settings
from app.services.analysis_engine import analyze_snapshot
from app.services.binance_market import create_binance_provider_from_settings
from app.services.binance_portfolio_prices import create_binance_portfolio_price_provider_from_settings
from app.services.market_provider import InvalidSymbolError, MarketDataProvider, MarketDataUnavailableError, SimulationMarketProvider
from app.services.portfolio_valuation import value_account
from app.services.llm_provider import create_explanation_provider_from_settings, DisabledLLMProvider
from app.services.simulation import initial_activity, portfolio_snapshot, portfolio_suggestions, report

settings = get_settings()
app = FastAPI(title="ORBIT Read-Only Intelligence API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=["GET", "POST"], allow_headers=["*"])
activity: list[AuditEvent] = initial_activity()
market_provider: MarketDataProvider = create_binance_provider_from_settings(settings) if settings.app_mode in {"binance", "binance_account"} else SimulationMarketProvider()
account_provider = create_binance_account_provider_from_settings(settings) if settings.app_mode == "binance_account" else None
portfolio_price_provider = create_binance_portfolio_price_provider_from_settings(settings) if account_provider is not None else None
WATCHLIST_SYMBOLS = ("BTC", "ETH", "BNB")
explanation_provider = create_explanation_provider_from_settings(settings)


@app.get("/health")
def health() -> dict[str, str]:
    mode = settings.app_mode if settings.app_mode in {"simulation", "binance", "binance_account"} else "simulation"
    configured = not isinstance(explanation_provider, DisabledLLMProvider)
    return {"status": "ok", "mode": mode, "account_access": "read_only" if account_provider else "disabled", "order_capability": "disabled", "llm_provider": getattr(explanation_provider, "provider_name", "deterministic"), "llm_status": "configured" if configured and getattr(explanation_provider, "last_call_succeeded", None) is not False else "unavailable" if configured else "disabled", "llm_error": getattr(explanation_provider, "last_error_code", None) or "none"}


@app.get("/api/v1/market", response_model=list[AssetSnapshot])
async def markets() -> list[AssetSnapshot]:
    try:
        snapshots = await market_provider.get_snapshots(WATCHLIST_SYMBOLS)
        return [snapshots[symbol] for symbol in WATCHLIST_SYMBOLS]
    except InvalidSymbolError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MarketDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"error_code": "MARKET_DATA_UNAVAILABLE", "message": str(exc), "retryable": True}) from exc


@app.get("/api/v1/market/{symbol}", response_model=AssetSnapshot)
async def market(symbol: str) -> AssetSnapshot:
    try:
        return (await market_provider.get_snapshots([symbol]))[symbol.upper()]
    except InvalidSymbolError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MarketDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"error_code": "MARKET_DATA_UNAVAILABLE", "message": str(exc), "retryable": True}) from exc


@app.get("/api/v1/account", response_model=AccountSnapshot)
async def get_account() -> AccountSnapshot:
    if account_provider is None:
        raise HTTPException(status_code=409, detail={"error_code": "ACCOUNT_NOT_ENABLED", "message": "Authenticated account reads are disabled; simulation remains the default.", "retryable": False})
    try:
        result = await account_provider.get_account()
        activity.append(AuditEvent(request_id="account", stage="account", status="read", summary=f"Verified read-only account snapshot retrieved ({result.freshness})."))
        return result
    except AccountCredentialsError as exc:
        raise HTTPException(status_code=401, detail={"error_code": "ACCOUNT_CREDENTIALS_REJECTED", "message": str(exc), "retryable": False}) from exc
    except AccountPermissionError as exc:
        raise HTTPException(status_code=403, detail={"error_code": "ACCOUNT_PERMISSION_REJECTED", "message": str(exc), "retryable": False}) from exc
    except AccountDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"error_code": "ACCOUNT_DATA_UNAVAILABLE", "message": str(exc), "retryable": True}) from exc


@app.get("/api/v1/analyze/{symbol}")
async def analyze(symbol: str):
    symbol = symbol.upper()
    if symbol not in {"BTC", "ETH", "BNB"}:
        raise HTTPException(status_code=422, detail="Unsupported symbol")
    if settings.app_mode == "simulation":
        return report(symbol)
    try:
        current = (await market_provider.get_snapshots([symbol]))[symbol]
        return analyze_snapshot(current, explanation_provider=explanation_provider)
    except MarketDataUnavailableError as exc:
        raise HTTPException(status_code=503, detail={"error_code": "ANALYSIS_DATA_UNAVAILABLE", "message": str(exc), "retryable": True}) from exc


@app.get("/api/v1/portfolio", response_model=PortfolioSnapshot)
async def get_portfolio():
    if account_provider is not None:
        try:
            account = await account_provider.get_account()
            prices = await portfolio_price_provider.get_prices([balance.asset for balance in account.balances])
            result = value_account(account, prices)
            activity.append(AuditEvent(request_id="portfolio", stage="account", status="read", summary=f"Verified read-only portfolio valued from account and public market data ({result.freshness})."))
            return result
        except (AccountCredentialsError, AccountPermissionError) as exc:
            raise HTTPException(status_code=403, detail={"error_code": "ACCOUNT_PERMISSION_REJECTED", "message": str(exc), "retryable": False}) from exc
        except (AccountDataUnavailableError, MarketDataUnavailableError) as exc:
            raise HTTPException(status_code=503, detail={"error_code": "PORTFOLIO_DATA_UNAVAILABLE", "message": str(exc), "retryable": True}) from exc
    if settings.app_mode == "simulation":
        activity.append(AuditEvent(request_id="portfolio", stage="account", status="read", summary="Read-only portfolio snapshot retrieved."))
        return portfolio_snapshot()
    raise HTTPException(status_code=409, detail={"error_code": "ACCOUNT_NOT_ENABLED", "message": "Connect a verified read-only Binance account to view a live portfolio.", "retryable": False})


@app.post("/api/v1/advice", response_model=AdviceResponse)
async def advice(request: AdviceRequest) -> AdviceResponse:
    if account_provider is None or portfolio_price_provider is None:
        raise HTTPException(status_code=409, detail={"error_code": "ACCOUNT_NOT_ENABLED", "message": "Connect a verified read-only Binance account for portfolio advice.", "retryable": False})
    try:
        account = await account_provider.get_account()
        prices = await portfolio_price_provider.get_prices([balance.asset for balance in account.balances])
        portfolio = value_account(account, prices)
        context = {"total_value": portfolio.total_value, "stablecoin_percent": portfolio.stablecoin_percent, "concentration_risk": portfolio.concentration_risk.value, "priced_assets": [h.symbol for h in portfolio.holdings if h.price_status == "available"], "unpriced_assets": portfolio.unpriced_assets, "freshness": portfolio.freshness}
        if hasattr(explanation_provider, "generate_advice"):
            answer = explanation_provider.generate_advice(request.question, context)
            provider = getattr(explanation_provider, "provider_name", "deterministic") if not isinstance(explanation_provider, DisabledLLMProvider) and getattr(explanation_provider, "last_call_succeeded", False) else "deterministic"
        else:
            answer = "Review the priced and unpriced holdings above; no live language model is configured."
            provider = "deterministic"
        return AdviceResponse(answer=answer, provider=provider, source="binance", limitations=["Informational only; no orders or financial advice.", "Advice is limited to the supplied account and public market snapshots."])
    except (AccountCredentialsError, AccountPermissionError) as exc:
        raise HTTPException(status_code=403, detail={"error_code": "ACCOUNT_PERMISSION_REJECTED", "message": str(exc), "retryable": False}) from exc
    except (AccountDataUnavailableError, MarketDataUnavailableError) as exc:
        raise HTTPException(status_code=503, detail={"error_code": "ADVICE_DATA_UNAVAILABLE", "message": str(exc), "retryable": True}) from exc


@app.get("/api/v1/portfolio/suggestions", response_model=list[PortfolioSuggestion])
def get_portfolio_suggestions():
    if settings.app_mode != "simulation":
        raise HTTPException(status_code=409, detail={"error_code": "ACCOUNT_NOT_ENABLED", "message": "Live portfolio suggestions require a verified read-only account.", "retryable": False})
    activity.append(AuditEvent(request_id="suggestions", stage="analysis", status="generated", summary="Portfolio improvement suggestions generated without order capability."))
    return portfolio_suggestions()


@app.get("/api/v1/activity", response_model=list[AuditEvent])
def get_activity():
    return list(reversed(activity))


@app.post("/api/v1/simulation/reset")
def reset():
    if settings.app_mode != "simulation":
        raise HTTPException(status_code=409, detail={"error_code": "SIMULATION_DISABLED", "message": "Simulation mode is not active.", "retryable": False})
    activity.clear()
    activity.extend(initial_activity())
    return {"status": "reset", "mode": "simulation", "account_access": "read_only"}
