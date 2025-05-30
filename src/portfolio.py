#
# author: somnath.banerjee
#

# system

# first-party
from src.config.ColumnNameConsts import ColumnNames
from src.util.gspread import transactions
from src.util.yfinance import curr_price

# third-party
import pandas as pd

# database
from src.database.models import update_total

CN = ColumnNames


def load():
    t = transactions()
    h = t.groupby(["Category", "Company", "Ticker"])[["Qty", "Total"]].sum()
    h[CN.COST_PRICE] = h[CN.TOTAL] / h[CN.QTY]

    stocks = h.iloc[h.index.get_level_values("Category") != "Cryptocurrency"]
    cryptos = h.iloc[h.index.get_level_values("Category") == "Cryptocurrency"]
    # stocks = stocks[3:6] # only for debugging

    stock_prices = curr_price(stocks.index.get_level_values("Ticker"))
    crypto_prices = curr_price(cryptos.index.get_level_values("Ticker"), crypto=True)

    p = pd.concat([stock_prices, crypto_prices])
    h = h.join(p, on="Ticker", how="inner")
    h = h.set_index(h.index.droplevel(["Category"]))
    h.reset_index(inplace=True)

    if not h[h[CN.PRICE].isnull()].empty:
        null_tickers = h[h[CN.PRICE].isnull()][CN.TICKER].values
        print("Discarding null prices: " + ", ".join(null_tickers))
        h = h.dropna(axis=0)

    return h


def summary():
    s = load()

    s[CN.MARKET_VALUE] = s[CN.QTY] * s[CN.PRICE]
    s[CN.DAY_CHNG_VAL] = s[CN.MARKET_VALUE] * s[CN.DAY_CHNG] / (1 + s[CN.DAY_CHNG])

    s[CN.DAY_CHNG] = 100 * s[CN.DAY_CHNG]
    s[CN.GAIN] = s[CN.MARKET_VALUE] - s[CN.TOTAL]
    s[CN.GAIN_PCT] = 100 * s[CN.GAIN] / s[CN.TOTAL]

    t = s.sum()
    t = t[[CN.TOTAL, CN.MARKET_VALUE, CN.DAY_CHNG_VAL]]
    t[CN.GAIN] = t[CN.MARKET_VALUE] - t[CN.TOTAL]
    t[CN.GAIN_PCT] = 100 * t[CN.GAIN] / t[CN.TOTAL]
    t[CN.DAY_CHNG] = (
        100 * t[CN.DAY_CHNG_VAL] / (t[CN.MARKET_VALUE] - t[CN.DAY_CHNG_VAL])
    )

    t = t.to_frame().T
    t = t[
        [CN.TOTAL, CN.MARKET_VALUE, CN.GAIN, CN.GAIN_PCT, CN.DAY_CHNG, CN.DAY_CHNG_VAL]
    ]

    t[CN.TOTAL] = t[CN.TOTAL].apply(lambda x: f"${x:,.0f}")
    t[CN.MARKET_VALUE] = t[CN.MARKET_VALUE].apply(lambda x: f"${x:,.0f}")
    t[CN.GAIN] = t[CN.GAIN].apply(lambda x: f"${x:,.0f}")
    t[CN.DAY_CHNG_VAL] = t[CN.DAY_CHNG_VAL].apply(lambda x: f"${x:,.0f}")

    t[CN.GAIN_PCT] = t[CN.GAIN_PCT].apply(lambda x: f"{x:.2f}%")
    t[CN.DAY_CHNG] = t[CN.DAY_CHNG].apply(lambda x: f"{x:.2f}%")

    s = s[
        [
            CN.NAME,
            CN.TICKER,
            CN.PRICE,
            CN.DAY_CHNG,
            CN.QTY,
            CN.DAY_CHNG_VAL,
            CN.COST_PRICE,
            CN.TOTAL,
            CN.MARKET_VALUE,
            CN.GAIN,
            CN.GAIN_PCT,
        ]
    ]
    s = s.astype({CN.TOTAL: int, CN.MARKET_VALUE: int, CN.GAIN: int})
    s = s.round(2)
    s = s.sort_values(CN.DAY_CHNG, ascending=False)

    try:
        update_total(t)
    except Exception as e:
        print(f"Warning: Failed to save data to database: {e}")
    
    return s, t
