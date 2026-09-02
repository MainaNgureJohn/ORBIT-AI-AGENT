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

NOW = datetime.now(timezone.utc)

FIXTURES = {
    "BTC": {"price": 68420.0, "change": 2.84, "volume": 28_400_000_000, "momentum": 74, "volatility": 42, "trend": "Bullish", "volume_signal": "Above average", "sr": "$66,800 support · $70,200 resistance"},
    "ETH": {"price": 3528.40, "change": 1.26, "volume": 14_100_000_000, "momentum": 64, "volatility": 49, "trend": "Constructive", "volume_signal": "Steady", "sr": "$3,420 support · $3,680 resistance"},
    "BNB": {"price": 612.75, "change": -0.42, "volume": 1_900_000_000, "momentum": 48, "volatility": 35, "trend": "Neutral", "volume_signal": "Below average", "sr": "$590 support · $640 resistance"},
}


def snapshot(symbol: str) -> AssetSnapshot:
    item = FIXTURES[symbol]
    return AssetSnapshot(symbol=symbol, price=item["price"], change_24h=item["change"], volume_24h=item["volume"], timestamp=NOW)


def report(symbol: str) -> AnalysisReport:
    item = FIXTURES[symbol]
    market = max(0, min(100, 50 + item["change"] * 8))
    technical = round((item["momentum"] + (100 - item["volatility"])) / 2, 1)
    risk_score = round(100 - item["volatility"], 1)
    final = round(market * .30 + technical * .35 + risk_score * .20, 1)
    risk = RiskLevel.LOW if item["volatility"] < 40 else RiskLevel.MEDIUM if item["volatility"] < 60 else RiskLevel.HIGH
    reasons = [f"{item['trend']} trend with {item['change']:+.2f}% 24-hour movement", f"Momentum is {item['momentum']}/100", f"Volatility risk is {item['volatility']}/100"]
    limitations = ["On-chain data is unavailable in simulation mode", "Fixture prices are not live market data"]
    return AnalysisReport(asset=symbol, snapshot=snapshot(symbol), metrics=TechnicalMetrics(trend=item["trend"], momentum=item["momentum"], volatility=item["volatility"], volume_signal=item["volume_signal"], support_resistance=item["sr"]), score=ScoreBreakdown(market=market, technical=technical, on_chain=None, risk=risk_score, final=final), risk_level=risk, reasons=reasons, limitations=limitations, generated_at=NOW)


def portfolio_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        total_value=1250.25,
        stablecoin_percent=28,
        concentration_risk=RiskLevel.MEDIUM,
        positions=[
            PortfolioPosition(symbol="BTC", quantity=0.007676, market_value=525.16, allocation_percent=42),
            PortfolioPosition(symbol="ETH", quantity=0.1063, market_value=375.09, allocation_percent=30),
            PortfolioPosition(symbol="USDT", quantity=350, market_value=350, allocation_percent=28),
        ],
        fetched_at=NOW,
    )


def portfolio_suggestions() -> list[PortfolioSuggestion]:
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
            generated_at=NOW,
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
            generated_at=NOW,
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
            generated_at=NOW,
        ),
    ]


def initial_activity() -> list[AuditEvent]:
    return [AuditEvent(request_id="boot", stage="system", status="ready", summary="Read-only simulation initialized; order functionality does not exist.")]
