"""Simulation configuration model."""

from datetime import date

from pydantic import BaseModel, Field

from portfolio_simulator.domain.enums import (
    InvestmentStrategy,
    RebalanceFrequency,
    RebalanceStrategy,
)


class SimulationConfig(BaseModel):
    """All parameters needed to run a portfolio backtest."""

    start_date: date
    end_date: date
    initial_investment: float = Field(default=10_000.0, ge=0.0)
    recurring_investment: float = Field(
        default=0.0,
        description="Monthly cashflow — positive = contribution, negative = withdrawal",
    )
    investment_strategy: InvestmentStrategy = InvestmentStrategy.LUMP_SUM
    rebalance_strategy: RebalanceStrategy = RebalanceStrategy.NONE
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.QUARTERLY
    rebalance_tolerance: float = Field(
        default=0.05, ge=0.0, le=0.5, description="Drift threshold for tolerance-based rebalancing"
    )
    transaction_cost_pct: float = Field(default=0.0, ge=0.0, description="Per-trade cost as decimal")
    management_fee_pct: float = Field(default=0.0, ge=0.0, description="Annual advisory fee as decimal")
    tax_rate_pct: float = Field(default=0.0, ge=0.0, description="Capital gains tax rate on rebalance sells")
    include_ter: bool = True

    model_config = {"frozen": True}
