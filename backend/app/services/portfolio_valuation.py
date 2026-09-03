"""Read-only valuation of verified account balances using public prices."""

from collections.abc import Mapping

from app.models.schemas import AccountSnapshot, AssetSnapshot, PortfolioHolding, PortfolioPosition, PortfolioSnapshot, RiskLevel


STABLECOINS = frozenset({"USDT", "USDC", "BUSD", "FDUSD", "DAI", "TUSD"})


def value_account(account: AccountSnapshot, market: Mapping[str, AssetSnapshot]) -> PortfolioSnapshot:
    valued: list[tuple[str, float, float]] = []
    unpriced: list[str] = []
    holding_rows: list[tuple[str, float, float | None, float | None, str, str]] = []
    for balance in account.balances:
        if balance.total <= 0:
            continue
        if balance.asset in STABLECOINS:
            unit_price = 1.0
            freshness = account.freshness
        elif balance.asset in market:
            unit_price = market[balance.asset].price
            freshness = market[balance.asset].freshness
        else:
            unpriced.append(balance.asset)
            holding_rows.append((balance.asset, balance.total, None, None, "unpriced", "stale" if account.freshness == "stale" else "fresh"))
            continue
        holding_rows.append((balance.asset, balance.total, unit_price, balance.total * unit_price, "available", freshness))
        valued.append((balance.asset, balance.total, balance.total * unit_price))

    total_value = sum(value for _, _, value in valued)
    positions = [
        PortfolioPosition(symbol=asset, quantity=quantity, market_value=round(value, 8), allocation_percent=round(value / total_value * 100, 4) if total_value else 0)
        for asset, quantity, value in valued
    ]
    holdings = [
        PortfolioHolding(
            symbol=asset,
            quantity=quantity,
            market_value=round(value, 8) if value is not None else None,
            allocation_percent=round(value / total_value * 100, 4) if value is not None and total_value else 0 if value is not None else None,
            unit_price=price,
            price_status=status,
            freshness=freshness,
        )
        for asset, quantity, price, value, status, freshness in holding_rows
    ]
    stablecoin_value = sum(value for asset, _, value in valued if asset in STABLECOINS)
    largest_allocation = max((position.allocation_percent for position in positions), default=0)
    concentration = RiskLevel.HIGH if largest_allocation > 50 else RiskLevel.MEDIUM if largest_allocation > 35 else RiskLevel.LOW
    freshness = "stale" if account.freshness == "stale" or any(item.freshness == "stale" for item in market.values()) else "fresh"
    return PortfolioSnapshot(
        total_value=round(total_value, 8),
        stablecoin_percent=round(stablecoin_value / total_value * 100, 4) if total_value else 0,
        concentration_risk=concentration,
        positions=positions,
        holdings=holdings,
        source="binance",
        permission_scope="read_only",
        fetched_at=account.fetched_at,
        freshness=freshness,
        unpriced_assets=sorted(unpriced),
    )
