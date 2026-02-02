# Feature Implementation Plan: Historical Price Changes

**Overall Progress:** `0%`

## TLDR
Add 5 new columns to the home page table showing stock price changes over 7 days, 1 month, 3 months, 6 months, and 1 year. Use an in-memory cache to store historical reference prices (invalidated daily) to avoid repeated yfinance calls on page refreshes.

## Critical Decisions
- **No Postgres** - in-memory cache is sufficient given rare server restarts
- **Cache only 5 reference prices per ticker** - not full year of daily data
- **Date-based cache invalidation** - cache resets when date changes
- **Nearest trading day logic** - use most recent trading day before target (max 5 day lookback)
- **Bulk yfinance fetch** - `yf.download(tickers, period="1y")` for efficiency
- **Column order** - Day Change → 7D → 1M → 3M → 6M → 1Y → Qty...
- **Display format** - percentages with green/red coloring, "N/A" for insufficient data

## Tasks

- [ ] 🟥 **Step 1: Add column name constants**
  - [ ] 🟥 Add `CHNG_7D`, `CHNG_1M`, `CHNG_3M`, `CHNG_6M`, `CHNG_1Y` to `ColumnNameConsts.py`

- [ ] 🟥 **Step 2: Create historical price cache module**
  - [ ] 🟥 Create `src/util/historical_cache.py`
  - [ ] 🟥 Implement in-memory cache structure with date-based invalidation
  - [ ] 🟥 Implement `get_historical_prices(tickers)` function that:
    - Returns cached prices if cache date == today and ticker exists
    - Fetches missing tickers via `yf.download(tickers, period="1y")`
    - Extracts prices at 5 reference dates (nearest trading day logic)
    - Updates cache with fetched data

- [ ] 🟥 **Step 3: Implement nearest trading day logic**
  - [ ] 🟥 Calculate target dates (7d, 1m, 3m, 6m, 1y ago from today)
  - [ ] 🟥 Find nearest available trading day before each target (max 5 day lookback)
  - [ ] 🟥 Return `None` if no valid price found within lookback window

- [ ] 🟥 **Step 4: Integrate with portfolio.py**
  - [ ] 🟥 Call `get_historical_prices()` in `summary()` function
  - [ ] 🟥 Compute percentage changes: `(current_price - historical_price) / historical_price`
  - [ ] 🟥 Add 5 new columns to the summary DataFrame
  - [ ] 🟥 Handle `None` values as "N/A"

- [ ] 🟥 **Step 5: Update Flask template**
  - [ ] 🟥 Add 5 new column headers to `table_view.html`
  - [ ] 🟥 Apply green/red styling based on positive/negative values

- [ ] 🟥 **Step 6: Update DataTables configuration**
  - [ ] 🟥 Update `static/tables.js` with new column definitions
  - [ ] 🟥 Add percentage formatting for new columns
  - [ ] 🟥 Ensure columns are sortable

- [ ] 🟥 **Step 7: Test**
  - [ ] 🟥 Test with existing portfolio (normal case)
  - [ ] 🟥 Test adding a new ticker (cache miss → fetch)
  - [ ] 🟥 Test page refresh (cache hit)
  - [ ] 🟥 Test ticker with insufficient history (IPO < 1 year)
