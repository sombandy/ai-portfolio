#!/usr/bin/env python

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN

# third-party
import pandas as pd
import yfinance as yf

def curr_price(tickers):
    if tickers is None or len(tickers) == 0:
        return None

    tickers_str = ' '.join(tickers)

    yesterday = (pd.Timestamp.today() - pd.DateOffset(days=1)).strftime("%Y-%m-%d")
    data = yf.download(tickers_str, start=yesterday, group_by='ticker')

    c_prices = data.iloc[-1].loc[(slice(None), 'Close')]
    c_prices.name = CN.PRICE

    d1_ago_price = data.iloc[-2].loc[(slice(None), 'Close')]
    day_change = (c_prices - d1_ago_price) / d1_ago_price
    day_change.name = CN.DAY_CHNG
    return pd.concat([c_prices, day_change], axis=1)
