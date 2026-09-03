import asyncio

import pytest

from app.services.binance_portfolio_prices import BinancePortfolioPriceProvider
from app.services.market_provider import InvalidSymbolError, MarketDataUnavailableError


class FakeResponse:
    def __init__(self, payload=None, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def get(self, path, **kwargs):
        self.calls.append((path, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def aclose(self):
        return None


def ticker(symbol, price):
    return {"symbol": symbol, "price": str(price)}


def provider(client, **kwargs):
    return BinancePortfolioPriceProvider(client=client, sleep=lambda _: asyncio.sleep(0), **kwargs)


def test_resolves_direct_and_bridge_prices_with_one_unsigned_request():
    client = FakeClient([FakeResponse([
        ticker("BTCUSDT", 60000),
        ticker("ETHUSDT", 3000),
        ticker("BNBUSDT", 600),
        ticker("DIRECTUSDT", 2),
        ticker("ALPHABTC", 0.0001),
        ticker("BETAETH", 0.01),
        ticker("GAMMABNB", 0.1),
    ])])
    result = asyncio.run(provider(client).get_prices(["direct", "alpha", "beta", "gamma"]))

    assert result["DIRECT"].price == 2
    assert result["ALPHA"].price == 6
    assert result["BETA"].price == 30
    assert result["GAMMA"].price == 60
    assert all(snapshot.freshness == "fresh" for snapshot in result.values())
    assert client.calls == [("/api/v3/ticker/price", {})]


def test_unknown_asset_is_omitted_instead_of_inventing_a_price():
    result = asyncio.run(provider(FakeClient([FakeResponse([ticker("BTCUSDT", 60000)])])).get_prices(["UNKNOWN"]))
    assert result == {}


def test_invalid_asset_is_rejected_before_network_call():
    client = FakeClient([])
    with pytest.raises(InvalidSymbolError):
        asyncio.run(provider(client).get_prices(["bad-symbol"]))
    assert client.calls == []


def test_malformed_or_empty_price_book_is_unavailable():
    with pytest.raises(MarketDataUnavailableError):
        asyncio.run(provider(FakeClient([FakeResponse({"symbol": "BTCUSDT"})])).get_prices(["BTC"]))
    with pytest.raises(MarketDataUnavailableError):
        asyncio.run(provider(FakeClient([FakeResponse([ticker("BTCUSDT", "nan")])])).get_prices(["BTC"]))


@pytest.mark.parametrize("status", [429, 418])
def test_rate_limit_retries_and_honors_retry_after(status):
    waits = []
    client = FakeClient([FakeResponse(status_code=status, headers={"Retry-After": "2"}), FakeResponse([ticker("BTCUSDT", 60000)])])
    service = BinancePortfolioPriceProvider(client=client, max_retries=1, sleep=lambda delay: waits.append(delay))
    result = asyncio.run(service.get_prices(["BTC"]))
    assert result["BTC"].price == 60000
    assert waits == [2.0]


def test_cache_avoids_request_and_bounded_stale_cache_is_fallback():
    now = [100.0]
    client = FakeClient([FakeResponse([ticker("BTCUSDT", 60000)]), OSError("offline")])
    service = BinancePortfolioPriceProvider(client=client, max_retries=0, cache_ttl_seconds=10, stale_ttl_seconds=100, clock=lambda: now[0])

    asyncio.run(service.get_prices(["BTC"]))
    now[0] = 105
    cached = asyncio.run(service.get_prices(["BTC"]))
    assert cached["BTC"].freshness == "fresh"
    assert len(client.calls) == 1

    now[0] = 111
    stale = asyncio.run(service.get_prices(["BTC"]))
    assert stale["BTC"].freshness == "stale"
    assert len(client.calls) == 2
