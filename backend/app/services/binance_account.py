"""Strictly read-only Binance Spot account adapter.

The adapter verifies the API key with ``GET /sapi/v1/account/apiRestrictions``
before reading balances from ``GET /api/v3/account``. Both requests are signed
server-side; no write endpoint or secret is exposed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
import hashlib
import hmac
import inspect
import json
from time import monotonic
from typing import Any
from urllib.parse import urlencode

try:
    import httpx
except ImportError:  # Simulation mode remains usable before backend deps are installed.
    httpx = None  # type: ignore[assignment]

from app.models.schemas import AccountBalance, AccountSnapshot
from app.services.account_provider import AccountCredentialsError, AccountDataUnavailableError, AccountPermissionError


_NETWORK_ERRORS = tuple(error for error in (getattr(httpx, "TimeoutException", None), getattr(httpx, "NetworkError", None), OSError) if error is not None) or (Exception,)


class BinanceAccountProvider:
    endpoint_path = "/api/v3/account"
    permission_endpoint_path = "/sapi/v1/account/apiRestrictions"
    time_endpoint_path = "/api/v3/time"

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        account_access: str = "read_only",
        base_url: str = "https://api.binance.com",
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
        cache_ttl_seconds: float = 15.0,
        stale_ttl_seconds: float = 300.0,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Any] = asyncio.sleep,
        clock: Callable[[], float] = monotonic,
        wall_clock_ms: Callable[[], int] | None = None,
    ) -> None:
        self._validate_credentials(api_key, api_secret, account_access)
        self.api_key = api_key
        self._api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds) if httpx is not None else timeout_seconds
        self.max_retries = max(0, max_retries)
        self.cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self.stale_ttl_seconds = max(0.0, stale_ttl_seconds)
        self._client = client
        self._sleep = sleep
        self._clock = clock
        self._wall_clock_ms = wall_clock_ms or (lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
        self._time_offset_ms = 0
        self._cache: tuple[AccountSnapshot, float] | None = None

    async def get_account(self) -> AccountSnapshot:
        now = self._clock()
        if self._cache is not None and now - self._cache[1] <= self.cache_ttl_seconds:
            return self._cache[0]
        try:
            return await self._fetch()
        except (AccountCredentialsError, AccountPermissionError):
            raise
        except Exception as exc:
            if self._cache is not None and now - self._cache[1] <= self.stale_ttl_seconds:
                return self._cache[0].model_copy(update={"freshness": "stale"})
            if isinstance(exc, AccountDataUnavailableError):
                raise
            raise AccountDataUnavailableError(f"Binance account data unavailable: {exc}") from exc

    async def _fetch(self) -> AccountSnapshot:
        if httpx is None and self._client is None:
            raise AccountDataUnavailableError("httpx is not installed; install backend requirements first")
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)  # type: ignore[union-attr]
        try:
            permission_payload = await self._request(client, self.permission_endpoint_path)
            self._validate_permission_payload(permission_payload)
            account_payload = await self._request(client, self.endpoint_path, {"omitZeroBalances": "true"})
            return self._parse_account_payload(account_payload)
        finally:
            if own_client:
                await client.aclose()

    async def _request(self, client: Any, path: str, extra_params: dict[str, str] | None = None) -> Any:
        for attempt in range(self.max_retries + 1):
            params = dict(extra_params or {})
            params.update({"recvWindow": "5000", "timestamp": str(self._wall_clock_ms() + self._time_offset_ms)})
            params["signature"] = sign_query(params, self._api_secret)
            try:
                response = await client.get(path, params=params, headers={"X-MBX-APIKEY": self.api_key})
            except _NETWORK_ERRORS as exc:
                if attempt >= self.max_retries:
                    raise AccountDataUnavailableError("Binance account request timed out or failed on the network") from exc
                await self._wait(min(2.0, 0.25 * (2**attempt)))
                continue
            if response.status_code in {401, 403}:
                raise AccountCredentialsError("Binance rejected the account credentials")
            if response.status_code in {429, 418}:
                if attempt >= self.max_retries:
                    raise AccountDataUnavailableError(f"Binance rate limit response ({response.status_code})")
                await self._wait(_retry_after(response, attempt))
                continue
            if response.status_code >= 400:
                code = _binance_error_code(response)
                if code in {-2014, -2015, -1022}:
                    reason = {
                        -2014: "API key format is invalid",
                        -2015: "API key, trusted IP, or reading permission was rejected",
                        -1022: "request signature was rejected",
                    }[code]
                    raise AccountCredentialsError(f"Binance rejected the credentials: {reason}")
                if code == -1021:
                    if attempt >= self.max_retries:
                        raise AccountDataUnavailableError("Binance rejected the timestamp after automatic server-time synchronization")
                    await self._synchronize_time(client)
                    continue
                suffix = f" (code {code})" if code is not None else ""
                raise AccountDataUnavailableError(f"Binance returned HTTP {response.status_code}{suffix}")
            try:
                return response.json()
            except ValueError as exc:
                raise AccountDataUnavailableError("Binance returned malformed JSON") from exc
        raise AccountDataUnavailableError("Binance account request exhausted retries")

    async def _synchronize_time(self, client: Any) -> None:
        before = self._wall_clock_ms()
        try:
            response = await client.get(self.time_endpoint_path)
        except _NETWORK_ERRORS as exc:
            raise AccountDataUnavailableError("Binance server time is unavailable") from exc
        after = self._wall_clock_ms()
        if response.status_code >= 400:
            raise AccountDataUnavailableError(f"Binance server time returned HTTP {response.status_code}")
        try:
            payload = response.json()
            server_time = payload["serverTime"]
        except (ValueError, TypeError, KeyError) as exc:
            raise AccountDataUnavailableError("Binance server time response was malformed") from exc
        if not isinstance(server_time, int):
            raise AccountDataUnavailableError("Binance server time response was malformed")
        midpoint = round((before + after) / 2)
        self._time_offset_ms = server_time - midpoint

    @staticmethod
    def _validate_permission_payload(payload: Any) -> None:
        if not isinstance(payload, dict):
            raise AccountPermissionError("Binance API-key permission response was not an object")
        dangerous_permissions = (
            "enableWithdrawals",
            "enableInternalTransfer",
            "enableMargin",
            "enableFutures",
            "permitsUniversalTransfer",
            "enableVanillaOptions",
            "enableFixApiTrade",
            "enableSpotAndMarginTrading",
            "enablePortfolioMarginTrading",
        )
        required = ("enableReading", *dangerous_permissions)
        if any(key not in payload or not isinstance(payload[key], bool) for key in required):
            raise AccountPermissionError("Binance API-key permission metadata is incomplete; read-only access cannot be verified")
        if payload["enableReading"] is not True:
            raise AccountPermissionError("Binance API key does not have reading permission")
        enabled = [key for key in dangerous_permissions if payload[key] is True]
        if enabled:
            raise AccountPermissionError("Binance API key has a write-capable permission enabled")

    def _parse_account_payload(self, payload: Any) -> AccountSnapshot:
        if not isinstance(payload, dict):
            raise AccountDataUnavailableError("Binance account response was not an object")
        raw_balances = payload.get("balances")
        if not isinstance(raw_balances, list):
            raise AccountDataUnavailableError("Binance account response has no valid balances list")
        balances: list[AccountBalance] = []
        try:
            for item in raw_balances:
                if not isinstance(item, dict) or not isinstance(item.get("asset"), str):
                    continue
                free = float(item["free"])
                locked = float(item["locked"])
                balances.append(AccountBalance(asset=item["asset"].upper(), free=free, locked=locked, total=free + locked))
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise AccountDataUnavailableError("Binance account response contains malformed balances") from exc
        snapshot = AccountSnapshot(balances=balances, fetched_at=datetime.now(timezone.utc))
        self._cache = (snapshot, self._clock())
        return snapshot

    async def _wait(self, delay: float) -> None:
        result = self._sleep(delay)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _validate_credentials(api_key: str, api_secret: str, account_access: str) -> None:
        if account_access.lower() != "read_only":
            raise AccountCredentialsError("BINANCE_ACCOUNT_ACCESS must be read_only")
        if not api_key or not api_secret:
            raise AccountCredentialsError("Binance read-only API credentials are not configured")


def sign_query(params: dict[str, str], secret: str) -> str:
    payload = urlencode(params)
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _retry_after(response: Any, attempt: int) -> float:
    value = response.headers.get("Retry-After")
    try:
        return min(30.0, max(0.0, float(value))) if value is not None else min(2.0, 0.25 * (2**attempt))
    except (TypeError, ValueError):
        return min(2.0, 0.25 * (2**attempt))


def _binance_error_code(response: Any) -> int | None:
    try:
        payload = response.json()
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    code = payload.get("code")
    return code if isinstance(code, int) else None


def create_binance_account_provider_from_settings(settings: Any) -> BinanceAccountProvider:
    return BinanceAccountProvider(
        api_key=settings.binance_api_key,
        api_secret=settings.binance_api_secret,
        account_access=settings.binance_account_access,
        base_url=settings.binance_account_base_url,
        timeout_seconds=settings.account_timeout_seconds,
        max_retries=settings.account_max_retries,
        cache_ttl_seconds=settings.account_cache_ttl_seconds,
        stale_ttl_seconds=settings.account_stale_ttl_seconds,
    )
