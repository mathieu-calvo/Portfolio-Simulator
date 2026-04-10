"""Plotly chart builders for portfolio analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from portfolio_simulator.analytics.efficient_frontier import EfficientFrontierResult
from portfolio_simulator.analytics.risk import drawdown_series
from portfolio_simulator.domain.results import BacktestResult, MonteCarloResult
from portfolio_simulator.visualization.theme import (
    NEGATIVE_COLOR,
    NEUTRAL_COLOR,
    POSITIVE_COLOR,
    get_color,
)


def portfolio_evolution_chart(
    results: list[BacktestResult],
    title: str = "Portfolio Value Over Time",
) -> go.Figure:
    """Line chart showing portfolio value evolution for one or more backtests."""
    fig = go.Figure()
    for i, r in enumerate(results):
        fig.add_trace(
            go.Scatter(
                x=r.portfolio_value.index,
                y=r.portfolio_value.values,
                name=r.portfolio_name,
                line=dict(color=get_color(i), width=2),
            )
        )
    fig.update_layout(
        title=title,
        yaxis_title="Portfolio Value",
        yaxis_tickprefix="$",
    )
    return fig


def drawdown_chart(
    results: list[BacktestResult],
    title: str = "Drawdown",
) -> go.Figure:
    """Area chart showing drawdowns over time."""
    fig = go.Figure()
    for i, r in enumerate(results):
        dd = drawdown_series(r.portfolio_value)
        fig.add_trace(
            go.Scatter(
                x=dd.index,
                y=dd.values,
                name=r.portfolio_name,
                fill="tozeroy",
                line=dict(color=get_color(i), width=1),
                fillcolor=f"rgba({','.join(str(int(get_color(i).lstrip('#')[j:j+2], 16)) for j in (0,2,4))}, 0.3)",
            )
        )
    fig.update_layout(
        title=title,
        yaxis_title="Drawdown",
        yaxis_tickformat=".1%",
    )
    return fig


def monthly_returns_histogram(
    monthly_rets: pd.Series,
    title: str = "Distribution of Monthly Returns",
) -> go.Figure:
    """Histogram of monthly returns with color coding."""
    colors = [POSITIVE_COLOR if v >= 0 else NEGATIVE_COLOR for v in monthly_rets.values]
    fig = go.Figure(
        go.Bar(
            x=monthly_rets.index.astype(str),
            y=monthly_rets.values,
            marker_color=colors,
        )
    )
    fig.update_layout(
        title=title,
        yaxis_title="Return",
        yaxis_tickformat=".1%",
        xaxis_title="Month",
        showlegend=False,
    )
    return fig


def returns_heatmap(
    monthly_rets: pd.Series,
    title: str = "Monthly Returns Heatmap",
) -> go.Figure:
    """Calendar heatmap of monthly returns (rows=years, columns=months)."""
    # Convert PeriodIndex to year/month
    idx = monthly_rets.index
    if hasattr(idx, "year") and hasattr(idx, "month"):
        years = idx.year
        months = idx.month
    else:
        years = pd.PeriodIndex(idx).year
        months = pd.PeriodIndex(idx).month

    df = pd.DataFrame({"year": years, "month": months, "return": monthly_rets.values})
    pivot = df.pivot_table(index="year", columns="month", values="return")
    pivot.columns = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ][: len(pivot.columns)]

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdYlGn",
            zmid=0,
            text=np.round(pivot.values * 100, 1),
            texttemplate="%{text}%",
            hovertemplate="Year: %{y}<br>Month: %{x}<br>Return: %{z:.2%}<extra></extra>",
        )
    )
    fig.update_layout(title=title, yaxis=dict(autorange="reversed"))
    return fig


def allocation_donut(
    weights: dict[str, float],
    title: str = "Portfolio Allocation",
) -> go.Figure:
    """Donut chart of portfolio allocation weights."""
    labels = list(weights.keys())
    values = list(weights.values())
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            textinfo="label+percent",
            marker=dict(colors=[get_color(i) for i in range(len(labels))]),
        )
    )
    fig.update_layout(title=title, showlegend=True)
    return fig


def efficient_frontier_chart(
    result: EfficientFrontierResult,
    title: str = "Efficient Frontier",
) -> go.Figure:
    """Scatter plot of the efficient frontier with optimal portfolios marked."""
    fig = go.Figure()

    # Frontier line
    vols = [p.volatility for p in result.frontier_points]
    rets = [p.expected_return for p in result.frontier_points]
    fig.add_trace(
        go.Scatter(
            x=vols,
            y=rets,
            mode="lines",
            name="Efficient Frontier",
            line=dict(color=NEUTRAL_COLOR, width=2),
        )
    )

    # Max Sharpe
    ms = result.max_sharpe_portfolio
    fig.add_trace(
        go.Scatter(
            x=[ms.volatility],
            y=[ms.expected_return],
            mode="markers",
            name=f"Max Sharpe ({ms.sharpe_ratio:.2f})",
            marker=dict(color=POSITIVE_COLOR, size=12, symbol="star"),
        )
    )

    # Min Volatility
    mv = result.min_volatility_portfolio
    fig.add_trace(
        go.Scatter(
            x=[mv.volatility],
            y=[mv.expected_return],
            mode="markers",
            name="Min Volatility",
            marker=dict(color=get_color(0), size=12, symbol="diamond"),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Annualized Volatility",
        yaxis_title="Annualized Expected Return",
        xaxis_tickformat=".1%",
        yaxis_tickformat=".1%",
    )
    return fig


def monte_carlo_chart(
    mc_result: MonteCarloResult,
    title: str = "Monte Carlo Projection",
) -> go.Figure:
    """Fan chart showing Monte Carlo simulation percentile bands."""
    fig = go.Figure()

    # P5-P95 band
    fig.add_trace(
        go.Scatter(
            x=mc_result.percentile_95.index,
            y=mc_result.percentile_95.values,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=mc_result.percentile_5.index,
            y=mc_result.percentile_5.values,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.1)",
            name="P5-P95",
        )
    )

    # P25-P75 band
    fig.add_trace(
        go.Scatter(
            x=mc_result.percentile_75.index,
            y=mc_result.percentile_75.values,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=mc_result.percentile_25.index,
            y=mc_result.percentile_25.values,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(31, 119, 180, 0.25)",
            name="P25-P75",
        )
    )

    # Median
    fig.add_trace(
        go.Scatter(
            x=mc_result.median.index,
            y=mc_result.median.values,
            mode="lines",
            name="Median",
            line=dict(color=get_color(0), width=2),
        )
    )

    fig.update_layout(
        title=title,
        yaxis_title="Portfolio Value",
        yaxis_tickprefix="$",
    )
    return fig


def rolling_volatility_chart(
    results: list[BacktestResult],
    window_days: int = 63,
    title: str = "Rolling Volatility (Quarterly)",
) -> go.Figure:
    """Line chart of rolling annualized volatility."""
    from portfolio_simulator.analytics.risk import rolling_volatility

    fig = go.Figure()
    for i, r in enumerate(results):
        vol = rolling_volatility(r.portfolio_value, window_days)
        fig.add_trace(
            go.Scatter(
                x=vol.index,
                y=vol.values,
                name=r.portfolio_name,
                line=dict(color=get_color(i), width=2),
            )
        )
    fig.update_layout(
        title=title,
        yaxis_title="Annualized Volatility",
        yaxis_tickformat=".1%",
    )
    return fig
