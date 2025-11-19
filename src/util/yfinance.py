#!/usr/bin/env python

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN

# third-party
import pandas as pd
import yfinance as yf

def curr_price(tickers, crypto=False):
    if tickers is None or len(tickers) == 0:
        return None

    c_prices = pd.Series(dtype=float)
    prev_close_prices = pd.Series(dtype=float)

    for ticker in tickers:
        tick = yf.Ticker(ticker)
        info = tick.info

        # Get previous close from ticker.info for accurate yesterday's price
        prev_close_val = info.get('previousClose') or info.get('regularMarketPreviousClose', 0)
        prev_close_prices[ticker] = prev_close_val

        # Get current price from ticker info
        curr_price_val = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        c_prices[ticker] = curr_price_val


    c_prices.name = CN.PRICE

    # print("Previous close prices")
    # print(prev_close_prices.to_string())
    # print("Current prices")
    # print(c_prices.to_string())

    # Calculate day change using previousClose from ticker info
    day_change = pd.Series(0.0, index=c_prices.index)
    for ticker in tickers:
        if prev_close_prices[ticker] > 0:
            day_change[ticker] = (c_prices[ticker] - prev_close_prices[ticker]) / prev_close_prices[ticker]

    day_change = day_change.fillna(0)
    day_change.name = CN.DAY_CHNG
    return pd.concat([c_prices, day_change], axis=1)
