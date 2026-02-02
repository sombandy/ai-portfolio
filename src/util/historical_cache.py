
import datetime
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional

_price_cache: Dict[str, Dict[str, float]] = {}
_cache_date: Optional[datetime.date] = None

def get_historical_prices(tickers: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Get historical prices for the given tickers.
    Returns a dictionary mapping ticker -> { '7D': price, '1M': price, ... }
    """
    global _cache_date, _price_cache
    
    today = datetime.date.today()
    
    # Invalidate cache if date has changed
    if _cache_date != today:
        _price_cache = {}
        _cache_date = today
        
    # Identify missing tickers
    # We filter out tickers that are already in cache
    missing_tickers = [t for t in tickers if t not in _price_cache]
    
    if missing_tickers:
        _fetch_and_cache_prices(missing_tickers)
        
    # Return requested tickers from cache
    return {t: _price_cache.get(t, {}) for t in tickers}

def _fetch_and_cache_prices(tickers: List[str]):
    """
    Fetches 1 year of history for missing tickers and calculates reference prices.
    """
    if not tickers:
        return

    try:
        # Fetch 1 year of data
        # auto_adjust=True ensures we get split/dividend adjusted prices (usually in 'Close')
        data = yf.download(tickers, period="1y", group_by='ticker', auto_adjust=True, threads=True)
        
        if data.empty:
            for t in tickers:
                _price_cache[t] = {}
            return

        # Calculate target dates
        targets = {
            "7D": datetime.timedelta(days=7),
            "1M": datetime.timedelta(days=30),
            "3M": datetime.timedelta(days=90),
            "6M": datetime.timedelta(days=180),
            "1Y": datetime.timedelta(days=365)
        }
        
        today_ts = pd.Timestamp(datetime.date.today())
        target_dates = {k: today_ts - v for k, v in targets.items()}
        
        # Handle single ticker case (yf returns flat DataFrame if 1 ticker)
        if len(tickers) == 1:
            # To unify logic, wrap it to look like multiple ticker structure or handle separately
            # If flat, columns are Open, High, Low, Close, Volume
            t = tickers[0]
            _price_cache[t] = _extract_prices_from_series(data, target_dates)
        else:
            # Multi-index columns: (Ticker, OHLCV)
            for t in tickers:
                if t in data.columns.levels[0]:
                    ticker_df = data[t]
                    _price_cache[t] = _extract_prices_from_series(ticker_df, target_dates)
                else:
                    _price_cache[t] = {}
                    
    except Exception as e:
        print(f"Error fetching historical prices: {e}")
        # Prevent partial failures from blocking future attempts? 
        # Or mark failed tickers as empty to avoid retry?
        for t in tickers:
            if t not in _price_cache:
                _price_cache[t] = {}

def _extract_prices_from_series(df: pd.DataFrame, target_dates: Dict[str, pd.Timestamp]) -> Dict[str, float]:
    """
    Finds the nearest price before or on the target date (max 5 days lookback).
    Assumes df has a 'Close' column and DatetimeIndex.
    """
    prices = {}
    if 'Close' not in df.columns:
        return {}

    # Filter out NaN prices upfront
    df = df[df['Close'].notna()]
    if df.empty:
        return {}

    # Ensure index is sorted
    df = df.sort_index()
    
    for period, target_date in target_dates.items():
        # Find the index of the nearest date in the DataFrame
        # 'method="nearest"' works well if we have continuous data, but we need to validate distance
        try:
             # get_indexer returns array of indices, we need the first one
             idx_loc = df.index.get_indexer([target_date], method="nearest")[0]
             
             # Check if index is valid (get_indexer can return -1 if empty, but we checked empty)
             if idx_loc == -1:
                 continue
                 
             nearest_date = df.index[idx_loc]
             price = df.iloc[idx_loc]['Close']
             
             # Calculate distance in days
             distance = abs((target_date - nearest_date).days)
             
             # Tolerance:
             # For 1Y, if data starts slightly after target (e.g. 2-3 days), acceptable.
             # For 7D, finding nearest trading day (prev or next) within 5 days is acceptable.
             if distance <= 7:
                 if pd.notna(price):
                     prices[period] = float(price)
                     
        except Exception:
            # Fallback or ignore
            pass
            
    return prices
