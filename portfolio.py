#
# author: somnath.banerjee
#
import getopt
import sys

import pandas as pd
import yfinance as yf

from ColumnNameConsts import ColumnNames

CN = ColumnNames

def curr_price(tickers, is_crypto=False):
	if tickers is None or tickers.empty:
		return None

	tickers_str = ' '.join(tickers)

	period = "2d"
	if is_crypto:
		period = "3d"

	data = yf.download(tickers_str, period=period, group_by='ticker')

	if len(tickers) > 1:  # mutiple tickers
		c_prices = data.iloc[-1].loc[(slice(None), 'Close')]
		c_prices.name = CN.PRICE

		d1_ago_price = data.iloc[-2].loc[(slice(None), 'Close')]
		day_change = (c_prices - d1_ago_price) / d1_ago_price
		day_change.name = CN.DAY_CHNG
		return pd.concat([c_prices, day_change], axis=1)

	else: # single ticker
		c_price = data.iloc[-1]["Close"]
		d1_ago_price = data.iloc[-2]["Close"]
		day_change = (c_price - d1_ago_price) / d1_ago_price
		df = pd.DataFrame({CN.PRICE : c_price, CN.DAY_CHNG : day_change},
				index=[tickers[0]])
		return df

def load(inputfile):
	t = pd.read_csv(inputfile)
	h = t.groupby(["Category", "Company", "Ticker"])[["Qty", "Total"]].sum()
	h[CN.COST_PRICE] = h[CN.TOTAL] / h[CN.QTY]

	stocks = h.iloc[h.index.get_level_values("Category") != "Cryptocurrency"]
	cryptos = h.iloc[h.index.get_level_values("Category") == "Cryptocurrency"]
	# stocks = stocks[3:6] # only for debugging

	stock_prices = curr_price(stocks.index.get_level_values("Ticker"))
	crypto_prices = curr_price(cryptos.index.get_level_values("Ticker"), True)

	p = stock_prices.append(crypto_prices)
	h = h.join(p, on="Ticker", how="inner")
	h = h.set_index(h.index.droplevel(["Category"]))
	h.reset_index(inplace=True)

	return h

def summary(inputfile):
	s = load(inputfile)

	s[CN.MARKET_VALUE] = s[CN.QTY] * s[CN.PRICE]
	s[CN.DAY_CHNG_VAL] = (s[CN.MARKET_VALUE] * s[CN.DAY_CHNG] /
								(1 + s[CN.DAY_CHNG]))

	s[CN.DAY_CHNG] = 100 * s[CN.DAY_CHNG]
	s[CN.GAIN] = s[CN.MARKET_VALUE] - s[CN.TOTAL]

	t = s.sum()
	t = t[[CN.TOTAL, CN.MARKET_VALUE, CN.DAY_CHNG_VAL]]
	t[CN.GAIN] = t[CN.MARKET_VALUE] - t[CN.TOTAL]
	t[CN.GAIN_PCT] = 100 * t[CN.GAIN] / t[CN.TOTAL]
	t[CN.DAY_CHNG] = 100 * t[CN.DAY_CHNG_VAL] / (t[CN.MARKET_VALUE] - t[CN.DAY_CHNG_VAL])

	t = t.to_frame().T
	t = t[[CN.TOTAL, CN.MARKET_VALUE, CN.GAIN, CN.GAIN_PCT, CN.DAY_CHNG, CN.DAY_CHNG_VAL]]
	t = t.astype({CN.TOTAL : int, CN.MARKET_VALUE : int, CN.GAIN : int,
					CN.DAY_CHNG_VAL : int})
	t = t.round(2)

	s = s[[CN.NAME, CN.TICKER, CN.PRICE, CN.DAY_CHNG, CN.QTY, CN.DAY_CHNG_VAL,
			CN.COST_PRICE, CN.TOTAL, CN.MARKET_VALUE, CN.GAIN]]
	s = s.astype({CN.TOTAL : int, CN.MARKET_VALUE : int, CN.GAIN : int})
	s = s.round(2)

	return s, t

def main(argv):
	inputfile = ""

	try:
		opts, _ = getopt.getopt(argv, "hi:", ["ifile="])
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
