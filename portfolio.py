#
# author: somnath.banerjee
#
import getopt
import pandas as pd
import sys
import yfinance as yf

def curr_price(tickers):
	tickers_str = ' '.join(tickers)

	data = yf.download(tickers_str, period="2d", group_by='ticker')
	
	c_prices = data.iloc[-1].loc[(slice(None), 'Close')]
	c_prices.name = "Curr Price"

	d1_ago_price = data.iloc[-2].loc[(slice(None), 'Close')]
	day_change = (c_prices - d1_ago_price) / d1_ago_price
	day_change.name = "Day Change"

	return pd.concat([c_prices, day_change], axis=1)

def holdings(inputfile):
	t = pd.read_csv(inputfile)
	h = t.groupby("Ticker")[["Qty", "Total"]].sum()
	h["Cost Price"] = h["Total"] / h["Qty"]
	return h

def summary(inputfile):
	h = holdings(inputfile)
	# h = h[3:6]

	c_prices = curr_price(h.index)
	s = pd.concat([h, c_prices], axis=1)
	s["Market Value"] = s["Qty"] * s["Curr Price"]
	s["Day Change Value"] = s["Market Value"] * s["Day Change"] / (1 + s["Day Change"])
	s["Day Change"] = 100 * s["Day Change"]
	s["Gain"] = s["Market Value"] - s["Total"]

	s = s.round(2)
	s = s.astype({"Total" : int, "Market Value" : int, "Gain" : int})
	s = s.sort_values(by="Day Change", ascending=False)

	t = s.sum()
	t = t[["Total", "Market Value", "Day Change Value"]]
	t["Day Change Pct"] = 100 * t["Day Change Value"] / (t["Market Value"] - t["Day Change Value"])
	t["Gain"] = t["Market Value"] - t["Total"]
	t = t.to_frame().T
	t = t.astype({"Total" : int, "Market Value" : int, "Gain" : int})
	t = t.round(2)

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
