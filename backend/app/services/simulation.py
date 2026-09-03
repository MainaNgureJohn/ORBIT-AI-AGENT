from datetime import datetime, timezone

from app.models.schemas import (
    AnalysisReport,
    AssetSnapshot,
    AuditEvent,
    PortfolioPosition,
    PortfolioSnapshot,
    PortfolioSuggestion,
    RiskLevel,
    ScoreBreakdown,
    TechnicalMetrics,
)
from app.services.analysis_engine import analyze_snapshot

FIXTURES = {
    "BTC": {"price": 68420.0, "change": 2.84, "volume": 28_400_000_000, "momentum": 74, "volatility": 42, "trend": "Bullish", "volume_signal": "Above average", "sr": "$66,800 support · $70,200 resistance"},
    "ETH": {"price": 3528.40, "change": 1.26, "volume": 14_100_000_000, "momentum": 64, "volatility": 49, "trend": "Constructive", "volume_signal": "Steady", "sr": "$3,420 support · $3,680 resistance"},
    "BNB": {"price": 612.75, "change": -0.42, "volume": 1_900_000_000, "momentum": 48, "volatility": 35, "trend": "Neutral", "volume_signal": "Below average", "sr": "$590 support · $640 resistance"},
}


def snapshot(symbol: str, timestamp: datetime | None = None) -> AssetSnapshot:
    item = FIXTURES[symbol]
    timestamp = timestamp or datetime.now(timezone.utc)
    return AssetSnapshot(symbol=symbol, price=item["price"], change_24h=item["change"], volume_24h=item["volume"], timestamp=timestamp, retrieved_at=timestamp)


def report(symbol: str) -> AnalysisReport:
    item = FIXTURES[symbol]
    current = snapshot(symbol)
    metrics = TechnicalMetrics(trend=item["trend"], momentum=item["momentum"], volatility=item["volatility"], volume_signal=item["volume_signal"], support_resistance=item["sr"])
    return analyze_snapshot(current, metrics=metrics, limitations=["On-chain data is unavailable in simulation mode"])


def portfolio_snapshot() -> PortfolioSnapshot:
    fetched_at = datetime.now(timezone.utc)
    return PortfolioSnapshot(
        total_value=1250.25,
        stablecoin_percent=28,
        concentration_risk=RiskLevel.MEDIUM,
        positions=[
            PortfolioPosition(symbol="BTC", quantity=0.007676, market_value=525.16, allocation_percent=42),
            PortfolioPosition(symbol="ETH", quantity=0.1063, market_value=375.09, allocation_percent=30),
            PortfolioPosition(symbol="USDT", quantity=350, market_value=350, allocation_percent=28),
        ],
        fetched_at=fetched_at,
    )


def portfolio_suggestions() -> list[PortfolioSuggestion]:
    generated_at = datetime.now(timezone.utc)
    return [
        PortfolioSuggestion(
            id="suggestion_reduce_btc_concentration",
            symbol="BTC",
            action="CONSIDER_REDUCE",
            current_allocation_percent=42,
            target_range="35–40%",
            risk=RiskLevel.MEDIUM,
            confidence_score=72,
            rationale=[
                "BTC is the largest position in the simulated portfolio.",
                "A smaller concentration may reduce single-asset drawdown sensitivity.",
            ],
            generated_at=generated_at,
        ),
        PortfolioSuggestion(
            id="suggestion_consider_bnb_diversification",
            symbol="BNB",
            action="CONSIDER_BUY",
            current_allocation_percent=0,
            target_range="5–8%",
            risk=RiskLevel.MEDIUM,
            confidence_score=61,
            rationale=[
                "The simulated portfolio has no BNB exposure.",
                "A small allocation could improve diversification without using the full stablecoin buffer.",
            ],
            generated_at=generated_at,
        ),
        PortfolioSuggestion(
            id="suggestion_hold_reserve",
            symbol="USDT",
            action="HOLD",
            current_allocation_percent=28,
            target_range="20–30%",
            risk=RiskLevel.LOW,
            confidence_score=84,
            rationale=[
                "The reserve remains inside the simulated target range.",
                "Liquidity gives the user flexibility during volatile conditions.",
            ],
            generated_at=generated_at,
        ),
    ]


def initial_activity() -> list[AuditEvent]:
    return [AuditEvent(request_id="boot", stage="system", status="ready", summary="Read-only simulation initialized; order functionality does not exist.")]
