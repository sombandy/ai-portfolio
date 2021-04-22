# The main flask app
#
# author: somnath.banerjee
#

import portfolio as pf
from flask import Flask, render_template
app = Flask(__name__)

TR_DATA = "data/test_transactions.csv"

@app.route('/')
def home_page():
	s, t = pf.summary(TR_DATA)
	s_table = s.to_html(table_id="summary", index=False)
	t_table = t.to_html(index=False)
	return render_template("table_view.html", data=s_table + "\n<p>\n" + t_table)

@app.route('/summary')
def summary():
	s, _ = pf.summary(TR_DATA)
	return s.to_json()
