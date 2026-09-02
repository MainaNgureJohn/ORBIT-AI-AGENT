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
    source: Literal["simulation"] = "simulation"
    freshness: Literal["fixture"] = "fixture"


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


class AnalysisReport(BaseModel):
    asset: str
    snapshot: AssetSnapshot
    metrics: TechnicalMetrics
    score: ScoreBreakdown
    risk_level: RiskLevel
    reasons: list[str]
    limitations: list[str]
    generated_at: datetime


class PortfolioPosition(BaseModel):
    symbol: str
    quantity: float = Field(ge=0)
    market_value: float = Field(ge=0)
    allocation_percent: float = Field(ge=0, le=100)


class PortfolioSnapshot(BaseModel):
    total_value: float = Field(ge=0)
    stablecoin_percent: float = Field(ge=0, le=100)
    concentration_risk: RiskLevel
    positions: list[PortfolioPosition]
    source: Literal["simulation"] = "simulation"
    permission_scope: Literal["read_only"] = "read_only"
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
