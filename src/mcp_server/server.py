from __future__ import annotations

import hmac
import json
from typing import Literal

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from src import portfolio_data
from src.mcp_server.config import PortfolioMcpConfig, load_config
from src.mcp_server.schemas import (
    ClosedPosition,
    EnrichedPosition,
    PortfolioSnapshotResponse,
    PositionDetailResponse,
    PositionsResponse,
    RealizedPositionsResponse,
    Transaction,
    TransactionsResponse,
)


class StaticTokenVerifier:
    def __init__(self, token: str):
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token, self._token):
            return None
        return AccessToken(
            token=token,
            client_id="portfolio-mcp",
            scopes=["portfolio:read"],
        )


def create_server(config: PortfolioMcpConfig | None = None) -> FastMCP:
    config = config or load_config()
    auth_settings = None
    token_verifier = None
    if config.transport == "streamable-http":
        if not config.auth_token:
            raise ValueError("PORTFOLIO_MCP_AUTH_TOKEN is required for streamable-http")
        base_url = f"http://{config.host}:{config.port}"
        auth_settings = AuthSettings(
            issuer_url=base_url,
            resource_server_url=base_url,
            required_scopes=["portfolio:read"],
        )
        token_verifier = StaticTokenVerifier(config.auth_token)

    mcp = FastMCP(
        "portfolio",
        instructions=(
            "Read-only access to the owner's portfolio holdings, transaction "
            "history, and realized-position summaries."
        ),
        host=config.host,
        port=config.port,
        streamable_http_path=config.path,
        log_level="ERROR",
        auth=auth_settings,
        token_verifier=token_verifier,
    )

    @mcp.tool()
    def get_portfolio_snapshot(
        group_by: Literal["ticker", "category", "account", "brokerage"] = "ticker",
    ) -> dict:
        """Return a dashboard-equivalent current portfolio summary."""

        response = PortfolioSnapshotResponse.model_validate(
            portfolio_data.get_portfolio_snapshot(group_by=group_by)
        )
        return response.model_dump(mode="json")

    @mcp.tool()
    def get_positions(
        ticker: str | None = None,
        category: str | None = None,
        account: str | None = None,
        brokerage: str | None = None,
    ) -> dict:
        """Return enriched current/open positions, optionally filtered."""

        response = PositionsResponse.model_validate(
            portfolio_data.get_positions(
                ticker=ticker,
                category=category,
                account=account,
                brokerage=brokerage,
            )
        )
        return response.model_dump(mode="json")

    @mcp.tool()
    def get_position_detail(
        ticker: str,
        include_closed_positions: bool = True,
        include_raw_transactions: bool = False,
        include_aggregate: bool = True,
    ) -> dict:
        """Return current position context and summarized closed history for one ticker."""

        response = PositionDetailResponse.model_validate(
            portfolio_data.get_position_detail(
                ticker=ticker,
                include_closed_positions=include_closed_positions,
                include_raw_transactions=include_raw_transactions,
                include_aggregate=include_aggregate,
            )
        )
        return response.model_dump(mode="json")

    @mcp.tool()
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
    ) -> dict:
        """Return normalized raw transactions from the Buy tab, Sell tab, or both."""

        response = TransactionsResponse.model_validate(
            portfolio_data.get_transactions(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                account=account,
                brokerage=brokerage,
                category=category,
                source=source,
                action=action,
                limit=limit,
            )
        )
        return response.model_dump(mode="json")

    @mcp.tool()
    def get_realized_positions(
        ticker: str | None = None,
        include_aggregate: bool = True,
    ) -> dict:
        """Return one closed-position summary per Sell row from the Sell tab."""

        response = RealizedPositionsResponse.model_validate(
            portfolio_data.get_realized_positions(
                ticker=ticker,
                include_aggregate=include_aggregate,
            )
        )
        return response.model_dump(mode="json")

    @mcp.resource("portfolio://schema/transactions")
    def transactions_schema() -> str:
        """Return the JSON schema for normalized transaction rows."""

        return json.dumps(Transaction.model_json_schema(), indent=2)

    @mcp.resource("portfolio://schema/positions")
    def positions_schema() -> str:
        """Return the JSON schema for enriched current positions."""

        return json.dumps(EnrichedPosition.model_json_schema(), indent=2)

    @mcp.resource("portfolio://schema/closed_positions")
    def closed_positions_schema() -> str:
        """Return the JSON schema for closed-position/disposal summaries."""

        return json.dumps(ClosedPosition.model_json_schema(), indent=2)

    return mcp


def run_server() -> None:
    config = load_config()
    server = create_server(config)
    server.run(config.transport)
