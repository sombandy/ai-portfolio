#!/usr/bin/env python

import json
import os
from datetime import date

from src.config.ColumnNameConsts import ColumnNames as CN

import gspread
import pandas as pd
from dotenv import load_dotenv

CONFIG_DIR = "../../config"

load_dotenv()

def load_gspread():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    credentials_file = os.path.join(cur_dir, CONFIG_DIR, "credentials.json")
    authorized_user_file = os.path.join(cur_dir, CONFIG_DIR, "authorized_user.json")

    if os.path.exists(authorized_user_file):
        credentials = json.loads(open(credentials_file).read())
        authorized_user = json.loads(open(authorized_user_file).read())
        gc, ret_au = gspread.oauth_from_dict(
            credentials,
            authorized_user,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )

        ret_au_json = json.loads(ret_au)
        with open(authorized_user_file, "w") as f:
            f.write(json.dumps(ret_au_json, indent=4))
    else:
        gc = gspread.oauth(
            credentials_filename=credentials_file,
            authorized_user_filename=authorized_user_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )

    return gc


def transactions(sheet_id=None):
    if not sheet_id:
        sheet_id = os.getenv("TRANSACTIONS_SHEET")

    gc = load_gspread()
    sh = gc.open_by_key(sheet_id)
    worksheet = sh.get_worksheet(0)

    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    df["Date"] = pd.to_datetime(df["Date"])

    cols = [CN.QTY, CN.COST_PRICE, CN.TOTAL]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    return df


def update_portfolio_summary(t, sheet_id=None, worksheet_id=None):
    """
    Update or insert portfolio summary data in Google Sheets for today's date.
    
    Args:
        t: DataFrame with single row containing portfolio summary data
        sheet_id: Google Sheets ID (optional, defaults to PORTFOLIO_SUMMARY_SHEET env var)
        worksheet_id: Specific worksheet/tab ID (optional, defaults to PORTFOLIO_SUMMARY_WORKSHEET env var)
    """
    
    if not sheet_id:
        sheet_id = os.getenv("TRANSACTIONS_SHEET")
        
    gc = load_gspread()
    sh = gc.open_by_key(sheet_id)
    
    try:
        worksheet = sh.worksheet("Net Worth")
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title="Net Worth", rows="1000", cols="8")
    
    existing_data = worksheet.get_all_values()
    headers = ["Date", "Total", "Market Value", "Gain", "Gain%", "Day Change", "Day Change Value", "Updated At"]
    if not existing_data or existing_data[0] != headers:
        worksheet.update('A1:H1', [headers])
    
    if hasattr(t, 'to_dict'):
        data = t.to_dict('records')[0]
    else:
        data = dict(t)
    
    today = date.today().strftime('%Y-%m-%d')
    
    total_value = data.get('Total', '0')
    market_value = data.get('Market Value', '0')
    gain_value = data.get('Gain', '0')
    gain_pct_value = round(float(data.get('Gain%', '0')), 2)
    day_change_value = round(float(data.get('Day Change', '0')), 2)
    day_change_val = data.get('Day Change Value', '0')
    updated_at = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    
    row_to_update = None
    existing_data = worksheet.get_all_values()
    
    for i, row in enumerate(existing_data[1:], start=2):
        if row and row[0] == today:
            row_to_update = i
            break
    
    gain_pct_decimal = gain_pct_value / 100
    day_change_decimal = day_change_value / 100
    
    row_data = [today, total_value, market_value, gain_value, gain_pct_decimal, day_change_decimal, day_change_val, updated_at]
    
    format_row = {
        "numberFormat": {
            "type": "PERCENT",
            "pattern": "0.00%"
        }
    }
    
    if row_to_update:
        worksheet.update(f'A{row_to_update}:H{row_to_update}', [row_data])
        print(f"Portfolio summary updated for {today}")
        worksheet.format(f'E{row_to_update}:F{row_to_update}', format_row)
    else:
        worksheet.insert_row(row_data, 2)
        print(f"Portfolio summary added for {today}")
        worksheet.format('E2:F2', format_row)
    
    return True
