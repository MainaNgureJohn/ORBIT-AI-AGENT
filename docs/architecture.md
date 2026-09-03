# Architecture

ORBIT separates presentation, deterministic calculations, external data access, and optional language-model explanations. This keeps the financial calculations inspectable and prevents an LLM from becoming a source of portfolio facts.

## Components

### Next.js frontend

The frontend renders the Command, Markets, Portfolio, and Activity views. It talks only to the ORBIT FastAPI backend through `NEXT_PUBLIC_BACKEND_URL`; it never receives Binance or LLM credentials.

### FastAPI backend

The backend owns runtime configuration, input validation, public market access, signed account reads, portfolio valuation, deterministic scoring, LLM calls, and sanitized errors. FastAPI also exposes interactive documentation at `/docs`.

### Provider layer

External integrations sit behind provider interfaces:

- The market provider returns normalized BTC, ETH, and BNB snapshots.
- The account provider verifies permissions before returning non-zero balances.
- The portfolio price provider resolves direct and bridge prices without sending account credentials.
- The explanation provider uses Groq, OpenAI, or a deterministic fallback.

## Data flows

### Public market request

```text
Browser → FastAPI → Binance public market host → normalized snapshot → Browser
```

No credential is involved. Responses include source, retrieval time, and freshness.

### Read-only portfolio request

```text
Browser → FastAPI
             ├── verify Binance API permissions
             ├── read account balances with a signed GET request
             └── value assets from the public price book
         → portfolio snapshot → Browser
```

The backend includes every non-zero balance. If it cannot establish a trustworthy public price, it marks the asset unpriced instead of inventing a value.

### Analysis request

```text
Validated market/account data → deterministic calculation → optional LLM wording
```

The deterministic report is the source of truth. The language model may explain supplied fields but does not calculate balances, change scores, fetch credentials, or perform account actions.

## Failure behavior

- Transient Binance failures use bounded retries and may serve a clearly marked, time-limited stale cache.
- Credential and permission failures never fall back to cached account data.
- Missing asset prices remain visible as unpriced holdings.
- LLM errors produce a sanitized provider status and deterministic fallback.
- Unsupported symbols and invalid modes return explicit client errors.

## Trust boundaries

- Browser: untrusted presentation client; no secrets.
- Backend process: the only component allowed to read credentials.
- Binance public host: market data only.
- Binance account host: signed read-only requests only.
- LLM provider: receives validated summaries only, never exchange keys or secrets.

ORBIT contains no code path for placing or managing orders, transferring funds, deposits, or withdrawals.
