import time
from typing import Optional

import yfinance as yf

_BATCH_SIZE = 50
_BATCH_DELAY = 2.0
_TICKER_DELAY = 0.3


def screen_stocks(
    tickers: list[str],
    min_market_cap: Optional[float] = None,
    max_market_cap: Optional[float] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_avg_volume: Optional[float] = None,
    max_pe_ratio: Optional[float] = None,
    sector: Optional[str] = None,
) -> list[dict]:
    """
    Batch-filter tickers by fundamental KPIs using yfinance.
    All filter conditions are AND-combined; unset filters are ignored.
    Tickers that fail to load are silently skipped.
    Returns a compact summary dict per passing stock.
    """
    results = []

    for batch_start in range(0, len(tickers), _BATCH_SIZE):
        batch = tickers[batch_start: batch_start + _BATCH_SIZE]

        for ticker in batch:
            time.sleep(_TICKER_DELAY)
            try:
                info = yf.Ticker(ticker).info
            except Exception:
                continue

            market_cap = info.get("marketCap")
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            avg_vol = info.get("averageVolume")
            pe = info.get("trailingPE")
            stk_sector = info.get("sector")

            if min_market_cap is not None and (market_cap is None or market_cap < min_market_cap):
                continue
            if max_market_cap is not None and market_cap is not None and market_cap > max_market_cap:
                continue
            if min_price is not None and (price is None or price < min_price):
                continue
            if max_price is not None and price is not None and price > max_price:
                continue
            if min_avg_volume is not None and (avg_vol is None or avg_vol < min_avg_volume):
                continue
            if max_pe_ratio is not None and pe is not None and pe > max_pe_ratio:
                continue
            if sector is not None and stk_sector != sector:
                continue

            results.append({
                "ticker": ticker,
                "name": info.get("longName"),
                "sector": stk_sector,
                "price": price,
                "market_cap": market_cap,
                "pe_ratio": pe,
                "avg_volume": avg_vol,
                "week_52_high": info.get("fiftyTwoWeekHigh"),
                "week_52_low": info.get("fiftyTwoWeekLow"),
            })

        if batch_start + _BATCH_SIZE < len(tickers):
            time.sleep(_BATCH_DELAY)

    return results
