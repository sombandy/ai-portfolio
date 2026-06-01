from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Literal

Transport = Literal["stdio", "sse", "streamable-http"]


@dataclass(frozen=True)
class PortfolioMcpConfig:
    transport: Transport = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/mcp"
    auth_token: str | None = None


def load_config() -> PortfolioMcpConfig:
    transport = os.getenv("PORTFOLIO_MCP_TRANSPORT", "stdio")
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise ValueError("PORTFOLIO_MCP_TRANSPORT must be stdio, sse, or streamable-http")

    return PortfolioMcpConfig(
        transport=transport,
        host=os.getenv("PORTFOLIO_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("PORTFOLIO_MCP_PORT", "8000")),
        path=os.getenv("PORTFOLIO_MCP_PATH", "/mcp"),
        auth_token=os.getenv("PORTFOLIO_MCP_AUTH_TOKEN"),
    )


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
