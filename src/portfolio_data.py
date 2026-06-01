from __future__ import annotations

import os
from collections import Counter, defaultdict
from datetime import date
from typing import Any, Literal

import pandas as pd

from src.config.ColumnNameConsts import ColumnNames as CN
from src.util.gspread import worksheet_values
from src.util.historical_cache import get_historical_prices
from src.util.yfinance import curr_price

SourceName = Literal["open_positions", "closed_positions"]

BUY_WORKSHEET = "Buy"
SELL_WORKSHEET = "Sell"
SOURCE_OPEN: SourceName = "open_positions"
SOURCE_CLOSED: SourceName = "closed_positions"

EXPECTED_COLUMNS = [
    "Date",
    "Brokerage",
    "Account",
    "Category",
    "Company",
    "Ticker",
    "Action",
    "Cost Basis Method",
    CN.QTY,
    CN.COST_PRICE,
    CN.TOTAL,
]

TRANSACTION_KEYS = [
    "date",
    "source",
    "brokerage",
    "account",
    "category",
    "company",
    "ticker",
    "action",
    "cost_basis_method",
    "qty",
    "price_per_share",
    "total",
    "row_number",
]


def load_buy_transactions() -> dict[str, Any]:
    return _load_tab(
        worksheet_name=os.getenv("BUY_WORKSHEET", BUY_WORKSHEET),
        worksheet_index=0,
        source=SOURCE_OPEN,
    )


def load_sell_transactions() -> dict[str, Any]:
    return _load_tab(
        worksheet_name=os.getenv("SELL_WORKSHEET", SELL_WORKSHEET),
        worksheet_index=None,
        source=SOURCE_CLOSED,
    )


def get_enriched_open_positions() -> dict[str, Any]:
    loaded = load_buy_transactions()
    warnings = list(loaded["warnings"])
    transactions = loaded["transactions"]
    buy_transactions = [tx for tx in transactions if tx["action"] == "Buy"]

    positions = []
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tx in buy_transactions:
        by_ticker[tx["ticker"]].append(tx)

    price_data, price_warnings = _load_current_prices(by_ticker)
    warnings.extend(price_warnings)

    tickers = sorted(by_ticker)
    try:
        historical_prices = get_historical_prices(tickers) if tickers else {}
    except Exception as exc:
        historical_prices = {}
        warnings.append(f"Historical price lookup failed: {exc}")

    for ticker in tickers:
        rows = by_ticker[ticker]
        qty = sum(tx["qty"] for tx in rows)
        total_cost_basis = sum(tx["total"] for tx in rows)
        average_cost = _divide(total_cost_basis, qty)

        current_price = price_data.get(ticker, {}).get("current_price")
        day_change_decimal = price_data.get(ticker, {}).get("day_change_decimal")

        if current_price is None:
            warnings.append(f"Current price unavailable for {ticker}.")
            day_change_pct = None
            day_change_value = None
            market_value = None
            gain = None
            gain_pct = None
        else:
            market_value = qty * current_price
            gain = market_value - total_cost_basis
            gain_pct = _pct(gain, total_cost_basis)
            day_change_pct = None if day_change_decimal is None else day_change_decimal * 100
            day_change_value = _day_change_value(market_value, day_change_decimal)

        position = {
            "ticker": ticker,
            "company": _representative_value(rows, "company"),
            "category": _representative_value(rows, "category"),
            "account": _representative_value(rows, "account"),
            "brokerage": _representative_value(rows, "brokerage"),
            "qty": _json_number(qty),
            "current_price": _json_number(current_price),
            "day_change_pct": _json_number(day_change_pct),
            "day_change_value": _json_number(day_change_value),
            "average_cost": _json_number(average_cost),
            "total_cost_basis": _json_number(total_cost_basis),
            "market_value": _json_number(market_value),
            "gain": _json_number(gain),
            "gain_pct": _json_number(gain_pct),
            "change_7d_pct": _historical_change(current_price, historical_prices, ticker, "7D"),
            "change_1m_pct": _historical_change(current_price, historical_prices, ticker, "1M"),
            "change_3m_pct": _historical_change(current_price, historical_prices, ticker, "3M"),
            "change_6m_pct": _historical_change(current_price, historical_prices, ticker, "6M"),
            "change_1y_pct": _historical_change(current_price, historical_prices, ticker, "1Y"),
            "transaction_count": len(rows),
            "first_buy_date": _min_date(rows),
            "last_buy_date": _max_date(rows),
        }
        positions.append(position)

    positions.sort(key=lambda pos: (pos["day_change_pct"] is None, -(pos["day_change_pct"] or 0)))
    return {
        "as_of": date.today().isoformat(),
        "source": "buy_tab",
        "positions": positions,
        "transaction_count": len(transactions),
        "warnings": _unique_warnings(warnings),
    }


