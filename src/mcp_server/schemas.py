from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EnrichedPosition(StrictModel):
    ticker: str
    company: str | None
    category: str | None
    account: str | None
    brokerage: str | None
    qty: float
    current_price: float | None
    day_change_pct: float | None
    day_change_value: float | None
    average_cost: float | None
    total_cost_basis: float
    market_value: float | None
    gain: float | None
    gain_pct: float | None
    change_7d_pct: float | None
    change_1m_pct: float | None
    change_3m_pct: float | None
    change_6m_pct: float | None
    change_1y_pct: float | None
    transaction_count: int
    first_buy_date: str | None
    last_buy_date: str | None


class PortfolioTotals(StrictModel):
    total_cost_basis: float
    market_value: float
    gain: float
    gain_pct: float | None
    day_change_pct: float | None
    day_change_value: float
    position_count: int
    transaction_count: int


class Allocation(StrictModel):
    key: str
    total_cost_basis: float
    market_value: float
    allocation_pct: float | None
    position_count: int


class PortfolioSnapshotResponse(StrictModel):
    as_of: str
    source: Literal["buy_tab"]
    totals: PortfolioTotals
    positions: list[EnrichedPosition]
    allocations: list[Allocation]
    warnings: list[str] = Field(default_factory=list)


class PositionsResponse(StrictModel):
    as_of: str
    source: Literal["buy_tab"]
    positions: list[EnrichedPosition]
    warnings: list[str] = Field(default_factory=list)


class Transaction(StrictModel):
    date: str | None
    source: Literal["open_positions", "closed_positions"]
    brokerage: str | None
    account: str | None
    category: str | None
    company: str | None
    ticker: str
    action: Literal["Buy", "Sell"]
    cost_basis_method: str | None
    qty: float
    price_per_share: float
    total: float
    row_number: int | None


class TransactionsResponse(StrictModel):
    transactions: list[Transaction]
    result_count: int
    truncated: bool
    warnings: list[str] = Field(default_factory=list)


class RealizedPosition(StrictModel):
    ticker: str
    company: str | None
    category: str | None
    qty_bought: float
    qty_sold: float
    is_quantity_matched: bool
    cost_basis: float
    proceeds: float
    realized_gain: float
    realized_gain_pct: float | None
    first_buy_date: str | None
    last_sell_date: str | None
    transaction_count: int


class ClosedPosition(StrictModel):
    closed_position_id: str
    ticker: str
    company: str | None
    category: str | None
    close_date: str | None
    qty_bought: float
    qty_sold: float
    is_quantity_matched: bool
    cost_basis: float
    proceeds: float
    average_cost: float | None
    sell_price: float | None
    average_sell_price: float | None
    realized_gain: float
    realized_gain_pct: float | None
    first_buy_date: str | None
    buy_transaction_count: int
    buy_row_numbers: list[int]
    sell_row_number: int | None


class RealizedPositionsResponse(StrictModel):
    source: Literal["sell_tab"]
    closed_positions: list[ClosedPosition]
    aggregate_realized_positions: list[RealizedPosition] | None
    warnings: list[str] = Field(default_factory=list)


class PositionDetailResponse(StrictModel):
    ticker: str
    open_position: EnrichedPosition | None
    open_transactions: list[Transaction]
    closed_positions: list[ClosedPosition]
    closed_transactions: list[Transaction]
    aggregate_realized_position: RealizedPosition | None
    warnings: list[str] = Field(default_factory=list)
