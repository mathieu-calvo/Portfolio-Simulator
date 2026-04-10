"""Business day math and date alignment utilities."""

from datetime import date, timedelta

import numpy as np
import pandas as pd


def to_business_day(dt: date, direction: str = "backward") -> date:
    """Adjust a date to the nearest business day.

    Args:
        dt: Date to adjust.
        direction: "backward" for previous business day, "forward" for next.
    """
    ts = pd.Timestamp(dt)
    if direction == "backward":
        return ts.to_pydatetime().date() if ts == pd.tseries.offsets.BDay().rollback(ts) else pd.tseries.offsets.BDay().rollback(ts).to_pydatetime().date()
    return ts.to_pydatetime().date() if ts == pd.tseries.offsets.BDay().rollforward(ts) else pd.tseries.offsets.BDay().rollforward(ts).to_pydatetime().date()


def generate_rebalance_dates(
    start: date,
    end: date,
    frequency: str,
) -> list[date]:
    """Generate business-day-adjusted rebalance dates for a period.

    Args:
        start: Period start date.
        end: Period end date.
        frequency: One of "monthly", "quarterly", "semi_annually", "annually".

    Returns:
        List of rebalance dates (adjusted to business days).
    """
    freq_map = {
        "monthly": "BME",
        "quarterly": "BQE",
        "semi_annually": "6BME",
        "annually": "BAE",
    }
    if frequency not in freq_map:
        raise ValueError(f"Unknown frequency: {frequency}. Must be one of {list(freq_map)}")

    dates = pd.date_range(start=start, end=end, freq=freq_map[frequency])
    return [d.date() for d in dates]


def align_date_index(*series: pd.Series, method: str = "inner") -> list[pd.Series]:
    """Align multiple time series to a common date index.

    Args:
        *series: Variable number of pd.Series with DatetimeIndex.
        method: "inner" for intersection, "outer" for union (forward-fill NaN).

    Returns:
        List of aligned Series.
    """
    if not series:
        return []

    combined = pd.concat(series, axis=1, join=method)
    if method == "outer":
        combined = combined.ffill()

    return [combined.iloc[:, i].dropna() for i in range(combined.shape[1])]


def year_fraction(start: date, end: date) -> float:
    """Calculate the year fraction between two dates (actual/365.25)."""
    delta = end - start
    return delta.days / 365.25
