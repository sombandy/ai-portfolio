#!/usr/bin/env python

# first-party
import argparse
import datetime
from src.util.gspread import load_gspread

# third-party
import pandas as pd

TR_FILE_KEY = "1KacMHxZpEOnud6F46m81AGC_lBpXpPvZJtCXwxHa1H0"


def new_investements(months=None):
    gc = load_gspread()
    sh = gc.open_by_key(TR_FILE_KEY)
    worksheet = sh.get_worksheet(0)

    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    df["Date"] = pd.to_datetime(df["Date"])
    df[["Total", "Qty"]] = df[["Total", "Qty"]].apply(pd.to_numeric, errors="coerce")

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

    grouped = df.groupby("Company").agg({"Total": "sum", "Qty": "sum"}).reset_index()
    grouped["Avg Price"] = grouped["Total"] / grouped["Qty"]
    df = grouped.sort_values("Total", ascending=False)

    total_invested = df["Total"].sum()
    all_row = pd.DataFrame([["Total", total_invested]], columns=["Company", "Total"])
    df = pd.concat([df, all_row], ignore_index=True)
    df["Percentage"] = df["Total"].apply(lambda x: (x / total_invested) * 100)

    df["Total"] = df["Total"].map("${:,.0f}".format)
    df["Qty"] = df["Qty"].map("{:,.0f}".format)
    df["Avg Price"] = df["Avg Price"].map("${:,.2f}".format)
    df["Percentage"] = df["Percentage"].map("{:,.2f}%".format)

    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-m", "--months", type=int)
    args = argparser.parse_args()

    new_investements(args.months)
