#
# author: somnath.banerjee
#

import pandas as pd

from src.config.ColumnNameConsts import ColumnNames as CN
from src.portfolio_data import get_enriched_open_positions
from src.util.gspread import update_portfolio_summary


def load():
    enriched = get_enriched_open_positions()
    return _positions_to_dataframe(enriched["positions"])


def summary():
    enriched = get_enriched_open_positions()
    s = _positions_to_dataframe(enriched["positions"])
    t = _totals_to_dataframe(enriched["positions"])

    formatted_t = t.copy()
    for column in [CN.TOTAL, CN.MARKET_VALUE, CN.GAIN, CN.DAY_CHNG_VAL]:
        formatted_t[column] = formatted_t[column].apply(lambda x: f"${x:,.0f}")

    for column in [CN.GAIN_PCT, CN.DAY_CHNG]:
        formatted_t[column] = formatted_t[column].apply(lambda x: f"{x:.2f}%")

    try:
        update_portfolio_summary(t)
    except Exception as e:
        print(f"Warning: Failed to save data to Google Sheets: {e}")

    return s, formatted_t


def _positions_to_dataframe(positions):
    s = pd.DataFrame(
        [
            {
                CN.NAME: pos["company"],
                CN.TICKER: pos["ticker"],
                CN.PRICE: pos["current_price"],
                CN.QTY: pos["qty"],
                CN.DAY_CHNG: pos["day_change_pct"],
                CN.DAY_CHNG_VAL: pos["day_change_value"],
                CN.COST_PRICE: pos["average_cost"],
                CN.TOTAL: pos["total_cost_basis"],
                CN.MARKET_VALUE: pos["market_value"],
                CN.GAIN_PCT: pos["gain_pct"],
                CN.GAIN: pos["gain"],
                CN.CHNG_7D: pos["change_7d_pct"],
                CN.CHNG_1M: pos["change_1m_pct"],
                CN.CHNG_3M: pos["change_3m_pct"],
                CN.CHNG_6M: pos["change_6m_pct"],
                CN.CHNG_1Y: pos["change_1y_pct"],
            }
            for pos in positions
        ],
        columns=[
            CN.NAME,
            CN.TICKER,
            CN.PRICE,
            CN.QTY,
            CN.DAY_CHNG,
            CN.DAY_CHNG_VAL,
            CN.COST_PRICE,
            CN.TOTAL,
            CN.MARKET_VALUE,
            CN.GAIN_PCT,
            CN.GAIN,
            CN.CHNG_7D,
            CN.CHNG_1M,
            CN.CHNG_3M,
            CN.CHNG_6M,
            CN.CHNG_1Y,
        ],
    )

    if s.empty:
        return s

    money_columns = [CN.TOTAL, CN.MARKET_VALUE, CN.GAIN]
    s[money_columns] = s[money_columns].round(0).astype("Int64")
    s = s.round(2)
    return s.sort_values(CN.DAY_CHNG, ascending=False, na_position="last")


def _totals_to_dataframe(positions):
    total_cost_basis = sum(pos["total_cost_basis"] or 0 for pos in positions)
    priced_cost_basis = sum(
        pos["total_cost_basis"] or 0 for pos in positions if pos["market_value"] is not None
    )
    market_value = sum(pos["market_value"] or 0 for pos in positions)
    gain = sum(pos["gain"] or 0 for pos in positions)
    day_change_value = sum(pos["day_change_value"] or 0 for pos in positions)
    previous_market_value = market_value - day_change_value

    gain_pct = 100 * gain / priced_cost_basis if priced_cost_basis else 0
    day_change_pct = (
        100 * day_change_value / previous_market_value if previous_market_value else 0
    )

    return pd.DataFrame(
        [
            {
                CN.TOTAL: total_cost_basis,
                CN.MARKET_VALUE: market_value,
                CN.GAIN: gain,
                CN.GAIN_PCT: gain_pct,
                CN.DAY_CHNG: day_change_pct,
                CN.DAY_CHNG_VAL: day_change_value,
            }
        ],
        columns=[
            CN.TOTAL,
            CN.MARKET_VALUE,
            CN.GAIN,
            CN.GAIN_PCT,
            CN.DAY_CHNG,
            CN.DAY_CHNG_VAL,
        ],
    )
