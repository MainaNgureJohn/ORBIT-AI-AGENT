from datetime import datetime, timezone

from app.models.schemas import AccountBalance, AccountSnapshot, AssetSnapshot
from app.services.portfolio_valuation import value_account


def test_read_only_account_is_valued_from_public_market_data():
    account = AccountSnapshot(
        balances=[AccountBalance(asset="BTC", free=0.5, locked=0, total=0.5), AccountBalance(asset="USDT", free=100, locked=0, total=100)],
        fetched_at=datetime.now(timezone.utc),
    )
    market = {"BTC": AssetSnapshot(symbol="BTC", price=10, change_24h=0, volume_24h=1, timestamp=datetime.now(timezone.utc), source="binance", freshness="fresh")}
    result = value_account(account, market)
    assert result.source == "binance"
    assert result.permission_scope == "read_only"
    assert result.total_value == 105
    assert result.stablecoin_percent == round(100 / 105 * 100, 4)
    assert result.freshness == "fresh"


def test_unpriced_assets_are_explicit_and_not_silently_valued():
    account = AccountSnapshot(balances=[AccountBalance(asset="XYZ", free=5, locked=0, total=5)], fetched_at=datetime.now(timezone.utc))
    result = value_account(account, {})
    assert result.total_value == 0
    assert result.positions == []
    assert result.unpriced_assets == ["XYZ"]
