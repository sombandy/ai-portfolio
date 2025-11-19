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

    # Separate stocks and crypto to use appropriate price fetching
    stocks = df[df["Category"] != "Cryptocurrency"]
    cryptos = df[df["Category"] == "Cryptocurrency"]

    # Fetch prices separately for stocks and crypto
    stock_prices = curr_price(stocks["Ticker"].unique())
    if not cryptos.empty:
        crypto_prices = curr_price(cryptos["Ticker"].unique(), crypto=True)
        df_price = pd.concat([stock_prices, crypto_prices])
    else:
        df_price = stock_prices

    df_price.drop(CN.DAY_CHNG, axis=1, inplace=True)
    df_price = df_price.reset_index().rename(columns={"index": "Ticker"})

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