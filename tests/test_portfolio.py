import unittest

from portfolio import curr_price
from ColumnNameConsts import ColumnNames

CN = ColumnNames

class TestCurrPrice(unittest.TestCase):

    def test_single_price(self):
        tickers = ["BTC-USD"]
        data = curr_price(tickers, is_crypto=True)
        
        assert(data.index == tickers)
        assert(data[CN.PRICE].values[0] > 1000)

    def test_multiple_prices(self):
        tickers = ["AMZN", "AAPL"]
        data = curr_price(tickers)
        assert((data[CN.PRICE].values > 0 ).all())

if __name__ == '__main__':
    unittest.main()