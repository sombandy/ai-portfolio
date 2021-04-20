#
# author: somnath.banerjee
#
import getopt
import sys

import pandas as pd
import yfinance as yf

from ColumnNameConsts import ColumnNames

CN = ColumnNames


def curr_price(tickers):
	tickers_str = ' '.join(tickers)

	data = yf.download(tickers_str, period="2d", group_by='ticker')
	
	c_prices = data.iloc[-1].loc[(slice(None), 'Close')]
	c_prices.name = CN.PRICE

	d1_ago_price = data.iloc[-2].loc[(slice(None), 'Close')]
	day_change = (c_prices - d1_ago_price) / d1_ago_price
	day_change.name = CN.DAY_CHNG

	return pd.concat([c_prices, day_change], axis=1)

def holdings(inputfile):
	t = pd.read_csv(inputfile)
	h = t.groupby("Ticker")[[CN.QTY, "Total"]].sum()
	h[CN.COST_PRICE] = h[CN.TOTAL] / h[CN.QTY]
	return h

def summary(inputfile):
	h = holdings(inputfile)
	# h = h[3:6]

	c_prices = curr_price(h.index)
	s = pd.concat([h, c_prices], axis=1)
	s[CN.MARKET_VALUE] = s[CN.QTY] * s[CN.PRICE]
	s[CN.DAY_CHNG_VAL] = (s[CN.MARKET_VALUE] * s[CN.DAY_CHNG] / 
								(1 + s[CN.DAY_CHNG]))

	s[CN.DAY_CHNG] = 100 * s[CN.DAY_CHNG]
	s[CN.GAIN] = s[CN.MARKET_VALUE] - s[CN.TOTAL]

	s = s.round(2)
	s = s.astype({CN.TOTAL : int, CN.MARKET_VALUE : int, CN.GAIN : int})


	t = s.sum()
	t = t[[CN.TOTAL, CN.MARKET_VALUE, CN.DAY_CHNG_VAL]]
	t[CN.GAIN] = t[CN.MARKET_VALUE] - t[CN.TOTAL]
	t[CN.DAY_CHNG] = 100 * t[CN.DAY_CHNG_VAL] / (t[CN.MARKET_VALUE] - t[CN.DAY_CHNG_VAL])
	print(t[CN.DAY_CHNG_VAL], t[CN.MARKET_VALUE], t[CN.DAY_CHNG])

	t = t.to_frame().T
	t = t.astype({CN.TOTAL : int, CN.MARKET_VALUE : int, CN.GAIN : int,
					CN.DAY_CHNG_VAL : int})
	t = t.round(2)

	s = s[[CN.PRICE, CN.DAY_CHNG, CN.QTY, CN.DAY_CHNG_VAL, CN.COST_PRICE,
			CN.TOTAL, CN.MARKET_VALUE, CN.GAIN]]

	t = t[[CN.TOTAL, CN.MARKET_VALUE, CN.GAIN, CN.DAY_CHNG, CN.DAY_CHNG_VAL]]

	return s, t

def main(argv):
	inputfile = ""

	try:
		opts, args = getopt.getopt(argv, "hi:", ["ifile="])
	except getopt.GetoptError:
		print("daily_view.py -i <inputfile>")
		sys.exit(2)

	for opt, arg in opts:
		if opt == '-h':
			print("daily_view.py -i <inputfile> -o <outputfile>")
		elif opt in ('-i', "--ifile"):
			inputfile = arg

	if inputfile=="":
		print("Input or output file is not provided")
		sys.exit()

	print("Input file is " + inputfile)
	s, t = summary(inputfile)
	print(s.to_json())
	print(t.to_json())
	
if __name__ == "__main__":
	main(sys.argv[1:])
