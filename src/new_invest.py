#!/usr/bin/env python

# system
import argparse
import datetime

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN
from src.util.gspread import transactions
from src.util.yfinance import curr_price

# third-party
import pandas as pd
import streamlit as st


def new_investements(months=0, days=0):
    df = transactions()

    today = datetime.date.today()
    if not months and not days:
        start_date = datetime.date(today.year, 1, 1)
    elif months > 0:
        start_date = today - pd.DateOffset(months=months)
    elif days > 0:
        start_date = today - pd.DateOffset(days=days)

    start_date = start_date.strftime("%Y-%m-%d")
    print("Looking investments from ", start_date, " to ", today)
    df = df[df["Date"] >= start_date]

    grouped = df.groupby("Ticker").agg({"Total": "sum", "Qty": "sum"}).reset_index()
    grouped[CN.COST_PRICE] = grouped["Total"] / grouped["Qty"]
    df = grouped.sort_values("Total", ascending=False)

    df_price = curr_price(df["Ticker"])
    df = df.join(df_price, on="Ticker", how="inner")
    df.drop(CN.DAY_CHNG, axis=1, inplace=True)

    df[CN.MARKET_VALUE] = df[CN.QTY] * df[CN.PRICE]
    df[CN.GAIN] = df[CN.QTY] * (df[CN.PRICE] - df[CN.COST_PRICE])
    df[CN.GAIN_PCT] = df[CN.GAIN] / df[CN.TOTAL]

    total_invested = df["Total"].sum()
    total_gains = df[CN.GAIN].sum()
    total_market_value = df[CN.MARKET_VALUE].sum()
    gain_pct = 100 * total_gains / total_invested
    total_df = pd.DataFrame(
        [["Total", total_invested, total_market_value, total_gains, gain_pct]],
        columns=[CN.TICKER, CN.TOTAL, CN.MARKET_VALUE, CN.GAIN, CN.GAIN_PCT],
    )

    df["Investment Pct"] = df["Total"].apply(lambda x: (x / total_invested))

    df[CN.QTY] = df[CN.QTY].map("{:,.0f}".format)

    cols = [CN.TOTAL, CN.MARKET_VALUE, CN.GAIN]
    df[cols] = df[cols].map(lambda x: "{:,.0f}".format(x))
    total_df[cols] = total_df[cols].map(lambda x: "{:,.0f}".format(x))

    cols = [CN.COST_PRICE, CN.PRICE]
    df[cols] = df[cols].map(lambda x: "${:,.2f}".format(x))

    cols = [CN.GAIN_PCT, "Investment Pct"]
    df[cols] = df[cols].map(lambda x: "{:,.2f}%".format(x * 100))

    cols = CN.GAIN_PCT
    total_df[cols] = total_df[cols].map(lambda x: "{:,.2f}%".format(x))

    print(df.to_string(index=False))
    print("\n")
    print(total_df.to_string(index=False))
    print("\n")
    return df, total_df


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-m", "--months", type=int, default=0)
    argparser.add_argument("-d", "--days", type=int, default=0)
    args = argparser.parse_args()

    df, total_df = new_investements(args.months, args.days)
    st.dataframe(df)
    st.dataframe(total_df)