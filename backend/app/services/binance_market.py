"""Async Binance public market-data adapter.

Only the public, unsigned 24-hour ticker endpoint is used here. This module
does not know about credentials and contains no order or account operations.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import json
from email.utils import parsedate_to_datetime
import inspect
from time import monotonic
from typing import Any

try:
    import httpx
except ImportError:  # Keep simulation startup usable before optional deps are installed.
    httpx = None  # type: ignore[assignment]


_NETWORK_ERRORS = (
    tuple(error for error in (getattr(httpx, "TimeoutException", None), getattr(httpx, "NetworkError", None), OSError) if error is not None)
    or (Exception,)
)

from app.models.schemas import AssetSnapshot
from app.services.market_provider import InvalidSymbolError, MarketDataProvider, MarketDataUnavailableError


SUPPORTED_SYMBOLS = frozenset({"BTC", "ETH", "BNB"})


class BinanceMarketProvider:
    endpoint_path = "/api/v3/ticker/24hr"

    def __init__(
        self,
        *,
        base_url: str = "https://data-api.binance.vision",
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
        cache_ttl_seconds: float = 15.0,
        stale_ttl_seconds: float = 300.0,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Any] = asyncio.sleep,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds) if httpx is not None else timeout_seconds
        self.max_retries = max(0, max_retries)
        self.cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self.stale_ttl_seconds = max(0.0, stale_ttl_seconds)
        self._client = client
        self._sleep = sleep
        self._clock = clock
        self._cache: dict[str, tuple[AssetSnapshot, float]] = {}

    async def get_snapshots(self, symbols: Sequence[str]) -> dict[str, AssetSnapshot]:
        requested = self._validate_symbols(symbols)
        now = self._clock()
        fresh = {symbol: self._cache[symbol][0] for symbol in requested if symbol in self._cache and now - self._cache[symbol][1] <= self.cache_ttl_seconds}
        missing = [symbol for symbol in requested if symbol not in fresh]
        if not missing:
            return fresh

        try:
            fetched = await self._fetch(missing)
        except Exception as exc:
            fallback = self._stale_fallback(missing, now)
            if len(fallback) == len(missing):
                return {**fresh, **fallback}
            if isinstance(exc, MarketDataUnavailableError):
                raise
            raise MarketDataUnavailableError(f"Binance market data unavailable: {exc}") from exc

        result = {**fresh, **fetched}
        if len(result) != len(requested):
            fallback = self._stale_fallback([symbol for symbol in requested if symbol not in result], now)
            result.update(fallback)
        if len(result) != len(requested):
            missing_symbols = ", ".join(symbol for symbol in requested if symbol not in result)
            raise MarketDataUnavailableError(f"No usable market data for: {missing_symbols}")
        return result

    async def _fetch(self, symbols: Sequence[str]) -> dict[str, AssetSnapshot]:
        params = {"symbols": json.dumps([f"{symbol}USDT" for symbol in symbols], separators=(",", ":"))}
        own_client = self._client is None
        if self._client is None and httpx is None:
            raise MarketDataUnavailableError("httpx is not installed; install backend requirements first")
        client = self._client or httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)  # type: ignore[union-attr]
        try:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(self.endpoint_path, params=params)
                except _NETWORK_ERRORS as exc:
                    if attempt >= self.max_retries:
                        raise MarketDataUnavailableError("Binance request timed out or failed on the network") from exc
                    await self._wait(self._backoff(attempt))
                    continue

                if response.status_code in {429, 418}:
                    if attempt >= self.max_retries:
                        raise MarketDataUnavailableError(f"Binance rate limit response ({response.status_code})")
                    await self._wait(self._retry_after(response, attempt))
                    continue
                if response.status_code >= 400:
                    raise MarketDataUnavailableError(f"Binance returned HTTP {response.status_code}")
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise MarketDataUnavailableError("Binance returned malformed JSON") from exc
                return self._parse_payload(payload)
        finally:
            if own_client:
                await client.aclose()
        raise MarketDataUnavailableError("Binance request exhausted retries")

    def _parse_payload(self, payload: Any) -> dict[str, AssetSnapshot]:
        if not isinstance(payload, list):
            raise MarketDataUnavailableError("Binance response was not a ticker list")
        parsed: dict[str, AssetSnapshot] = {}
        retrieved_at = datetime.now(timezone.utc)
        for item in payload:
            if not isinstance(item, dict) or not isinstance(item.get("symbol"), str):
                continue
            pair = item["symbol"].upper()
            if not pair.endswith("USDT") or pair[:-4] not in SUPPORTED_SYMBOLS:
                continue
            symbol = pair[:-4]
            try:
                close_time = int(item["closeTime"])
                snapshot = AssetSnapshot(
                    symbol=symbol,
                    price=float(item["lastPrice"]),
                    change_24h=float(item["priceChangePercent"]),
                    volume_24h=float(item["quoteVolume"] if "quoteVolume" in item else item["volume"]),
                    timestamp=datetime.fromtimestamp(close_time / 1000, tz=timezone.utc),
                    retrieved_at=retrieved_at,
                    source="binance",
                    freshness="fresh",
                )
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
            parsed[symbol] = snapshot
        if not parsed:
            raise MarketDataUnavailableError("Binance response contained no valid supported symbols")
        fetched_at = self._clock()
        for symbol, snapshot in parsed.items():
            self._cache[symbol] = (snapshot, fetched_at)
        return parsed

    def _stale_fallback(self, symbols: Sequence[str], now: float) -> dict[str, AssetSnapshot]:
        fallback: dict[str, AssetSnapshot] = {}
        for symbol in symbols:
            cached = self._cache.get(symbol)
            if cached is None or now - cached[1] > self.stale_ttl_seconds:
                continue
            snapshot = cached[0].model_copy(update={"freshness": "stale"})
            fallback[symbol] = snapshot
        return fallback

    @staticmethod
    def _validate_symbols(symbols: Sequence[str]) -> list[str]:
        normalized = [symbol.upper().strip() for symbol in symbols]
        invalid = [symbol for symbol in normalized if symbol not in SUPPORTED_SYMBOLS]
        if invalid or not normalized:
            raise InvalidSymbolError(f"Unsupported symbol(s): {', '.join(invalid or normalized)}")
        if len(set(normalized)) != len(normalized):
            normalized = list(dict.fromkeys(normalized))
        return normalized

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(2.0, 0.25 * (2**attempt))

    async def _wait(self, delay: float) -> None:
        result = self._sleep(delay)
        if inspect.isawaitable(result):
            await result

    def _retry_after(self, response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return min(30.0, max(0.0, float(value)))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return min(30.0, max(0.0, retry_at.timestamp() - datetime.now(timezone.utc).timestamp()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return self._backoff(attempt)


def create_binance_provider_from_settings(settings: Any) -> MarketDataProvider:
    return BinanceMarketProvider(
        base_url=settings.binance_base_url,
        timeout_seconds=settings.market_timeout_seconds,
        max_retries=settings.market_max_retries,
        cache_ttl_seconds=settings.market_cache_ttl_seconds,
        stale_ttl_seconds=settings.market_stale_ttl_seconds,
    )
