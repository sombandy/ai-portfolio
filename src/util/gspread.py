#!/usr/bin/env python

import json
import os

from src.config.ColumnNameConsts import ColumnNames as CN

import gspread
import pandas as pd
from dotenv import load_dotenv

CONFIG_DIR = "../../config"


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
        load_dotenv()
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
