"""Deterministic, testable analysis and opportunity scoring."""

from datetime import datetime, timezone

from app.models.schemas import AnalysisReport, AssetSnapshot, RiskLevel, ScoreBreakdown, TechnicalMetrics
from app.services.llm_provider import DeterministicExplanationProvider, ExplanationProvider


WEIGHTS = {"market": 0.30, "technical": 0.35, "on_chain": 0.15, "risk": 0.20}


def clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def calculate_score(*, market: float, technical: float, risk: float, on_chain: float | None = None) -> ScoreBreakdown:
    """Calculate the documented weighted score; unavailable inputs contribute zero explicitly."""
    components = {"market": clamp(market), "technical": clamp(technical), "risk": clamp(risk), "on_chain": None if on_chain is None else clamp(on_chain)}
    final = sum((components[name] or 0.0) * weight for name, weight in WEIGHTS.items())
    missing = [name for name, value in components.items() if value is None]
    return ScoreBreakdown(
        market=components["market"] or 0.0,
        technical=components["technical"] or 0.0,
        on_chain=components["on_chain"],
        risk=components["risk"] or 0.0,
        final=round(final, 1),
        missing_components=missing,
    )


def metrics_from_snapshot(snapshot: AssetSnapshot) -> TechnicalMetrics:
    """Derive conservative metrics from the available 24-hour snapshot only."""
    change = snapshot.change_24h
    momentum = clamp(50 + change * 8)
    volatility = clamp(abs(change) * 15)
    trend = "Bullish" if change >= 2 else "Constructive" if change > 0 else "Neutral" if change > -2 else "Bearish"
    volume_signal = "Unavailable without historical baseline"
    return TechnicalMetrics(
        trend=trend,
        momentum=round(momentum, 1),
        volatility=round(volatility, 1),
        volume_signal=volume_signal,
        support_resistance="Unavailable from 24-hour ticker alone",
    )


def analyze_snapshot(
    snapshot: AssetSnapshot,
    *,
    metrics: TechnicalMetrics | None = None,
    on_chain: float | None = None,
    limitations: list[str] | None = None,
    explanation_provider: ExplanationProvider | None = None,
) -> AnalysisReport:
    metrics = metrics or metrics_from_snapshot(snapshot)
    market_score = clamp(50 + snapshot.change_24h * 8)
    technical_score = (metrics.momentum + (100 - metrics.volatility)) / 2
    risk_score = 100 - metrics.volatility
    limitations = list(limitations or [])
    if on_chain is None:
        limitations.append("On-chain data is unavailable; its weighted component contributes zero.")
    if snapshot.source == "simulation":
        limitations.append("Fixture prices are not live market data.")
    elif snapshot.freshness == "stale":
        limitations.append("The latest refresh failed; this snapshot is from the bounded stale cache.")
    reasons = [
        f"{metrics.trend} trend with {snapshot.change_24h:+.2f}% 24-hour movement",
        f"Momentum is {metrics.momentum:g}/100",
        f"Volatility risk is {metrics.volatility:g}/100",
    ]
    generated_at = datetime.now(timezone.utc)
    report = AnalysisReport(
        asset=snapshot.symbol,
        snapshot=snapshot,
        metrics=metrics,
        score=calculate_score(market=market_score, technical=technical_score, risk=risk_score, on_chain=on_chain),
        risk_level=RiskLevel.LOW if metrics.volatility < 40 else RiskLevel.MEDIUM if metrics.volatility < 60 else RiskLevel.HIGH,
        reasons=reasons,
        limitations=limitations,
        generated_at=generated_at,
    )
    provider = explanation_provider or DeterministicExplanationProvider()
    return report.model_copy(update={"explanation": provider.generate_explanation(report)})
