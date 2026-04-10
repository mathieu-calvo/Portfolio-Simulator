"""Consistent Plotly theme and color palette."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# Color palette
COLORS = [
    "#1f77b4",  # Blue
    "#ff7f0e",  # Orange
    "#2ca02c",  # Green
    "#d62728",  # Red
    "#9467bd",  # Purple
    "#8c564b",  # Brown
    "#e377c2",  # Pink
    "#7f7f7f",  # Gray
    "#bcbd22",  # Olive
    "#17becf",  # Cyan
]

POSITIVE_COLOR = "#2ca02c"
NEGATIVE_COLOR = "#d62728"
NEUTRAL_COLOR = "#7f7f7f"
BACKGROUND_COLOR = "#ffffff"
GRID_COLOR = "#e5e5e5"

# Template
TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Inter, system-ui, sans-serif", size=13),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        colorway=COLORS,
        xaxis=dict(gridcolor=GRID_COLOR, showgrid=True),
        yaxis=dict(gridcolor=GRID_COLOR, showgrid=True),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=60, r=20, t=50, b=40),
        hovermode="x unified",
    )
)

pio.templates["portfolio_simulator"] = TEMPLATE
pio.templates.default = "portfolio_simulator"


def get_color(index: int) -> str:
    """Get a color from the palette by index (wraps around)."""
    return COLORS[index % len(COLORS)]
