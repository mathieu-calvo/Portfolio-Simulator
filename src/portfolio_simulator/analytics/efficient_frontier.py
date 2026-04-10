"""Efficient frontier computation and portfolio optimization."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from portfolio_simulator.config import settings


@dataclass(frozen=True)
class FrontierPoint:
    """A single point on the efficient frontier."""

    expected_return: float
    volatility: float
    weights: np.ndarray
    sharpe_ratio: float


@dataclass(frozen=True)
class EfficientFrontierResult:
    """Full efficient frontier computation result."""

    frontier_points: list[FrontierPoint]
    max_sharpe_portfolio: FrontierPoint
    min_volatility_portfolio: FrontierPoint
    asset_names: list[str]


def compute_efficient_frontier(
    prices_df: pd.DataFrame,
    n_points: int = 50,
    risk_free_rate: float | None = None,
    trading_days: int | None = None,
    allow_short: bool = False,
) -> EfficientFrontierResult:
    """Compute the efficient frontier for a set of assets.

    Args:
        prices_df: DataFrame with DatetimeIndex, one column per asset (prices).
        n_points: Number of points to compute along the frontier.
        risk_free_rate: Annual risk-free rate for Sharpe calculation.
        trading_days: Trading days per year.
        allow_short: Whether to allow short positions.

    Returns:
        EfficientFrontierResult with frontier points and optimal portfolios.
    """
    rf = risk_free_rate if risk_free_rate is not None else settings.risk_free_rate
    td = trading_days or settings.trading_days_per_year

    returns = prices_df.pct_change().dropna()
    mean_returns = returns.mean() * td  # Annualized
    cov_matrix = returns.cov() * td  # Annualized
    n_assets = len(prices_df.columns)
    asset_names = list(prices_df.columns)

    # Constraints
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    if allow_short:
        bounds = tuple((-1, 1) for _ in range(n_assets))
    else:
        bounds = tuple((0, 1) for _ in range(n_assets))

    def portfolio_volatility(weights: np.ndarray) -> float:
        return float(np.sqrt(weights @ cov_matrix.values @ weights))

    def portfolio_return(weights: np.ndarray) -> float:
        return float(weights @ mean_returns.values)

    def neg_sharpe(weights: np.ndarray) -> float:
        ret = portfolio_return(weights)
        vol = portfolio_volatility(weights)
        if vol == 0:
            return 0.0
        return -(ret - rf) / vol

    # Find min-volatility portfolio
    init_weights = np.ones(n_assets) / n_assets
    min_vol_result = minimize(
        portfolio_volatility,
        init_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    min_vol_weights = min_vol_result.x
    min_vol_ret = portfolio_return(min_vol_weights)
    min_vol_vol = portfolio_volatility(min_vol_weights)

    # Find max-Sharpe portfolio
    max_sharpe_result = minimize(
        neg_sharpe,
        init_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    max_sharpe_weights = max_sharpe_result.x

    # Compute frontier points across return range
    max_ret = float(mean_returns.max())
    target_returns = np.linspace(min_vol_ret, max_ret, n_points)

    frontier_points: list[FrontierPoint] = []
    for target_ret in target_returns:
        target_constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, tr=target_ret: portfolio_return(w) - tr},
        ]
        result = minimize(
            portfolio_volatility,
            init_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=target_constraints,
        )
        if result.success:
            vol = portfolio_volatility(result.x)
            ret = portfolio_return(result.x)
            sharpe = (ret - rf) / vol if vol > 0 else 0.0
            frontier_points.append(
                FrontierPoint(
                    expected_return=ret,
                    volatility=vol,
                    weights=result.x.copy(),
                    sharpe_ratio=sharpe,
                )
            )

    # Build special portfolio points
    ms_ret = portfolio_return(max_sharpe_weights)
    ms_vol = portfolio_volatility(max_sharpe_weights)
    ms_sharpe = (ms_ret - rf) / ms_vol if ms_vol > 0 else 0.0

    return EfficientFrontierResult(
        frontier_points=frontier_points,
        max_sharpe_portfolio=FrontierPoint(
            expected_return=ms_ret,
            volatility=ms_vol,
            weights=max_sharpe_weights,
            sharpe_ratio=ms_sharpe,
        ),
        min_volatility_portfolio=FrontierPoint(
            expected_return=min_vol_ret,
            volatility=min_vol_vol,
            weights=min_vol_weights,
            sharpe_ratio=(min_vol_ret - rf) / min_vol_vol if min_vol_vol > 0 else 0.0,
        ),
        asset_names=asset_names,
    )
