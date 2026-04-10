"""Asset domain model."""

from pydantic import BaseModel, Field

from portfolio_simulator.domain.enums import AssetType, Currency


class Asset(BaseModel):
    """A single financial instrument (ETF, stock, fund, etc.)."""

    ticker: str
    name: str
    asset_type: AssetType = AssetType.ETF
    currency: Currency = Currency.USD
    ter: float = Field(default=0.0, ge=0.0, description="Annual TER as decimal (0.002 = 0.2%)")

    model_config = {"frozen": True}

    def __hash__(self) -> int:
        return hash(self.ticker)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Asset):
            return NotImplemented
        return self.ticker == other.ticker
