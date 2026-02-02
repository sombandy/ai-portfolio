
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
        # Fetch 2 years of data to ensure we have enough buffer for 1Y lookback
        # (period="1y" sometimes falls short by a day or lands on a weekend/holiday at the very start)
        data = yf.download(tickers, period="2y", group_by='ticker', auto_adjust=True, threads=True)
        
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
        
    # Ensure index is sorted
    df = df.sort_index()
    
    for period, target_date in target_dates.items():
        # Get data up to target_date
        # Since we want "price a month ago", we want the price on (Today - 30d).
        # We look for the last available trading day <= target_date.
        
        subset = df.loc[:target_date]
        if subset.empty:
            continue
            
        # Filter out rows with NaN prices (e.g. weekends for stocks in multi-ticker df)
        subset = subset[subset['Close'].notna()]
        
        if subset.empty:
            continue
            
        last_entry = subset.iloc[-1]
        last_date = subset.index[-1]
        
        # Check lookback window (max 5 days)
        # We don't want a price from 2 months ago representing 1 month ago if trading was halted
        if (target_date - last_date).days > 5:
            continue
            
        price = last_entry['Close']
        
        # Handle potential NaN
        if pd.notna(price):
            prices[period] = float(price)
            
    return prices
