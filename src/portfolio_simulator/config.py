"""Application configuration via environment variables and .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Portfolio Simulator settings.

    All settings can be overridden via environment variables with the PSIM_ prefix,
    or via a .env file in the project root.
    """

    # Data provider
    default_provider: str = "yahoo"

    # Cache / storage
    cache_dir: Path = Path.home() / ".portfolio_simulator"
    cache_ttl_hours: int = 24

    # Defaults
    default_currency: str = "USD"
    risk_free_rate: float = 0.02
    trading_days_per_year: int = 252

    # Performance
    max_concurrent_fetches: int = 10

    # Cloud / auth
    database_url: str | None = None
    require_auth: bool = False

    # Future API keys
    bloomberg_api_key: str | None = None
    reuters_api_key: str | None = None

    model_config = {"env_prefix": "PSIM_", "env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def db_path(self) -> Path:
        return self.cache_dir / "portfolio_simulator.db"


def _load_settings() -> Settings:
    """Load settings, supplementing with Streamlit secrets when available."""
    s = Settings()
    try:
        import streamlit as st
        if "database" in st.secrets and not s.database_url:
            s.database_url = st.secrets["database"]["url"]
        if not s.require_auth and "credentials" in st.secrets:
            s.require_auth = True
    except Exception:
        pass
    return s


settings = _load_settings()
