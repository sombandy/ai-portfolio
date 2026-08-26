#!/usr/bin/env python

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN

# standard library
import math

# third-party
import pandas as pd
import yfinance as yf


def _positive_float(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def curr_price(tickers, crypto=False):
    if tickers is None or len(tickers) == 0:
        return None

    c_prices = pd.Series(dtype=float)
    prev_close_prices = pd.Series(dtype=float)

    for ticker in tickers:
        tick = yf.Ticker(ticker)

        # fast_info derives these values from daily price history. This matters for
        # 24-hour assets such as BTC, whose quote metadata can expose a stale
        # previousClose value for several days.
        fast_info = tick.fast_info
        curr_price_val = _positive_float(fast_info.get("last_price"))
        prev_close_val = _positive_float(fast_info.get("regular_market_previous_close"))

        if curr_price_val is None or prev_close_val is None:
            info = tick.info
            curr_price_val = curr_price_val or _positive_float(
                info.get("regularMarketPrice") or info.get("currentPrice")
            )
            prev_close_val = prev_close_val or _positive_float(
                info.get("regularMarketPreviousClose") or info.get("previousClose")
            )

        c_prices[ticker] = curr_price_val or 0.0
        prev_close_prices[ticker] = prev_close_val or 0.0

    c_prices.name = CN.PRICE

    # print("Previous close prices")
    # print(prev_close_prices.to_string())
    # print("Current prices")
    # print(c_prices.to_string())

    # Calculate day change using the prior daily close.
    day_change = pd.Series(0.0, index=c_prices.index)
    for ticker in tickers:
        if prev_close_prices[ticker] > 0:
            day_change[ticker] = (c_prices[ticker] - prev_close_prices[ticker]) / prev_close_prices[ticker]

    day_change = day_change.fillna(0)
    day_change.name = CN.DAY_CHNG
    return pd.concat([c_prices, day_change], axis=1)