def get_portfolio_snapshot(group_by: str = "ticker") -> dict[str, Any]:
    if group_by not in {"ticker", "category", "account", "brokerage"}:
        raise ValueError("group_by must be one of ticker, category, account, or brokerage")

    enriched = get_enriched_open_positions()
    positions = enriched["positions"]
    totals = _portfolio_totals(positions, enriched["transaction_count"])
    allocations = _allocations(positions, group_by)

    return {
        "as_of": enriched["as_of"],
        "source": "buy_tab",
        "totals": totals,
        "positions": positions,
        "allocations": allocations,
        "warnings": enriched["warnings"],
    }


def get_positions(
    ticker: str | None = None,
    category: str | None = None,
    account: str | None = None,
    brokerage: str | None = None,
) -> dict[str, Any]:
    enriched = get_enriched_open_positions()
    positions = [
        pos
        for pos in enriched["positions"]
        if _matches(pos["ticker"], ticker, ticker=True)
        and _matches(pos["category"], category)
        and _matches(pos["account"], account)
        and _matches(pos["brokerage"], brokerage)
    ]

    return {
        "as_of": enriched["as_of"],
        "source": "buy_tab",
        "positions": positions,
        "warnings": enriched["warnings"],
    }


def get_position_detail(
    ticker: str,
    include_closed_positions: bool = True,
    include_raw_transactions: bool = False,
    include_aggregate: bool = True,
) -> dict[str, Any]:
    normalized_ticker = _normalize_ticker(ticker)
    warnings: list[str] = []
    positions_result = get_positions(ticker=normalized_ticker)
    warnings.extend(positions_result["warnings"])
    open_position = positions_result["positions"][0] if positions_result["positions"] else None

    open_transactions_result = get_transactions(source=SOURCE_OPEN, ticker=normalized_ticker)
    warnings.extend(open_transactions_result["warnings"])

    closed_positions: list[dict[str, Any]] = []
    closed_transactions: list[dict[str, Any]] = []
    aggregate_realized_position = None

    if include_closed_positions or include_aggregate:
        realized_result = get_realized_positions(
            ticker=normalized_ticker,
            include_aggregate=include_aggregate,
        )
        warnings.extend(realized_result["warnings"])
        if include_closed_positions:
            closed_positions = realized_result["closed_positions"]
        aggregate_positions = realized_result.get("aggregate_realized_positions") or []
        if aggregate_positions:
            aggregate_realized_position = aggregate_positions[0]

    if include_raw_transactions:
        closed_transactions_result = get_transactions(source=SOURCE_CLOSED, ticker=normalized_ticker)
        warnings.extend(closed_transactions_result["warnings"])
        closed_transactions = closed_transactions_result["transactions"]

    return {
        "ticker": normalized_ticker,
        "open_position": open_position,
        "open_transactions": open_transactions_result["transactions"],
        "closed_positions": closed_positions,
        "closed_transactions": closed_transactions,
        "aggregate_realized_position": aggregate_realized_position,
        "warnings": _unique_warnings(warnings),
    }


