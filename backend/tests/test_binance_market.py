import asyncio
import json

import pytest

from app.models.schemas import AssetSnapshot
from app.services.binance_market import BinanceMarketProvider
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


def ticker(symbol="BTCUSDT", price="68000.10"):
    return {"symbol": symbol, "lastPrice": price, "priceChangePercent": "2.50", "quoteVolume": "1000000", "closeTime": 1725000000000}


def provider(client, **kwargs):
    return BinanceMarketProvider(client=client, sleep=lambda _: asyncio.sleep(0), **kwargs)


def test_success_parses_all_symbols_with_one_multi_symbol_request():
    client = FakeClient([FakeResponse([ticker(), ticker("ETHUSDT", "3500"), ticker("BNBUSDT", "600")])])
    result = asyncio.run(provider(client).get_snapshots(["BTC", "ETH", "BNB"]))
    assert set(result) == {"BTC", "ETH", "BNB"}
    assert isinstance(result["BTC"], AssetSnapshot)
    assert result["BTC"].source == "binance"
    assert result["BTC"].freshness == "fresh"
    assert len(client.calls) == 1
    assert client.calls[0][0] == "/api/v3/ticker/24hr"
    assert json.loads(client.calls[0][1]["params"]["symbols"]) == ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    assert "headers" not in client.calls[0][1]


def test_invalid_symbols_are_rejected_before_network_call():
    client = FakeClient([])
    with pytest.raises(InvalidSymbolError):
        asyncio.run(provider(client).get_snapshots(["DOGE"]))
    assert client.calls == []


def test_malformed_response_is_unavailable():
    with pytest.raises(MarketDataUnavailableError):
        asyncio.run(provider(FakeClient([FakeResponse({"symbol": "BTCUSDT"})])).get_snapshots(["BTC"]))


def test_network_failure_retries_then_reports_unavailable():
    client = FakeClient([OSError("offline"), OSError("offline"), OSError("offline")])
    with pytest.raises(MarketDataUnavailableError):
        asyncio.run(provider(client, max_retries=2).get_snapshots(["BTC"]))
    assert len(client.calls) == 3


@pytest.mark.parametrize("status", [429, 418])
def test_rate_limit_honors_retry_after_and_then_succeeds(status):
    waits = []
    client = FakeClient([FakeResponse(status_code=status, headers={"Retry-After": "3"}), FakeResponse([ticker()])])
    service = BinanceMarketProvider(client=client, sleep=lambda delay: waits.append(delay), max_retries=1)
    result = asyncio.run(service.get_snapshots(["BTC"]))
    assert result["BTC"].price == 68000.10
    assert waits == [3.0]


def test_cache_avoids_second_request_and_stale_cache_is_fallback():
    now = [100.0]
    client = FakeClient([FakeResponse([ticker()]), OSError("offline")])
    service = BinanceMarketProvider(client=client, cache_ttl_seconds=10, stale_ttl_seconds=100, clock=lambda: now[0], sleep=lambda _: asyncio.sleep(0))
    first = asyncio.run(service.get_snapshots(["BTC"]))
    now[0] = 105
    cached = asyncio.run(service.get_snapshots(["BTC"]))
    assert len(client.calls) == 1
    assert cached["BTC"].freshness == "fresh"
    now[0] = 111
    stale = asyncio.run(service.get_snapshots(["BTC"]))
    assert stale["BTC"].freshness == "stale"
    assert first["BTC"].source == "binance"


def test_partial_response_uses_stale_entry_for_missing_symbol():
    now = [100.0]
    client = FakeClient([FakeResponse([ticker("ETHUSDT", "3500")]), FakeResponse([ticker("BTCUSDT", "68000")])])
    service = BinanceMarketProvider(client=client, cache_ttl_seconds=1, stale_ttl_seconds=100, clock=lambda: now[0], sleep=lambda _: asyncio.sleep(0))
    asyncio.run(service.get_snapshots(["ETH"]))
    now[0] = 102
    result = asyncio.run(service.get_snapshots(["BTC", "ETH"]))
    assert result["BTC"].freshness == "fresh"
    assert result["ETH"].freshness == "stale"
