"""Domain enumerations for portfolio simulation."""

from enum import Enum


class AssetType(str, Enum):
    ETF = "etf"
    STOCK = "stock"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    INDEX = "index"
    FUTURES = "futures"
    CRYPTO = "crypto"


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CHF = "CHF"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"


class RebalanceStrategy(str, Enum):
    NONE = "none"
    CALENDAR = "calendar"
    TOLERANCE = "tolerance"


class RebalanceFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class InvestmentStrategy(str, Enum):
    LUMP_SUM = "lump_sum"
    DCA = "dca"