def get_transactions(
    ticker: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    account: str | None = None,
    brokerage: str | None = None,
    category: str | None = None,
    source: Literal["open_positions", "closed_positions", "all"] = "all",
    action: Literal["Buy", "Sell", "all"] = "all",
    limit: int = 500,
) -> dict[str, Any]:
    if source not in {"open_positions", "closed_positions", "all"}:
        raise ValueError("source must be open_positions, closed_positions, or all")
    if action not in {"Buy", "Sell", "all"}:
        raise ValueError("action must be Buy, Sell, or all")

    warnings: list[str] = []
    transactions: list[dict[str, Any]] = []
    if source in {SOURCE_OPEN, "all"}:
        loaded = load_buy_transactions()
        warnings.extend(loaded["warnings"])
        transactions.extend(loaded["transactions"])
    if source in {SOURCE_CLOSED, "all"}:
        loaded = load_sell_transactions()
        warnings.extend(loaded["warnings"])
        transactions.extend(loaded["transactions"])

    start = _parse_filter_date(start_date, "start_date", warnings)
    end = _parse_filter_date(end_date, "end_date", warnings)
    normalized_ticker = _normalize_ticker(ticker) if ticker else None

    filtered = []
    for tx in transactions:
        tx_date = tx["date"]
        if normalized_ticker and tx["ticker"] != normalized_ticker:
            continue
        if action != "all" and tx["action"] != action:
            continue
        if not _matches(tx["account"], account):
            continue
        if not _matches(tx["brokerage"], brokerage):
            continue
        if not _matches(tx["category"], category):
            continue
        if start and (tx_date is None or tx_date < start):
            continue
        if end and (tx_date is None or tx_date > end):
            continue
        filtered.append(tx)

    filtered.sort(
        key=lambda tx: (
            tx["date"] is None,
            tx["date"] or "",
            tx["source"],
            tx["row_number"] or 0,
        )
    )

    safe_limit = max(1, min(int(limit or 500), 5000))
    truncated = len(filtered) > safe_limit
    limited = filtered[:safe_limit]

    return {
        "transactions": [_transaction_view(tx) for tx in limited],
        "result_count": len(limited),
        "truncated": truncated,
        "warnings": _unique_warnings(warnings),
    }


def get_realized_positions(
    ticker: str | None = None,
    include_aggregate: bool = True,
) -> dict[str, Any]:
    loaded = load_sell_transactions()
    warnings = list(loaded["warnings"])
    normalized_ticker = _normalize_ticker(ticker) if ticker else None
    transactions = sorted(loaded["transactions"], key=lambda tx: tx["row_number"] or 0)
    closed_positions, match_warnings = _closed_positions_from_sell_transactions(
        transactions,
        target_ticker=normalized_ticker,
    )
    warnings.extend(match_warnings)

    aggregate_realized_positions = (
        _aggregate_realized_positions(closed_positions) if include_aggregate else None
    )

    return {
        "source": "sell_tab",
        "closed_positions": closed_positions,
        "aggregate_realized_positions": aggregate_realized_positions,
        "warnings": _unique_warnings(warnings),
    }


