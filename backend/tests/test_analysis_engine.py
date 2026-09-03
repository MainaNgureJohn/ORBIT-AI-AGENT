from datetime import datetime, timezone

from app.models.schemas import AssetSnapshot, TechnicalMetrics
from app.services.analysis_engine import analyze_snapshot, calculate_score, metrics_from_snapshot
from app.services.llm_provider import DisabledLLMProvider
from app.services.simulation import report


def test_missing_on_chain_is_explicit_and_not_positive():
    score = calculate_score(market=80, technical=70, risk=60)
    assert score.final == 60.5
    assert score.on_chain is None
    assert score.missing_components == ["on_chain"]


def test_score_inputs_are_clamped_to_zero_to_hundred():
    score = calculate_score(market=120, technical=-10, risk=60, on_chain=200)
    assert score.market == 100
    assert score.technical == 0
    assert score.on_chain == 100
    assert score.final == 57.0


def test_metrics_from_snapshot_are_deterministic_and_bounded():
    snapshot = AssetSnapshot(symbol="BTC", price=100, change_24h=-4, volume_24h=1000, timestamp=datetime.now(timezone.utc))
    metrics = metrics_from_snapshot(snapshot)
    assert metrics.trend == "Bearish"
    assert metrics.momentum == 18
    assert metrics.volatility == 60
    assert 0 <= metrics.momentum <= 100
    assert 0 <= metrics.volatility <= 100


def test_analysis_uses_replaceable_explanation_provider():
    snapshot = AssetSnapshot(symbol="BTC", price=100, change_24h=1, volume_24h=1000, timestamp=datetime.now(timezone.utc))
    metrics = TechnicalMetrics(trend="Constructive", momentum=58, volatility=20, volume_signal="Unknown", support_resistance="Unknown")
    result = analyze_snapshot(snapshot, metrics=metrics, explanation_provider=DisabledLLMProvider())
    assert result.explanation is not None
    assert "BTC" in result.explanation
    assert "On-chain data is unavailable" in result.limitations[0]


def test_simulation_report_keeps_fixture_score_and_labels_missing_data():
    result = report("BTC")
    assert result.score.final == 56.5
    assert result.score.missing_components == ["on_chain"]
    assert result.explanation and "informational opportunity score" in result.explanation
