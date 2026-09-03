"""Provider contract shared by simulation and public market-data adapters."""

from collections.abc import Sequence
from typing import Protocol

from app.models.schemas import AssetSnapshot
from app.services.simulation import snapshot


class MarketProviderError(RuntimeError):
    """Base error for a market read that could not be completed safely."""


class InvalidSymbolError(MarketProviderError):
    pass


class MarketDataUnavailableError(MarketProviderError):
    pass


class MarketDataProvider(Protocol):
    async def get_snapshots(self, symbols: Sequence[str]) -> dict[str, AssetSnapshot]:
        """Return snapshots keyed by ORBIT symbols (for example ``BTC``)."""


class SimulationMarketProvider:
    """Adapter that keeps deterministic fixture reads behind the same contract."""

    async def get_snapshots(self, symbols: Sequence[str]) -> dict[str, AssetSnapshot]:
        normalized = [symbol.upper().strip() for symbol in symbols]
        unsupported = [symbol for symbol in normalized if symbol not in {"BTC", "ETH", "BNB"}]
        if unsupported or not normalized:
            raise InvalidSymbolError(f"Unsupported symbol(s): {', '.join(unsupported or normalized)}")
        return {symbol: snapshot(symbol) for symbol in dict.fromkeys(normalized)}
