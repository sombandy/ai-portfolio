#!/usr/bin/env python

# system

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN
from src.util.gspread import transactions
from src.util.yfinance import curr_price

# third-party
import streamlit as st
import pandas as pd


def loss_tracker():
    df = transactions()

    unique_tickers = df["Ticker"].unique()
    df_price = curr_price(unique_tickers)
    df_price.drop(CN.DAY_CHNG, axis=1, inplace=True)

    df = df.merge(df_price, on="Ticker", how="inner")
    df = df[df[CN.PRICE] < df[CN.COST_PRICE]]

    grouped = df.groupby("Ticker").agg({"Total": "sum", "Qty": "sum"}).reset_index()
    grouped = grouped.merge(df_price, on="Ticker", how="inner")
    grouped[CN.COST_PRICE] = grouped["Total"] / grouped["Qty"]
    
    columns = [CN.TICKER, CN.TOTAL, CN.QTY, CN.COST_PRICE, CN.PRICE]
    grouped = grouped[columns]

    grouped[CN.MARKET_VALUE] = grouped[CN.QTY] * grouped[CN.PRICE]
    grouped[CN.GAIN] = grouped[CN.MARKET_VALUE] - grouped[CN.TOTAL]
    grouped[CN.GAIN_PCT] = 100 * grouped[CN.GAIN] / grouped[CN.TOTAL]
    grouped = grouped.sort_values(by=CN.GAIN)
    grouped = grouped.astype({CN.QTY: int, CN.TOTAL: int, CN.MARKET_VALUE: int, CN.GAIN: int})
    grouped = grouped.round(2)

    print(grouped.to_string(index=False))
    return grouped


if __name__ == "__main__":
    df = loss_tracker()
    st.dataframe(df)