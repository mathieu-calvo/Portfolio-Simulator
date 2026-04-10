# Portfolio Simulator: Source-Agnostic Backtesting & Analytics

A Python library and web application for building, backtesting, and comparing investment portfolios. Supports any financial data source (Yahoo Finance, Reuters, Bloomberg) and any asset type (ETFs, stocks, mutual funds, bonds, futures, crypto).

Inspired by [Curvo Backtest](https://curvo.eu/backtest/en/), built to go further: source-agnostic, asset-agnostic, fully extensible, and usable both as an importable library and a standalone web app.

## Who This Is For

- Individual investors who want to backtest portfolio strategies before committing capital
- Financial analysts building custom portfolio analysis workflows in Python
- Developers who need a pluggable backtesting engine they can extend with new data sources
- Anyone who wants a free, self-hosted alternative to commercial backtesting tools

## Features

| Category | What You Get |
|----------|-------------|
| **Portfolio Construction** | Build portfolios from any asset type, set target weights, save and manage |
| **Backtesting Engine** | Vectorized simulation with calendar-based, tolerance-based, or no rebalancing |
| **Investment Strategies** | Lump sum and dollar-cost averaging (DCA) with configurable monthly contributions |
| **Cost Modeling** | TER drag, transaction costs, management fees, capital gains tax on rebalances |
| **Return Analytics** | Cumulative, annualized, calendar-year, quarterly, monthly, rolling, multi-horizon (YTD/1Y/3Y/5Y/10Y) |
| **Risk Analytics** | Volatility, max drawdown, VaR, CVaR, rolling volatility, drawdown series |
| **Risk-Adjusted Ratios** | Sharpe, Sortino, Calmar, Information ratio |
| **Monte Carlo** | Future projections with 5-tier scenarios (P5/P25/P50/P75/P95) |
| **Efficient Frontier** | Mean-variance optimization, max Sharpe and min volatility portfolios |
| **Portfolio Comparison** | Side-by-side analytics and charts for up to 5 portfolios |
| **Interactive Charts** | Plotly-powered: evolution, drawdown, heatmaps, histograms, frontier plots, MC fan charts |
| **Data Sources** | Yahoo Finance built-in; plug in Reuters, Bloomberg, or CSV files via the Provider protocol |
| **Caching** | Two-tier (SQLite + in-memory LRU) so repeat queries are instant |
| **Currency Conversion** | FX rate fetching and series conversion between any currency pair |

## Prerequisites

- Python 3.11+
- pip

## Setup

```bash
git clone https://github.com/mathieu-calvo/Portfolio-Simulator.git
cd Portfolio-Simulator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick Start

### As a Python Library

```python
from datetime import date
from portfolio_simulator import Asset, Portfolio, PortfolioAllocation, SimulationConfig
from portfolio_simulator.providers.yahoo import YahooFinanceProvider
from portfolio_simulator.services.data_service import DataService
from portfolio_simulator.services.backtest_engine import BacktestEngine
from portfolio_simulator.analytics import returns, risk, ratios

# Set up
provider = YahooFinanceProvider()
data_service = DataService(provider)
engine = BacktestEngine(data_service)

# Build a portfolio
portfolio = Portfolio(
    name="Global 60/40",
    allocations=[
        PortfolioAllocation(asset=Asset(ticker="VTI", name="US Stocks"), weight=0.6),
        PortfolioAllocation(asset=Asset(ticker="BND", name="US Bonds"), weight=0.4),
    ],
)

# Configure and run backtest
config = SimulationConfig(
    start_date=date(2015, 1, 1),
    end_date=date(2024, 12, 31),
    initial_investment=10_000,
    rebalance_strategy="quarterly",
)
result = engine.run(portfolio, config)

# Analyze
print(f"Final value:        ${result.portfolio_value.iloc[-1]:,.2f}")
print(f"Cumulative return:  {returns.cumulative_return(result.portfolio_value):.1%}")
print(f"Annualized return:  {returns.annualized_return(result.portfolio_value):.1%}")
print(f"Max drawdown:       {risk.max_drawdown(result.portfolio_value).max_drawdown:.1%}")
print(f"Sharpe ratio:       {ratios.sharpe_ratio(result.portfolio_value):.2f}")
```

### As a Web App

```bash
streamlit run src/portfolio_simulator/ui/app.py
```

Then open `http://localhost:8501` in your browser.

## Repository Structure

```
Portfolio-Simulator/
├── pyproject.toml                          # Build config, dependencies
├── .env.example                            # Configuration template
│
├── src/
│   └── portfolio_simulator/
│       ├── __init__.py                     # Public API exports
│       ├── config.py                       # Pydantic Settings (env vars / .env)
│       │
│       ├── domain/                         # Pure data models
│       │   ├── enums.py                    # AssetType, Currency, RebalanceStrategy, ...
│       │   ├── asset.py                    # Asset model
│       │   ├── portfolio.py                # Portfolio + PortfolioAllocation
│       │   ├── simulation.py               # SimulationConfig
│       │   └── results.py                  # BacktestResult, MonteCarloResult
│       │
│       ├── providers/                      # Data source adapters
│       │   ├── base.py                     # DataProvider Protocol
│       │   ├── yahoo.py                    # Yahoo Finance (yfinance)
│       │   ├── csv_provider.py             # CSV files (offline / testing)
│       │   └── registry.py                 # Provider registry
│       │
│       ├── cache/                          # Market data caching
│       │   ├── base.py                     # CacheBackend Protocol
│       │   ├── sqlite_cache.py             # SQLite persistent cache
│       │   └── memory_cache.py             # In-memory LRU cache
│       │
│       ├── services/                       # Business logic
│       │   ├── data_service.py             # Fetch + cache orchestration
│       │   ├── backtest_engine.py          # Core simulation engine
│       │   ├── currency_service.py         # FX conversion
│       │   └── portfolio_store.py          # Portfolio persistence (SQLite)
│       │
│       ├── analytics/                      # Financial calculations
│       │   ├── returns.py                  # Return metrics
│       │   ├── risk.py                     # Risk metrics
│       │   ├── ratios.py                   # Risk-adjusted ratios
│       │   ├── monte_carlo.py              # Monte Carlo simulation
│       │   ├── efficient_frontier.py       # Mean-variance optimization
│       │   ├── comparison.py               # Multi-portfolio comparison
│       │   └── costs.py                    # Fee and tax impact
│       │
│       ├── visualization/                  # Plotly charts
│       │   ├── charts.py                   # All chart types
│       │   ├── tables.py                   # Summary tables
│       │   └── theme.py                    # Color palette and layout
│       │
│       ├── ui/                             # Streamlit web app
│       │   ├── app.py                      # Entrypoint
│       │   ├── pages/
│       │   │   ├── portfolio_builder.py    # Build and save portfolios
│       │   │   ├── backtest.py             # Run simulations
│       │   │   ├── comparison.py           # Compare portfolios
│       │   │   └── optimizer.py            # Efficient frontier + Monte Carlo
│       │   └── components/
│       │       ├── asset_picker.py         # Asset search widget
│       │       ├── weight_editor.py        # Weight allocation editor
│       │       └── metric_cards.py         # KPI display cards
│       │
│       └── utils/
│           ├── date_utils.py               # Business day math
│           └── validation.py               # Input validators
│
├── tests/
│   ├── conftest.py                         # Shared fixtures
│   ├── unit/                               # 62 unit tests
│   └── fixtures/
│       └── example_portfolios/             # JSON portfolio examples
│
└── notebooks/
    └── quickstart.ipynb                    # Library API demo
```

## Architecture

### Data Provider Pattern

Adding a new data source means implementing four methods:

```python
class DataProvider(Protocol):
    def get_price_history(self, ticker, start, end) -> pd.Series: ...
    def search_assets(self, query, asset_type, limit) -> list[AssetInfo]: ...
    def get_asset_info(self, ticker) -> AssetInfo: ...
    def get_fx_rates(self, base, quote, start, end) -> pd.Series: ...
```

Yahoo Finance is included. CSV files work for offline use and testing. Reuters and Bloomberg can be added by implementing the same protocol.

### Caching

Market data is cached in two tiers to minimize API calls:

1. **In-memory LRU** -- instant repeated access within a session
2. **SQLite on disk** -- persists across sessions with configurable TTL (default 24h)

### Analytics

All analytics functions are pure: they take a `pd.Series` (prices or returns) and return data. No I/O, no side effects, fully testable.

```python
from portfolio_simulator.analytics import returns, risk, ratios

returns.cumulative_return(prices)          # Total return
returns.annualized_return(prices)          # CAGR
returns.multi_horizon_returns(prices)      # YTD, 1Y, 3Y, 5Y, 10Y, Full
risk.max_drawdown(prices)                  # Peak-to-trough with dates
risk.value_at_risk(prices, 0.95)           # Historical VaR
ratios.sharpe_ratio(prices)               # Risk-adjusted return
ratios.sortino_ratio(prices)              # Downside-only penalty
```

## Configuration

All settings are configurable via environment variables (prefix `PSIM_`) or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `PSIM_DEFAULT_PROVIDER` | `yahoo` | Data source |
| `PSIM_CACHE_DIR` | `~/.portfolio_simulator` | Cache/DB location |
| `PSIM_CACHE_TTL_HOURS` | `24` | Cache expiry |
| `PSIM_DEFAULT_CURRENCY` | `USD` | Base currency |
| `PSIM_RISK_FREE_RATE` | `0.02` | For Sharpe ratio |
| `PSIM_MAX_CONCURRENT_FETCHES` | `10` | Parallel data downloads |

See [`.env.example`](.env.example) for the full template.

## Testing

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=portfolio_simulator
```

## Deployment

The Streamlit app can be deployed for free on [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Push to GitHub
2. Connect your repo at [share.streamlit.io](https://share.streamlit.io)
3. Set the main file to `src/portfolio_simulator/ui/app.py`
4. Add any API keys via the Secrets dashboard

## Roadmap

- [ ] Reuters and Bloomberg data providers
- [ ] Benchmark comparison (vs. S&P 500, etc.)
- [ ] Portfolio contribution breakdown (which assets drove returns)
- [ ] Tax-lot tracking for more accurate tax simulation
- [ ] Export reports to PDF
- [ ] User authentication for the hosted version

## License

MIT License. See [LICENSE](LICENSE) for details.
