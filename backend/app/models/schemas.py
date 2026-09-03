from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AssetSnapshot(BaseModel):
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    timestamp: datetime
    retrieved_at: datetime | None = None
    source: Literal["simulation", "binance"] = "simulation"
    freshness: Literal["fixture", "fresh", "stale"] = "fixture"


class TechnicalMetrics(BaseModel):
    trend: str
    momentum: float = Field(ge=0, le=100)
    volatility: float = Field(ge=0, le=100)
    volume_signal: str
    support_resistance: str


class ScoreBreakdown(BaseModel):
    market: float = Field(ge=0, le=100)
    technical: float = Field(ge=0, le=100)
    on_chain: float | None = Field(default=None, ge=0, le=100)
    risk: float = Field(ge=0, le=100)
    final: float = Field(ge=0, le=100)
    missing_components: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    asset: str
    snapshot: AssetSnapshot
    metrics: TechnicalMetrics
    score: ScoreBreakdown
    risk_level: RiskLevel
    reasons: list[str]
    limitations: list[str]
    generated_at: datetime
    explanation: str | None = None


class PortfolioPosition(BaseModel):
    symbol: str
    quantity: float = Field(ge=0)
    market_value: float = Field(ge=0)
    allocation_percent: float = Field(ge=0, le=100)


class PortfolioHolding(BaseModel):
    """Every non-zero account holding, including assets without a price."""

    symbol: str
    quantity: float = Field(ge=0)
    market_value: float | None = Field(default=None, ge=0)
    allocation_percent: float | None = Field(default=None, ge=0, le=100)
    unit_price: float | None = Field(default=None, ge=0)
    price_status: Literal["available", "unpriced"]
    source: Literal["binance"] = "binance"
    freshness: Literal["fresh", "stale"] = "fresh"


class PortfolioSnapshot(BaseModel):
    total_value: float = Field(ge=0)
    stablecoin_percent: float = Field(ge=0, le=100)
    concentration_risk: RiskLevel
    positions: list[PortfolioPosition]
    holdings: list[PortfolioHolding] = Field(default_factory=list)
    source: Literal["simulation", "binance"] = "simulation"
    permission_scope: Literal["read_only"] = "read_only"
    fetched_at: datetime
    freshness: Literal["fixture", "fresh", "stale"] = "fixture"
    unpriced_assets: list[str] = Field(default_factory=list)


class AccountBalance(BaseModel):
    asset: str
    free: float = Field(ge=0)
    locked: float = Field(ge=0)
    total: float = Field(ge=0)


class AccountSnapshot(BaseModel):
    balances: list[AccountBalance]
    source: Literal["binance"] = "binance"
    permission_scope: Literal["read_only"] = "read_only"
    permissions_verified: bool = True
    freshness: Literal["fresh", "stale"] = "fresh"
    fetched_at: datetime


class PortfolioSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: f"suggestion_{uuid4().hex[:10]}")
    symbol: str
    action: Literal["HOLD", "CONSIDER_BUY", "CONSIDER_REDUCE", "REBALANCE"]
    current_allocation_percent: float = Field(ge=0, le=100)
    target_range: str
    risk: RiskLevel
    confidence_score: float = Field(ge=0, le=100)
    rationale: list[str]
    disclaimer: str = "Informational suggestion only. ORBIT cannot place orders."
    generated_at: datetime


class AdviceRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AdviceResponse(BaseModel):
    answer: str
    provider: Literal["openai", "groq", "deterministic"]
    source: Literal["binance", "none"] = "none"
    limitations: list[str] = Field(default_factory=list)


class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str
    stage: str
    status: str
    summary: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    retryable: bool
    request_id: str
