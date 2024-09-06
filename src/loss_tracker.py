#!/usr/bin/env python

# system

# first-party
from src.config.ColumnNameConsts import ColumnNames as CN
from src.util.gspread import transactions
from src.util.yfinance import curr_price

# third-party
import pandas as pd


def loss_tracker():
    df = transactions()

    unique_tickers = df["Ticker"].unique()
    df_price = curr_price(unique_tickers)
    df_price.drop(CN.DAY_CHNG, axis=1, inplace=True)

    df = df.merge(df_price, on="Ticker", how="inner")
    df = df[df[CN.PRICE] < df[CN.COST_PRICE]]

    df = df.groupby("Ticker").agg({"Total": "sum", "Qty": "sum"}).reset_index()
    df = df.merge(df_price, on="Ticker", how="inner")
    df[CN.COST_PRICE] = df["Total"] / df["Qty"]
    
    columns = [CN.TICKER, CN.TOTAL, CN.QTY, CN.COST_PRICE, CN.PRICE]
    df = df[columns]

    df[CN.MARKET_VALUE] = df[CN.QTY] * df[CN.PRICE]
    df[CN.GAIN] = df[CN.MARKET_VALUE] - df[CN.TOTAL]
    df[CN.GAIN_PCT] = 100 * df[CN.GAIN] / df[CN.TOTAL]
    df = df.sort_values(by=CN.GAIN)
    df = df.round(2)

    total_invested = df["Total"].sum()
    total_gains = df[CN.GAIN].sum()
    total_market_value = df[CN.MARKET_VALUE].sum()
    gain_pct = 100 * total_gains / total_invested
    total_df = pd.DataFrame(
        [["Total", total_invested, total_market_value, total_gains, gain_pct]],
        columns=[CN.TICKER, CN.TOTAL, CN.MARKET_VALUE, CN.GAIN, CN.GAIN_PCT],
    )
    total_df = total_df.astype({CN.GAIN: int, CN.GAIN_PCT: float})
    total_df = total_df.round(2)

    cols = [CN.TOTAL, CN.MARKET_VALUE, CN.GAIN]
    df[cols] = df[cols].map(lambda x: "{:,.0f}".format(x))
    total_df[cols] = total_df[cols].map(lambda x: "{:,.0f}".format(x))

    print(df.to_string(index=False))
    print("\n")
    print(total_df.to_string(index=False))
    print("\n")
    return df, total_df


if __name__ == "__main__":
    loss_tracker()