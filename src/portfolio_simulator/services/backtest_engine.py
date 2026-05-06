"""Core backtest engine with vectorized execution between rebalance points."""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd

from portfolio_simulator.analytics.costs import (
    management_fee_daily,
    tax_on_gains,
    ter_drag_daily,
    transaction_cost_impact,
)
from portfolio_simulator.domain.enums import (
    InvestmentStrategy,
    RebalanceStrategy,
)
from portfolio_simulator.domain.portfolio import Portfolio
from portfolio_simulator.domain.results import BacktestResult
from portfolio_simulator.domain.simulation import SimulationConfig
from portfolio_simulator.services.data_service import DataService
from portfolio_simulator.utils.date_utils import generate_rebalance_dates

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Portfolio backtesting engine.

    Runs vectorized simulation with support for:
    - Calendar-based, tolerance-based, or no rebalancing
    - Dollar-cost averaging (DCA) inflows
    - Transaction costs, management fees, TER, and tax deductions
    """

    def __init__(self, data_service: DataService) -> None:
        self._data_service = data_service

    def run(self, portfolio: Portfolio, config: SimulationConfig) -> BacktestResult:
        """Execute a backtest for a single portfolio.

        Args:
            portfolio: Portfolio with target allocations.
            config: Simulation parameters.

        Returns:
            BacktestResult with full time series.
        """
        # 1. Fetch price data for all assets
        prices_df = self._data_service.get_prices_bulk(
            portfolio.tickers, config.start_date, config.end_date
        )

        if prices_df.empty:
            raise ValueError("No price data available for the given date range")

        # Drop rows where any asset is missing (inner join by date)
        prices_df = prices_df.dropna()

        # 2. Compute daily returns matrix
        returns_df = prices_df.pct_change().iloc[1:]
        dates = returns_df.index
        tickers = list(returns_df.columns)
        n_days = len(dates)
        n_assets = len(tickers)

        # 3. Build target weights array (aligned to tickers)
        target_weights = np.array([portfolio.weight_for(t) for t in tickers])

        # 4. Determine rebalance schedule
        rebalance_set = self._get_rebalance_dates(config, dates)

        # 5. Simulate day by day with vectorized segments
        portfolio_values = np.empty(n_days)
        actual_weights_matrix = np.empty((n_days, n_assets))
        total_fees = 0.0
        total_taxes = 0.0
        total_invested = config.initial_investment

        # Initialize
        current_value = config.initial_investment
        current_weights = target_weights.copy()
        returns_arr = returns_df.values  # (n_days, n_assets)
        actual_rebalance_dates: list = []

        # TER daily drag per asset
        if config.include_ter:
            ter_drags = np.array([ter_drag_daily(a.ter) for a in portfolio.assets])
        else:
            ter_drags = np.zeros(n_assets)

        # Management fee daily
        mgmt_fee_daily = management_fee_daily(config.management_fee_pct)

        # DCA: monthly contribution dates
        dca_dates = set()
        if (
            config.investment_strategy == InvestmentStrategy.DCA
            and config.recurring_investment > 0
        ):
            monthly_dates = pd.date_range(
                start=config.start_date, end=config.end_date, freq="BME"
            )
            dca_dates = set(monthly_dates)

        for i in range(n_days):
            dt = dates[i]
            day_returns = returns_arr[i]  # returns for each asset

            # Apply TER drag to returns
            adjusted_returns = day_returns - ter_drags

            # Portfolio return for this day
            port_return = current_weights @ adjusted_returns

            # Update portfolio value
            new_value = current_value * (1 + port_return)

            # Deduct daily management fee
            fee = new_value * mgmt_fee_daily
            new_value -= fee
            total_fees += fee

            # DCA inflow
            if dt in dca_dates:
                new_value += config.recurring_investment
                total_invested += config.recurring_investment

            # Update actual weights (drift with returns)
            if current_value > 0:
                asset_values = current_weights * current_value * (1 + adjusted_returns)
                current_weights = asset_values / asset_values.sum()
            else:
                current_weights = target_weights.copy()

            # Check rebalancing
            needs_rebalance = False
            if config.rebalance_strategy == RebalanceStrategy.CALENDAR:
                needs_rebalance = dt in rebalance_set
            elif config.rebalance_strategy == RebalanceStrategy.TOLERANCE:
                deviation = np.abs(current_weights - target_weights).max()
                needs_rebalance = deviation > config.rebalance_tolerance

            if needs_rebalance and new_value > 0:
                # Calculate turnover and costs
                turnover = np.abs(current_weights - target_weights).sum() / 2
                tx_cost = transaction_cost_impact(
                    new_value, turnover, config.transaction_cost_pct
                )
                total_fees += tx_cost

                # Tax on rebalance: estimate realized gains on positions being sold
                if config.tax_rate_pct > 0:
                    # Simplified: tax on the portion being sold that exceeds target
                    sells = np.maximum(current_weights - target_weights, 0)
                    # Approximate gain as portfolio appreciation * sell fraction
                    gain_estimate = new_value * sells.sum() * max(0, port_return)
                    tax = tax_on_gains(gain_estimate, config.tax_rate_pct)
                    total_taxes += tax
                    new_value -= tax

                new_value -= tx_cost
                current_weights = target_weights.copy()
                actual_rebalance_dates.append(dt)

            # Store
            portfolio_values[i] = new_value
            actual_weights_matrix[i] = current_weights
            current_value = new_value

        # 6. Build result objects
        value_series = pd.Series(portfolio_values, index=dates, name=portfolio.name)
        daily_ret = value_series.pct_change().fillna(0)
        daily_ret.name = portfolio.name
        weights_df = pd.DataFrame(
            actual_weights_matrix, index=dates, columns=tickers
        )

        rebalance_dates_list = sorted(
            d.date() if hasattr(d, "date") else d for d in actual_rebalance_dates
        )

        return BacktestResult(
            portfolio_name=portfolio.name,
            config=config,
            portfolio_value=value_series,
            daily_returns=daily_ret,
            asset_weights_over_time=weights_df,
            rebalance_dates=tuple(rebalance_dates_list),
            total_invested=total_invested,
            total_fees_paid=total_fees,
            total_taxes_paid=total_taxes,
        )

    def run_comparison(
        self,
        portfolios: list[Portfolio],
        config: SimulationConfig,
    ) -> list[BacktestResult]:
        """Run backtest for multiple portfolios with the same config."""
        return [self.run(p, config) for p in portfolios]

    def _get_rebalance_dates(
        self,
        config: SimulationConfig,
        dates: pd.DatetimeIndex,
    ) -> set:
        """Compute the set of rebalance dates based on strategy."""
        if config.rebalance_strategy == RebalanceStrategy.NONE:
            return set()

        if config.rebalance_strategy == RebalanceStrategy.CALENDAR:
            rebal_dates = generate_rebalance_dates(
                config.start_date,
                config.end_date,
                config.rebalance_frequency.value,
            )
            # Snap to actual trading dates
            trading_dates = set(dates)
            snapped = set()
            for rd in rebal_dates:
                ts = pd.Timestamp(rd)
                if ts in trading_dates:
                    snapped.add(ts)
                else:
                    # Find nearest previous trading date
                    candidates = [d for d in dates if d <= ts]
                    if candidates:
                        snapped.add(candidates[-1])
            return snapped

        # Tolerance-based: checked dynamically in the loop
        return set()
