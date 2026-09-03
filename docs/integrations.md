# Integrations

## Binance public market data

Verified 2026-09-02 against the official Binance documentation:

- Base URL: `https://data-api.binance.vision`, the documented market-data-only host for public APIs.
- Route: `GET /api/v3/ticker/24hr` with the `symbols` query parameter containing `BTCUSDT`, `ETHUSDT`, and `BNBUSDT`; ORBIT's watchlist calls this upstream route once through `GET /api/v1/market`.
- The multi-symbol request is one request for the watchlist (the endpoint accepts 1–20 symbols and has request weight 2).
- Security type: `NONE`; no API key, secret, signature, account permission, or credential is used.
- Rate limits: the adapter honors `Retry-After` on HTTP 429 (rate limit) and 418 (temporary IP ban), with bounded retries and backoff. Successful reads are cached briefly; a bounded stale cache is returned when a refresh fails.

Official references:

- [General REST API information](https://developers.binance.com/en/docs/products/spot/rest-api)
- [Market REST API](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)

This integration is read-only market observation. ORBIT does not implement trading, order, account, transfer, deposit, or withdrawal operations.

## Binance authenticated account reads

Verified 2026-09-02 against the official [Spot Account REST API](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/account) and [Wallet Account REST API](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account):

- Routes: `GET /sapi/v1/account/apiRestrictions` verifies the API key's actual permissions before `GET /api/v3/account` reads balances. Both use `https://api.binance.com`.
- Security type: `USER_DATA`; requests are signed server-side with HMAC SHA-256, include a timestamp, and send the API key only in `X-MBX-APIKEY`.
- ORBIT requests only non-zero balances and never calls order, trade, transfer, deposit, withdrawal, or user-stream endpoints.
- `enableReading` must be `true`. Withdrawal, internal/universal transfer, spot/margin/futures/options/portfolio-margin trading, and FIX trading permissions must all be present and `false`; otherwise the key is rejected before balances are accepted.
- Account reads use bounded timeout/retries, `Retry-After` handling for 429/418, short caching, and stale fallback only for transient failures. Credential or permission failures never fall back to cached data.
- If Binance reports timestamp drift, ORBIT reads Binance's unsigned public server-time endpoint, keeps an in-memory offset, re-signs, and retries without changing the host computer's clock.

### Public valuation of account assets

- Route: unsigned `GET /api/v3/ticker/price` on the market-data-only host; no account credentials are attached.
- ORBIT downloads one price book per cache refresh and prefers a direct `ASSETUSDT` market.
- If no direct market exists, it may derive the value through `ASSETBTC`, `ASSETETH`, or `ASSETBNB` and that bridge asset's USDT price.
- Non-positive, non-finite, malformed, or unavailable prices are discarded. Assets with no valid route remain in `unpriced_assets`.
- The provider uses the same bounded retries, rate-limit handling, short cache, and stale-cache window as the public watchlist adapter.

This mode is disabled by default. No real credentials are included in examples, tests, screenshots, or commits.

## Language-model explanations

ORBIT supports optional Groq and OpenAI providers behind one explanation interface. Groq uses the OpenAI-compatible Chat Completions route; OpenAI uses the Responses API. Provider keys remain in the backend process environment and are sent only to the selected provider.

The model receives a compact JSON summary of validated market or portfolio fields. It never receives Binance credentials and does not calculate balances, prices, or deterministic scores. Provider errors are reduced to a sanitized health state, and the application falls back to deterministic wording.
