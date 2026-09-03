import asyncio

from app.main import app
from app.main import get_account, market, markets
from app.services.simulation import portfolio_snapshot, portfolio_suggestions, report, snapshot


def test_score_is_deterministic_and_bounded():
    result = report("BTC")
    assert result.score.final == 56.5
    assert 0 <= result.score.final <= 100
    assert result.score.on_chain is None


def test_portfolio_is_explicitly_read_only():
    result = portfolio_snapshot()
    assert result.permission_scope == "read_only"
    assert result.total_value == 1250.25
    assert sum(position.allocation_percent for position in result.positions) == 100


def test_suggestions_contain_no_execution_fields():
    results = portfolio_suggestions()
    assert len(results) == 3
    forbidden = {"side", "quantity", "order_id", "confirmation_state", "execute"}
    assert all(forbidden.isdisjoint(result.model_dump()) for result in results)
    assert all("cannot place orders" in result.disclaimer for result in results)


def test_api_exposes_no_order_routes():
    paths = {route.path for route in app.routes}
    assert "/api/v1/portfolio" in paths
    assert "/api/v1/portfolio/suggestions" in paths
    assert not any("order" in path or "trade-proposal" in path for path in paths)


def test_market_route_defaults_to_simulation_provider():
    result = asyncio.run(market("btc"))
    assert result.source == "simulation"
    assert result.freshness == "fixture"
    assert result.retrieved_at == result.timestamp


def test_simulation_fixture_timestamp_is_refreshed_per_read():
    first = snapshot("BTC")
    second = snapshot("BTC")
    assert second.timestamp >= first.timestamp
    assert second.retrieved_at == second.timestamp


def test_watchlist_route_returns_all_symbols_from_provider_contract():
    result = asyncio.run(markets())
    assert [snapshot.symbol for snapshot in result] == ["BTC", "ETH", "BNB"]
    assert all(snapshot.source == "simulation" for snapshot in result)


def test_authenticated_account_route_is_disabled_in_simulation():
    try:
        asyncio.run(get_account())
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    else:
        raise AssertionError("account reads must remain disabled in simulation mode")
