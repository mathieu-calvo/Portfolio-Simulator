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

    # Future API keys
    bloomberg_api_key: str | None = None
    reuters_api_key: str | None = None

    model_config = {"env_prefix": "PSIM_", "env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def db_path(self) -> Path:
        return self.cache_dir / "portfolio_simulator.db"


settings = Settings()