def _closed_positions_from_sell_transactions(
    transactions: list[dict[str, Any]],
    target_ticker: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    closed_positions: list[dict[str, Any]] = []
    sequence_by_ticker: dict[str, int] = defaultdict(int)

    for index, tx in enumerate(transactions):
        if tx["action"] != "Sell":
            continue
        if target_ticker and tx["ticker"] != target_ticker:
            continue

        ticker = tx["ticker"]
        sequence_by_ticker[ticker] += 1
        qty_remaining = tx["qty"]
        qty_bought = 0.0
        cost_basis = 0.0
        consumed_lots: list[dict[str, Any]] = []
        buy_row_numbers: list[int] = []

        for candidate in transactions[index + 1 :]:
            if qty_remaining <= 0.000001:
                break
            if candidate["action"] == "Sell":
                break
            if candidate["ticker"] != ticker:
                continue

            available_qty = candidate["qty"]
            if available_qty <= 0:
                continue

            consumed_qty = min(available_qty, qty_remaining)
            lot_cost = candidate["total"] * consumed_qty / available_qty

            qty_remaining -= consumed_qty
            qty_bought += consumed_qty
            cost_basis += lot_cost
            consumed_lots.append(candidate)

            row_number = candidate.get("row_number")
            if row_number is not None and row_number not in buy_row_numbers:
                buy_row_numbers.append(row_number)

        is_quantity_matched = abs(qty_bought - tx["qty"]) < 0.000001
        if not is_quantity_matched:
            warnings.append(
                f"Sell tab row {tx.get('row_number')} for {ticker} sold {tx['qty']} shares "
                f"but only {qty_bought} following Buy shares were available before the next Sell row."
            )

        proceeds = tx["total"]
        realized_gain = proceeds - cost_basis
        closed_positions.append(
            {
                "closed_position_id": f"{ticker}-{tx.get('row_number') or sequence_by_ticker[ticker]}",
                "ticker": ticker,
                "company": tx.get("company") or _representative_value(consumed_lots, "company"),
                "category": tx.get("category") or _representative_value(consumed_lots, "category"),
                "close_date": tx.get("date"),
                "qty_bought": _json_number(qty_bought) or 0,
                "qty_sold": _json_number(tx["qty"]) or 0,
                "is_quantity_matched": is_quantity_matched,
                "cost_basis": _json_number(cost_basis) or 0,
                "proceeds": _json_number(proceeds) or 0,
                "average_cost": _json_number(_divide(cost_basis, qty_bought)),
                "sell_price": _json_number(tx["price_per_share"]),
                "average_sell_price": _json_number(_divide(proceeds, tx["qty"])),
                "realized_gain": _json_number(realized_gain) or 0,
                "realized_gain_pct": _json_number(_pct(realized_gain, cost_basis)),
                "first_buy_date": _min_date(consumed_lots),
                "buy_transaction_count": len(buy_row_numbers),
                "buy_row_numbers": buy_row_numbers,
                "sell_row_number": tx.get("row_number"),
            }
        )

    closed_positions.sort(
        key=lambda position: (
            position["close_date"] is None,
            position["close_date"] or "",
            position["sell_row_number"] or 0,
        )
    )
    return closed_positions, warnings


def _aggregate_realized_positions(
    closed_positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    row_sets: dict[str, set[int]] = defaultdict(set)

    for position in closed_positions:
        ticker = position["ticker"]
        if ticker not in grouped:
            grouped[ticker] = {
                "ticker": ticker,
                "company": position.get("company"),
                "category": position.get("category"),
                "qty_bought": 0.0,
                "qty_sold": 0.0,
                "is_quantity_matched": True,
                "cost_basis": 0.0,
                "proceeds": 0.0,
                "realized_gain": 0.0,
                "first_buy_date": None,
                "last_sell_date": None,
            }

        aggregate = grouped[ticker]
        aggregate["company"] = aggregate["company"] or position.get("company")
        aggregate["category"] = aggregate["category"] or position.get("category")
        aggregate["qty_bought"] += position["qty_bought"] or 0
        aggregate["qty_sold"] += position["qty_sold"] or 0
        aggregate["is_quantity_matched"] = (
            aggregate["is_quantity_matched"] and position["is_quantity_matched"]
        )
        aggregate["cost_basis"] += position["cost_basis"] or 0
        aggregate["proceeds"] += position["proceeds"] or 0
        aggregate["realized_gain"] += position["realized_gain"] or 0
        aggregate["first_buy_date"] = _earliest(
            aggregate["first_buy_date"],
            position.get("first_buy_date"),
        )
        aggregate["last_sell_date"] = _latest(
            aggregate["last_sell_date"],
            position.get("close_date"),
        )

        for row_number in position.get("buy_row_numbers", []):
            row_sets[ticker].add(row_number)
        if position.get("sell_row_number") is not None:
            row_sets[ticker].add(position["sell_row_number"])

    aggregates = []
    for ticker in sorted(grouped):
        aggregate = grouped[ticker]
        cost_basis = aggregate["cost_basis"]
        aggregates.append(
            {
                "ticker": aggregate["ticker"],
                "company": aggregate["company"],
                "category": aggregate["category"],
                "qty_bought": _json_number(aggregate["qty_bought"]) or 0,
                "qty_sold": _json_number(aggregate["qty_sold"]) or 0,
                "is_quantity_matched": aggregate["is_quantity_matched"],
                "cost_basis": _json_number(cost_basis) or 0,
                "proceeds": _json_number(aggregate["proceeds"]) or 0,
                "realized_gain": _json_number(aggregate["realized_gain"]) or 0,
                "realized_gain_pct": _json_number(_pct(aggregate["realized_gain"], cost_basis)),
                "first_buy_date": aggregate["first_buy_date"],
                "last_sell_date": aggregate["last_sell_date"],
                "transaction_count": len(row_sets[ticker]),
            }
        )

    return aggregates


def _load_tab(
    worksheet_name: str,
    worksheet_index: int | None,
    source: SourceName,
) -> dict[str, Any]:
    warnings: list[str] = []
    try:
        values = worksheet_values(
            worksheet_name=worksheet_name,
            worksheet_index=worksheet_index,
        )
    except Exception as exc:
        return {
            "transactions": [],
            "warnings": [f"Unable to read {worksheet_name} worksheet: {exc}"],
        }

    if not values:
        return {
            "transactions": [],
            "warnings": [f"{worksheet_name} worksheet is empty."],
        }

    headers = [_clean_header(header) for header in values[0]]
    if "Price per share" in headers and CN.COST_PRICE not in headers:
        headers = [CN.COST_PRICE if header == "Price per share" else header for header in headers]

    rows = []
    for offset, row in enumerate(values[1:], start=2):
        padded = row + [""] * max(0, len(headers) - len(row))
        rows.append(dict(zip(headers, padded, strict=False)) | {"row_number": offset})

    present = set(headers)
    for column in EXPECTED_COLUMNS:
        if column not in present:
            warnings.append(f"{worksheet_name} worksheet is missing column '{column}'.")

    transactions = []
    for raw in rows:
        tx = _normalize_transaction(raw, source, worksheet_name, warnings)
        if tx:
            transactions.append(tx)

    return {
        "transactions": transactions,
        "warnings": _unique_warnings(warnings),
    }


def _normalize_transaction(
    raw: dict[str, Any],
    source: SourceName,
    worksheet_name: str,
    warnings: list[str],
) -> dict[str, Any] | None:
    row_number = raw.get("row_number")
    ticker = _normalize_ticker(raw.get(CN.TICKER))
    if not ticker:
        warnings.append(f"{worksheet_name} row {row_number} has a blank ticker and was skipped.")
        return None

    action = _clean_string(raw.get("Action"))
    if not action and source == SOURCE_OPEN:
        action = "Buy"
    elif action:
        action = action.strip().title()

    if action not in {"Buy", "Sell"}:
        warnings.append(
            f"{worksheet_name} row {row_number} has unsupported action '{raw.get('Action')}' and was skipped."
        )
        return None

    date_value = _normalize_date(raw.get("Date"), worksheet_name, row_number, warnings)
    qty = _normalize_number(raw.get(CN.QTY), CN.QTY, worksheet_name, row_number, warnings)
    price = _normalize_number(
        raw.get(CN.COST_PRICE),
        CN.COST_PRICE,
        worksheet_name,
        row_number,
        warnings,
    )
    total = _normalize_number(raw.get(CN.TOTAL), CN.TOTAL, worksheet_name, row_number, warnings)

    if price == 0 and qty:
        price = _divide(total, qty) or 0
    if total == 0 and qty and price:
        total = qty * price

    return {
        "date": date_value,
        "source": source,
        "brokerage": _clean_string(raw.get("Brokerage")),
        "account": _clean_string(raw.get("Account")),
        "category": _clean_string(raw.get("Category")),
        "company": _clean_string(raw.get(CN.NAME)),
        "ticker": ticker,
        "action": action,
        "cost_basis_method": _clean_string(raw.get("Cost Basis Method")),
        "qty": _json_number(qty) or 0,
        "price_per_share": _json_number(price) or 0,
        "total": _json_number(total) or 0,
        "row_number": row_number,
    }


def _load_current_prices(by_ticker: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    price_data: dict[str, Any] = {}
    stock_tickers = []
    crypto_tickers = []
    for ticker, rows in by_ticker.items():
        if _representative_value(rows, "category") == "Cryptocurrency":
            crypto_tickers.append(ticker)
        else:
            stock_tickers.append(ticker)

    for tickers, crypto in [(stock_tickers, False), (crypto_tickers, True)]:
        if not tickers:
            continue
        try:
            prices = curr_price(tickers, crypto=crypto)
        except Exception as exc:
            warnings.append(f"Current price lookup failed for {', '.join(tickers)}: {exc}")
            continue

        if prices is None or prices.empty:
            warnings.append(f"Current price lookup returned no data for {', '.join(tickers)}.")
            continue

        for ticker in tickers:
            if ticker not in prices.index:
                continue
            current_price = _json_number(prices.loc[ticker].get(CN.PRICE))
            day_change = _json_number(prices.loc[ticker].get(CN.DAY_CHNG))
            if current_price is None or current_price <= 0:
                continue
            price_data[ticker] = {
                "current_price": current_price,
                "day_change_decimal": day_change,
            }

    return price_data, warnings


def _portfolio_totals(positions: list[dict[str, Any]], transaction_count: int) -> dict[str, Any]:
    total_cost_basis = sum(pos["total_cost_basis"] or 0 for pos in positions)
    priced_cost_basis = sum(
        pos["total_cost_basis"] or 0 for pos in positions if pos["market_value"] is not None
    )
    market_value = sum(pos["market_value"] or 0 for pos in positions)
    gain = sum(pos["gain"] or 0 for pos in positions)
    day_change_value = sum(pos["day_change_value"] or 0 for pos in positions)
    previous_market_value = market_value - day_change_value

    return {
        "total_cost_basis": _json_number(total_cost_basis),
        "market_value": _json_number(market_value),
        "gain": _json_number(gain),
        "gain_pct": _json_number(_pct(gain, priced_cost_basis)),
        "day_change_pct": _json_number(_pct(day_change_value, previous_market_value)),
        "day_change_value": _json_number(day_change_value),
        "position_count": len(positions),
        "transaction_count": transaction_count,
    }


def _allocations(positions: list[dict[str, Any]], group_by: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    total_market_value = sum(pos["market_value"] or 0 for pos in positions)

    for pos in positions:
        key = pos["ticker"] if group_by == "ticker" else pos.get(group_by) or "Unspecified"
        if key not in grouped:
            grouped[key] = {
                "key": key,
                "total_cost_basis": 0.0,
                "market_value": 0.0,
                "position_count": 0,
            }
        grouped[key]["total_cost_basis"] += pos["total_cost_basis"] or 0
        grouped[key]["market_value"] += pos["market_value"] or 0
        grouped[key]["position_count"] += 1

    allocations = []
    for item in grouped.values():
        market_value = item["market_value"]
        allocations.append(
            {
                "key": item["key"],
                "total_cost_basis": _json_number(item["total_cost_basis"]),
                "market_value": _json_number(market_value),
                "allocation_pct": _json_number(_pct(market_value, total_market_value)),
                "position_count": item["position_count"],
            }
        )

    allocations.sort(key=lambda item: item["market_value"], reverse=True)
    return allocations


def _transaction_view(tx: dict[str, Any]) -> dict[str, Any]:
    return {key: tx.get(key) for key in TRANSACTION_KEYS}


def _historical_change(
    current_price: float | None,
    historical_prices: dict[str, dict[str, float]],
    ticker: str,
    period: str,
) -> float | None:
    historical_price = historical_prices.get(ticker, {}).get(period)
    if current_price is None or not historical_price:
        return None
    return _json_number(_pct(current_price - historical_price, historical_price))


def _day_change_value(market_value: float, day_change_decimal: float | None) -> float | None:
    if day_change_decimal is None or day_change_decimal == -1:
        return None
    return _json_number(market_value * day_change_decimal / (1 + day_change_decimal))


def _representative_value(rows: list[dict[str, Any]], key: str) -> str | None:
    values = [row.get(key) for row in rows if row.get(key)]
    if not values:
        return None

    counts = Counter(values)
    max_count = max(counts.values())
    candidates = {value for value, count in counts.items() if count == max_count}
    for row in sorted(rows, key=_row_sort_key, reverse=True):
        value = row.get(key)
        if value in candidates:
            return value
    return values[-1]


def _min_date(rows: list[dict[str, Any]]) -> str | None:
    dates = [row["date"] for row in rows if row.get("date")]
    return min(dates) if dates else None


def _max_date(rows: list[dict[str, Any]]) -> str | None:
    dates = [row["date"] for row in rows if row.get("date")]
    return max(dates) if dates else None


def _row_sort_key(row: dict[str, Any]) -> tuple[str, int]:
    return (row.get("date") or "", row.get("row_number") or 0)


def _earliest(first: str | None, second: str | None) -> str | None:
    dates = [value for value in [first, second] if value]
    return min(dates) if dates else None


def _latest(first: str | None, second: str | None) -> str | None:
    dates = [value for value in [first, second] if value]
    return max(dates) if dates else None


def _matches(value: str | None, filter_value: str | None, ticker: bool = False) -> bool:
    if filter_value is None or filter_value == "":
        return True
    if ticker:
        return (value or "").upper() == _normalize_ticker(filter_value)
    return (value or "").casefold() == str(filter_value).strip().casefold()


def _parse_filter_date(value: str | None, field_name: str, warnings: list[str]) -> str | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        warnings.append(f"Ignoring invalid {field_name}: {value}.")
        return None
    return parsed.date().isoformat()


def _normalize_date(
    value: Any,
    worksheet_name: str,
    row_number: int | None,
    warnings: list[str],
) -> str | None:
    if _is_blank(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        warnings.append(f"{worksheet_name} row {row_number} has an invalid date: {value}.")
        return None
    return parsed.date().isoformat()


def _normalize_number(
    value: Any,
    column: str,
    worksheet_name: str,
    row_number: int | None,
    warnings: list[str],
) -> float:
    if _is_blank(value):
        warnings.append(f"{worksheet_name} row {row_number} has a blank {column}; using 0.")
        return 0.0
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    parsed = pd.to_numeric(cleaned, errors="coerce")
    if pd.isna(parsed):
        warnings.append(f"{worksheet_name} row {row_number} has invalid {column}: {value}; using 0.")
        return 0.0
    return float(parsed)


def _normalize_ticker(value: Any) -> str:
    cleaned = _clean_string(value)
    return cleaned.upper() if cleaned else ""


def _clean_header(value: Any) -> str:
    return str(value or "").strip()


def _clean_string(value: Any) -> str | None:
    if _is_blank(value):
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ""


def _divide(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or not denominator:
        return None
    return 100 * numerator / denominator


def _json_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def _unique_warnings(warnings: list[str]) -> list[str]:
    return list(dict.fromkeys(warning for warning in warnings if warning))
