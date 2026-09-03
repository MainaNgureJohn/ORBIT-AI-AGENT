"""Environment-backed, safe defaults for the read-only market service."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    app_mode: str = "binance"
    frontend_origin: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    llm_provider: str = "disabled"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = 20.0
    binance_base_url: str = "https://data-api.binance.vision"
    binance_account_base_url: str = "https://api.binance.com"
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_account_access: str = "read_only"
    account_timeout_seconds: float = 5.0
    account_max_retries: int = 2
    account_cache_ttl_seconds: float = 15.0
    account_stale_ttl_seconds: float = 300.0
    market_timeout_seconds: float = 5.0
    market_max_retries: int = 2
    market_cache_ttl_seconds: float = 15.0
    market_stale_ttl_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", cls.app_env),
            app_mode=os.getenv("APP_MODE", cls.app_mode).lower(),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", cls.frontend_origin),
            backend_url=os.getenv("BACKEND_URL", cls.backend_url),
            llm_provider=os.getenv("LLM_PROVIDER", cls.llm_provider).lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", cls.openai_model),
            openai_base_url=os.getenv("OPENAI_BASE_URL", cls.openai_base_url).rstrip("/"),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("GROQ_MODEL", cls.groq_model),
            groq_base_url=os.getenv("GROQ_BASE_URL", cls.groq_base_url).rstrip("/"),
            llm_timeout_seconds=_float_env("LLM_TIMEOUT_SECONDS", cls.llm_timeout_seconds),
            binance_base_url=os.getenv("BINANCE_BASE_URL", cls.binance_base_url).rstrip("/"),
            binance_account_base_url=os.getenv("BINANCE_ACCOUNT_BASE_URL", cls.binance_account_base_url).rstrip("/"),
            binance_api_key=os.getenv("BINANCE_API_KEY", ""),
            binance_api_secret=os.getenv("BINANCE_API_SECRET", ""),
            binance_account_access=os.getenv("BINANCE_ACCOUNT_ACCESS", cls.binance_account_access).lower(),
            account_timeout_seconds=_float_env("ACCOUNT_TIMEOUT_SECONDS", cls.account_timeout_seconds),
            account_max_retries=_int_env("ACCOUNT_MAX_RETRIES", cls.account_max_retries),
            account_cache_ttl_seconds=_float_env("ACCOUNT_CACHE_TTL_SECONDS", cls.account_cache_ttl_seconds),
            account_stale_ttl_seconds=_float_env("ACCOUNT_STALE_TTL_SECONDS", cls.account_stale_ttl_seconds),
            market_timeout_seconds=_float_env("MARKET_TIMEOUT_SECONDS", cls.market_timeout_seconds),
            market_max_retries=_int_env("MARKET_MAX_RETRIES", cls.market_max_retries),
            market_cache_ttl_seconds=_float_env("MARKET_CACHE_TTL_SECONDS", cls.market_cache_ttl_seconds),
            market_stale_ttl_seconds=_float_env("MARKET_STALE_TTL_SECONDS", cls.market_stale_ttl_seconds),
        )


def _float_env(name: str, default: float) -> float:
    try:
        return max(0.1, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def get_settings() -> Settings:
    return Settings.from_env()
