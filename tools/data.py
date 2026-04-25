import time
from typing import Optional

import pandas as pd
import yfinance as yf

_REQUEST_DELAY_SECONDS = 0.5

SECTOR_ETFS = {
    "Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}


class DataFetchError(Exception):
    pass


def get_stock_universe() -> list[str]:
    """Scrape S&P 500 tickers from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url, header=0)
        df = tables[0]
        tickers = df["Symbol"].tolist()
        # yfinance uses dashes; Wikipedia uses dots (e.g. BRK.B -> BRK-B)
        return [t.replace(".", "-") for t in tickers]
    except Exception as e:
        raise DataFetchError(f"Failed to fetch S&P 500 universe: {e}")


def get_stock_details(ticker: str) -> dict:
    """Return comprehensive fundamental data for a single stock."""
    time.sleep(_REQUEST_DELAY_SECONDS)
    try:
        info = yf.Ticker(ticker).info
    except Exception as e:
        raise DataFetchError(f"yfinance error for {ticker}: {e}")

    return {
        "ticker": ticker,
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps_ttm": info.get("trailingEps"),
        "eps_forward": info.get("forwardEps"),
        "revenue_growth_yoy": info.get("revenueGrowth"),
        "earnings_growth_yoy": info.get("earningsGrowth"),
        "gross_margin": info.get("grossMargins"),
        "net_margin": info.get("profitMargins"),
        "debt_to_equity": info.get("debtToEquity"),
        "free_cash_flow": info.get("freeCashflow"),
        "dividend_yield": info.get("dividendYield"),
        "price_to_book": info.get("priceToBook"),
        "week_52_high": info.get("fiftyTwoWeekHigh"),
        "week_52_low": info.get("fiftyTwoWeekLow"),
        "avg_volume": info.get("averageVolume"),
        "beta": info.get("beta"),
        # Trimmed to keep context window usage reasonable
        "description": (info.get("longBusinessSummary") or "")[:400],
    }


def get_price_history(ticker: str, period: str = "1y") -> dict:
    """
    Return percentage price changes over 1mo/3mo/6mo/1y from a single
    Yahoo Finance fetch, plus a flag for trading above the 52-week average.
    """
    time.sleep(_REQUEST_DELAY_SECONDS)
    try:
        hist = yf.Ticker(ticker).history(period="1y")
    except Exception as e:
        raise DataFetchError(f"Price history error for {ticker}: {e}")

    if hist.empty:
        raise DataFetchError(f"No price history returned for {ticker}")

    closes = hist["Close"]
    current = float(closes.iloc[-1])

    def pct_change(lookback_days: int) -> Optional[float]:
        if len(closes) < lookback_days:
            return None
        past = float(closes.iloc[-lookback_days])
        return round((current - past) / past * 100, 2)

    avg_52w = float(closes.mean())

    return {
        "ticker": ticker,
        "current_price": round(current, 2),
        "change_1mo_pct": pct_change(21),
        "change_3mo_pct": pct_change(63),
        "change_6mo_pct": pct_change(126),
        "change_1y_pct": pct_change(252),
        "above_52w_avg": current > avg_52w if avg_52w else None,
    }


def get_sector_performance(sector: str) -> dict:
    """Return sector trend data via its representative SPDR ETF."""
    etf = SECTOR_ETFS.get(sector)
    if not etf:
        return {"sector": sector, "error": f"No ETF mapping for sector '{sector}'"}
    result = get_price_history(etf, period="1y")
    result["sector"] = sector
    result["etf"] = etf
    return result
