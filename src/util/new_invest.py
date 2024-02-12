#!/usr/bin/env python

# system
import argparse
import datetime

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN
from src.util.gspread import transactions
from src.util.yfinance import curr_price

# third-party
# import streamlit as st
import pandas as pd


def new_investements(months=None):
    df = transactions()

    if not months:
        current_year = datetime.datetime.now().year
        print("Looking for current year: ", current_year)
        df = df[df["Date"].dt.year == current_year]
    else:
        today = datetime.date.today()
        start_date = today - pd.DateOffset(months=months)
        start_date = start_date.strftime("%Y-%m-%d")
        print("Looking investments from ", start_date, " to ", today)
        df = df[df["Date"] >= start_date]

    grouped = df.groupby("Ticker").agg({"Total": "sum", "Qty": "sum"}).reset_index()
    grouped[CN.COST_PRICE] = grouped["Total"] / grouped["Qty"]
    df = grouped.sort_values("Total", ascending=False)

    df_price = curr_price(df["Ticker"])
    df = df.join(df_price, on="Ticker", how="inner")
    df.drop(CN.DAY_CHNG, axis=1, inplace=True)

    df[CN.GAIN] = df[CN.QTY] * (df[CN.PRICE] - df[CN.COST_PRICE])
    df[CN.GAIN_PCT] = df[CN.GAIN] / df[CN.TOTAL]

    total_invested = df["Total"].sum()
    total_gains = df[CN.GAIN].sum()
    gain_pct = total_gains / total_invested
    all_row = pd.DataFrame(
        [["Total", total_invested, total_gains, gain_pct]],
        columns=["Ticker", "Total", CN.GAIN, CN.GAIN_PCT],
    )
    df["Investment Pct"] = df["Total"].apply(lambda x: (x / total_invested))

    df[CN.QTY] = df[CN.QTY].map("{:,.0f}".format)

    cols = [CN.TOTAL, CN.GAIN]
    df[cols] = df[cols].map(lambda x: "${:,.0f}".format(x))

    cols = [CN.COST_PRICE, CN.PRICE]
    df[cols] = df[cols].map(lambda x: "${:,.2f}".format(x))

    cols = [CN.GAIN_PCT, "Investment Pct"]
    df[cols] = df[cols].map(lambda x: "{:,.2f}%".format(x * 100))

    cols = [CN.TOTAL, CN.GAIN]
    all_row[cols] = all_row[cols].map(lambda x: "${:,.0f}".format(x))

    cols = CN.GAIN_PCT
    all_row[cols] = all_row[cols].map(lambda x: "{:,.2f}%".format(x * 100))
    df = pd.concat([df, all_row], ignore_index=True)

    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-m", "--months", type=int)
    args = argparser.parse_args()

    df = new_investements(args.months)
    # st.table(df).sortable(True)
