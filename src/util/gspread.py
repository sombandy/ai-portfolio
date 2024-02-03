#!/usr/bin/env python

# third-party
import json
import os
import gspread

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
    else:
        gc = gspread.oauth(
            credentials_filename=credentials_file,
            authorized_user_filename=authorized_user_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

    return gc
