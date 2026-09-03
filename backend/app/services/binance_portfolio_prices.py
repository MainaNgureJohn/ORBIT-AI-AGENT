"""Public Binance prices for valuing arbitrary read-only account assets.

The provider downloads the unsigned symbol-price book once, then resolves an
asset through a direct USDT pair or a BTC/ETH/BNB bridge. Unsupported assets
are deliberately omitted so the portfolio layer can report them as unpriced.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import inspect
import math
import re
from time import monotonic
from typing import Any

try:
    import httpx
except ImportError:  # Keep simulation startup usable before optional deps are installed.
    httpx = None  # type: ignore[assignment]

from app.models.schemas import AssetSnapshot
from app.services.market_provider import InvalidSymbolError, MarketDataUnavailableError


_NETWORK_ERRORS = (
    tuple(error for error in (getattr(httpx, "TimeoutException", None), getattr(httpx, "NetworkError", None), OSError) if error is not None)
    or (Exception,)
)
_ASSET_PATTERN = re.compile(r"^[A-Z0-9]{1,20}$")
_BRIDGE_ASSETS = ("BTC", "ETH", "BNB")


class BinancePortfolioPriceProvider:
    endpoint_path = "/api/v3/ticker/price"

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
        self._cache: tuple[dict[str, float], float] | None = None

    async def get_prices(self, assets: Sequence[str]) -> dict[str, AssetSnapshot]:
        requested = self._validate_assets(assets)
        if not requested:
            return {}

        now = self._clock()
        freshness = "fresh"
        if self._cache is not None and now - self._cache[1] <= self.cache_ttl_seconds:
            price_book = self._cache[0]
        else:
            try:
                price_book = await self._fetch_price_book()
            except MarketDataUnavailableError:
                if self._cache is None or now - self._cache[1] > self.stale_ttl_seconds:
                    raise
                price_book = self._cache[0]
                freshness = "stale"

        retrieved_at = datetime.now(timezone.utc)
        resolved: dict[str, AssetSnapshot] = {}
        for asset in requested:
            price = self._resolve_usdt_price(asset, price_book)
            if price is None:
                continue
            resolved[asset] = AssetSnapshot(
                symbol=asset,
                price=price,
                change_24h=0,
                volume_24h=0,
                timestamp=retrieved_at,
                retrieved_at=retrieved_at,
                source="binance",
                freshness=freshness,
            )
        return resolved

    async def _fetch_price_book(self) -> dict[str, float]:
        own_client = self._client is None
        if self._client is None and httpx is None:
            raise MarketDataUnavailableError("httpx is not installed; install backend requirements first")
        client = self._client or httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)  # type: ignore[union-attr]
        try:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(self.endpoint_path)
                except _NETWORK_ERRORS as exc:
                    if attempt >= self.max_retries:
                        raise MarketDataUnavailableError("Binance price request timed out or failed on the network") from exc
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
                    raise MarketDataUnavailableError("Binance returned malformed price JSON") from exc
                price_book = self._parse_price_book(payload)
                self._cache = (price_book, self._clock())
                return price_book
        finally:
            if own_client:
                await client.aclose()
        raise MarketDataUnavailableError("Binance price request exhausted retries")

    @staticmethod
    def _parse_price_book(payload: Any) -> dict[str, float]:
        if not isinstance(payload, list):
            raise MarketDataUnavailableError("Binance price response was not a ticker list")
        prices: dict[str, float] = {}
        for item in payload:
            if not isinstance(item, dict) or not isinstance(item.get("symbol"), str):
                continue
            try:
                price = float(item["price"])
            except (KeyError, TypeError, ValueError):
                continue
            if price > 0 and math.isfinite(price):
                prices[item["symbol"].upper()] = price
        if not prices:
            raise MarketDataUnavailableError("Binance price response contained no usable prices")
        return prices

    @staticmethod
    def _resolve_usdt_price(asset: str, prices: dict[str, float]) -> float | None:
        direct = prices.get(f"{asset}USDT")
        if direct is not None:
            return direct
        for bridge in _BRIDGE_ASSETS:
            asset_bridge = prices.get(f"{asset}{bridge}")
            bridge_usdt = prices.get(f"{bridge}USDT")
            if asset_bridge is not None and bridge_usdt is not None:
                price = asset_bridge * bridge_usdt
                if price > 0 and math.isfinite(price):
                    return price
        return None

    @staticmethod
    def _validate_assets(assets: Sequence[str]) -> list[str]:
        normalized = list(dict.fromkeys(asset.upper().strip() for asset in assets))
        invalid = [asset for asset in normalized if not _ASSET_PATTERN.fullmatch(asset)]
        if invalid:
            raise InvalidSymbolError(f"Invalid account asset symbol(s): {', '.join(invalid)}")
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


def create_binance_portfolio_price_provider_from_settings(settings: Any) -> BinancePortfolioPriceProvider:
    return BinancePortfolioPriceProvider(
        base_url=settings.binance_base_url,
        timeout_seconds=settings.market_timeout_seconds,
        max_retries=settings.market_max_retries,
        cache_ttl_seconds=settings.market_cache_ttl_seconds,
        stale_ttl_seconds=settings.market_stale_ttl_seconds,
    )
