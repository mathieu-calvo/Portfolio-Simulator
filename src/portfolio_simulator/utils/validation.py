"""Input validation utilities."""

from __future__ import annotations

import math
from datetime import date

import numpy as np


def validate_weights(weights: list[float] | np.ndarray, tolerance: float = 1e-6) -> None:
    """Validate that portfolio weights sum to 1.0 and are non-negative.

    Raises:
        ValueError: If weights don't sum to ~1.0 or contain negative values.
    """
    total = sum(weights)
    if not math.isclose(total, 1.0, abs_tol=tolerance):
        raise ValueError(f"Weights must sum to 1.0, got {total:.6f}")
    if any(w < -tolerance for w in weights):
        raise ValueError("Weights must be non-negative")


def validate_date_range(start: date, end: date) -> None:
    """Validate that start date is before end date.

    Raises:
        ValueError: If start >= end.
    """
    if start >= end:
        raise ValueError(f"Start date ({start}) must be before end date ({end})")
