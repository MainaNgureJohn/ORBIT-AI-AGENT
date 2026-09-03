import asyncio
import hashlib
import hmac
from urllib.parse import urlencode

import pytest

from app.services.account_provider import AccountCredentialsError, AccountDataUnavailableError, AccountPermissionError
from app.services.binance_account import BinanceAccountProvider, sign_query


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
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def aclose(self):
        return None


def permission_payload(**overrides):
    payload = {
        "enableReading": True,
        "enableWithdrawals": False,
        "enableInternalTransfer": False,
        "enableMargin": False,
        "enableFutures": False,
        "permitsUniversalTransfer": False,
        "enableVanillaOptions": False,
        "enableFixApiTrade": False,
        "enableSpotAndMarginTrading": False,
        "enablePortfolioMarginTrading": False,
    }
    payload.update(overrides)
    return payload


def account_payload():
    return {
        # These are account-status fields, not API-key permission metadata.
        "canTrade": True,
        "canWithdraw": True,
        "canDeposit": True,
        "balances": [{"asset": "BTC", "free": "0.5", "locked": "0.1"}, {"asset": "USDT", "free": "100", "locked": "0"}],
    }


def service(client, **kwargs):
    return BinanceAccountProvider(api_key="test-key", api_secret="test-secret", client=client, sleep=lambda _: asyncio.sleep(0), **kwargs)


def test_account_read_is_signed_and_contains_only_read_endpoint():
    client = FakeClient([FakeResponse(permission_payload()), FakeResponse(account_payload())])
    result = asyncio.run(service(client, wall_clock_ms=lambda: 1700000000000).get_account())
    assert result.permission_scope == "read_only"
    assert result.permissions_verified is True
    assert [(balance.asset, balance.total) for balance in result.balances] == [("BTC", 0.6), ("USDT", 100.0)]
    permission_path, permission_kwargs = client.calls[0]
    assert permission_path == "/sapi/v1/account/apiRestrictions"
    assert permission_kwargs["headers"] == {"X-MBX-APIKEY": "test-key"}
    path, kwargs = client.calls[1]
    assert path == "/api/v3/account"
    assert kwargs["headers"] == {"X-MBX-APIKEY": "test-key"}
    params = kwargs["params"]
    assert params["timestamp"] == "1700000000000"
    assert params["omitZeroBalances"] == "true"
    assert params["signature"] == sign_query({"omitZeroBalances": "true", "recvWindow": "5000", "timestamp": "1700000000000"}, "test-secret")
    assert "test-secret" not in str(kwargs)


def test_signature_matches_hmac_sha256():
    params = {"timestamp": "1", "recvWindow": "5000"}
    expected = hmac.new(b"secret", urlencode(params).encode(), hashlib.sha256).hexdigest()
    assert sign_query(params, "secret") == expected


def test_credentials_must_be_configured_as_read_only():
    with pytest.raises(AccountCredentialsError):
        BinanceAccountProvider(api_key="", api_secret="secret")
    with pytest.raises(AccountCredentialsError):
        BinanceAccountProvider(api_key="key", api_secret="secret", account_access="trade")


@pytest.mark.parametrize(
    "permission",
    [
        "enableWithdrawals",
        "enableInternalTransfer",
        "enableMargin",
        "enableFutures",
        "permitsUniversalTransfer",
        "enableVanillaOptions",
        "enableFixApiTrade",
        "enableSpotAndMarginTrading",
        "enablePortfolioMarginTrading",
    ],
)
def test_any_over_privileged_permission_is_rejected(permission):
    with pytest.raises(AccountPermissionError):
        asyncio.run(service(FakeClient([FakeResponse(permission_payload(**{permission: True}))])).get_account())


def test_reading_permission_is_required():
    with pytest.raises(AccountPermissionError):
        asyncio.run(service(FakeClient([FakeResponse(permission_payload(enableReading=False))])).get_account())


def test_missing_permission_metadata_fails_closed():
    payload = permission_payload()
    payload.pop("enableSpotAndMarginTrading")
    with pytest.raises(AccountPermissionError):
        asyncio.run(service(FakeClient([FakeResponse(payload)])).get_account())


def test_malformed_account_json_is_unavailable():
    with pytest.raises(AccountDataUnavailableError):
        asyncio.run(service(FakeClient([FakeResponse(permission_payload()), FakeResponse(ValueError("bad json"))])).get_account())


def test_unauthorized_credentials_do_not_use_stale_cache():
    client = FakeClient([FakeResponse(permission_payload()), FakeResponse(account_payload()), FakeResponse(status_code=401)])
    now = [100.0]
    account = service(client, clock=lambda: now[0], cache_ttl_seconds=0, stale_ttl_seconds=100)
    asyncio.run(account.get_account())
    now[0] = 101
    with pytest.raises(AccountCredentialsError):
        asyncio.run(account.get_account())


def test_rate_limit_retry_and_stale_fallback():
    waits = []
    now = [100.0]
    client = FakeClient([FakeResponse(status_code=429, headers={"Retry-After": "2"}), FakeResponse(permission_payload()), FakeResponse(account_payload()), OSError("offline"), OSError("offline")])
    account = BinanceAccountProvider(api_key="key", api_secret="secret", client=client, max_retries=1, cache_ttl_seconds=0, stale_ttl_seconds=100, clock=lambda: now[0], sleep=lambda delay: waits.append(delay))
    asyncio.run(account.get_account())
    assert waits == [2.0]
    now[0] = 101
    stale = asyncio.run(account.get_account())
    assert stale.freshness == "stale"


def test_network_failure_without_cache_is_retryable_unavailable():
    client = FakeClient([OSError("offline"), OSError("offline")])
    with pytest.raises(AccountDataUnavailableError):
        asyncio.run(service(client, max_retries=1).get_account())
    assert len(client.calls) == 2


@pytest.mark.parametrize("code", [-2014, -2015, -1022])
def test_binance_credential_errors_are_classified_without_echoing_response(code):
    client = FakeClient([FakeResponse({"code": code, "msg": "unsafe upstream detail"}, status_code=400)])
    with pytest.raises(AccountCredentialsError) as raised:
        asyncio.run(service(client).get_account())
    assert str(code) not in str(raised.value)
    assert "unsafe upstream detail" not in str(raised.value)


def test_binance_clock_error_is_actionable_and_safe():
    client = FakeClient([FakeResponse({"code": -1021, "msg": "unsafe upstream detail"}, status_code=400)])
    with pytest.raises(AccountDataUnavailableError, match="automatic server-time synchronization"):
        asyncio.run(service(client, max_retries=0).get_account())


def test_binance_clock_drift_is_synchronized_and_retried():
    times = iter([1000, 1100, 1200, 1300, 1400])
    client = FakeClient(
        [
            FakeResponse({"code": -1021}, status_code=400),
            FakeResponse({"serverTime": 10150}),
            FakeResponse(permission_payload()),
            FakeResponse(account_payload()),
        ]
    )
    result = asyncio.run(service(client, max_retries=1, wall_clock_ms=lambda: next(times)).get_account())
    assert result.permissions_verified is True
    assert [call[0] for call in client.calls] == [
        "/sapi/v1/account/apiRestrictions",
        "/api/v3/time",
        "/sapi/v1/account/apiRestrictions",
        "/api/v3/account",
    ]
    assert client.calls[2][1]["params"]["timestamp"] == "10300"
