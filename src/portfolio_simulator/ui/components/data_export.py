"""Excel export helpers for raw data download buttons.

Used by the Backtest and Comparison views to offer users a way to inspect and
export the underlying time series driving each analysis.
"""

from __future__ import annotations

import io
import re

import pandas as pd
import streamlit as st

_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_INVALID_SHEET_CHARS = re.compile(r"[\\/?*\[\]:]")


def _safe_sheet_name(name: str) -> str:
    """Excel sheet names are max 31 chars and can't contain :\\/?*[]."""
    cleaned = _INVALID_SHEET_CHARS.sub("-", name)
    return cleaned[:31] or "Sheet1"


def dataframes_to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Convert a dict of {sheet_name: DataFrame} into an .xlsx file in memory.

    Each entry becomes a sheet in the resulting workbook. Sheet names are
    sanitized to comply with Excel's restrictions.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        used: set[str] = set()
        for raw_name, df in sheets.items():
            name = _safe_sheet_name(raw_name)
            # Ensure uniqueness in case two names collide after truncation
            base = name
            i = 2
            while name in used:
                suffix = f" ({i})"
                name = (base[: 31 - len(suffix)] + suffix)
                i += 1
            used.add(name)
            df.to_excel(writer, sheet_name=name)
    return buffer.getvalue()


def download_excel_button(
    label: str,
    sheets: dict[str, pd.DataFrame],
    filename: str,
    key: str,
    help: str | None = None,
) -> None:
    """Render a download button that produces a multi-sheet Excel file."""
    try:
        excel_bytes = dataframes_to_excel_bytes(sheets)
    except Exception as e:  # pragma: no cover — defensive
        st.error(f"Failed to generate Excel file: {e}")
        return

    st.download_button(
        label=label,
        data=excel_bytes,
        file_name=filename,
        mime=_EXCEL_MIME,
        key=key,
        help=help,
    )
