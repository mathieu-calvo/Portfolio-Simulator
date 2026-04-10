"""Currency conversion service."""

from __future__ import annotations

from datetime import date

import pandas as pd

from portfolio_simulator.services.data_service import DataService


class CurrencyService:
    """Converts price series between currencies using FX rates from DataService."""

    def __init__(self, data_service: DataService) -> None:
        self._data_service = data_service

    def convert_series(
        self,
        series: pd.Series,
        from_currency: str,
        to_currency: str,
    ) -> pd.Series:
        """Convert a price/value series from one currency to another.

        Args:
            series: Price series with DatetimeIndex.
            from_currency: Source currency code.
            to_currency: Target currency code.

        Returns:
            Converted series with same index.
        """
        if from_currency == to_currency:
            return series

        start = series.index[0].date()
        end = series.index[-1].date()
        fx = self._data_service.get_fx_rates(from_currency, to_currency, start, end)

        # Align FX rates to the price series index
        fx_aligned = fx.reindex(series.index, method="ffill")
        converted = series * fx_aligned
        converted.name = series.name
        return converted

    def convert_dataframe(
        self,
        df: pd.DataFrame,
        from_currencies: dict[str, str],
        to_currency: str,
    ) -> pd.DataFrame:
        """Convert multiple columns, each potentially in a different currency.

        Args:
            df: DataFrame with DatetimeIndex, one column per asset.
            from_currencies: Map of column name -> source currency code.
            to_currency: Target currency code.

        Returns:
            Converted DataFrame.
        """
        result = pd.DataFrame(index=df.index)
        for col in df.columns:
            from_ccy = from_currencies.get(col, to_currency)
            result[col] = self.convert_series(df[col], from_ccy, to_currency)
        return result
