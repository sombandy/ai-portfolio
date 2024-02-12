#!/usr/bin/env python

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN

# third-party
import pandas as pd
import yfinance as yf

def curr_price(tickers, is_crypto=False):
    if tickers is None or len(tickers) == 0:
        return None

    tickers_str = ' '.join(tickers)

    period = "2d"
    if is_crypto:
        period = "3d"

    data = yf.download(tickers_str, period=period, group_by='ticker')

    if len(tickers) > 1:  # mutiple tickers
        c_prices = data.iloc[-1].loc[(slice(None), 'Close')]
        c_prices.name = CN.PRICE

        d1_ago_price = data.iloc[-2].loc[(slice(None), 'Close')]
        day_change = (c_prices - d1_ago_price) / d1_ago_price
        day_change.name = CN.DAY_CHNG
        return pd.concat([c_prices, day_change], axis=1)

    else: # single ticker
        c_price = data.iloc[-1]["Close"]
        d1_ago_price = data.iloc[-2]["Close"]
        day_change = (c_price - d1_ago_price) / d1_ago_price
        df = pd.DataFrame({CN.PRICE : c_price, CN.DAY_CHNG : day_change},
            index=[tickers[0]])
        return df
