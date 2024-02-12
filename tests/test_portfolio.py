#!/usr/bin/env python

# first-party
from src.util.yfinance import curr_price
from src.config.ColumnNameConsts import ColumnNames as CN

# third-party
import pytest


def test_single_price():
    tickers = ["BTC-USD"]
    data = curr_price(tickers, is_crypto=True)
    print(data)

    assert data.index == tickers
    assert data[CN.PRICE].values[0] > 1000


def test_multiple_prices():
    tickers = ["AMZN", "AAPL"]
    data = curr_price(tickers)
    print(data)
    assert (data[CN.PRICE].values > 0).all()
