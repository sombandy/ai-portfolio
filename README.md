## Portfolio MCP server

Run the local stdio MCP server:

```bash
uv run python -m src.mcp_server
```

Required environment:

```text
TRANSACTIONS_SHEET=your-google-sheet-id
BUY_WORKSHEET=Buy
SELL_WORKSHEET=Sell
```

Claude Desktop / Claude Code config shape:

```json
{
  "mcpServers": {
    "portfolio": {
      "command": "/Users/somnath/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/somnath/code-projects/ai-portfolio",
        "run",
        "python",
        "-m",
        "src.mcp_server"
      ],
      "env": {
        "TRANSACTIONS_SHEET": "your-google-sheet-id"
      }
    }
  }
}
```

Use `uv --directory` instead of relying on `cwd`; some desktop MCP launchers do
not apply `cwd` before Python resolves local modules.

## ChatGPT setup

ChatGPT cannot launch this local `stdio` server directly. It needs a remote MCP
URL over HTTPS. For quick personal testing, run the server locally with the SSE
transport and expose it through a temporary HTTPS tunnel.

Start the local MCP server:

```bash
PORTFOLIO_MCP_TRANSPORT=sse \
PORTFOLIO_MCP_HOST=127.0.0.1 \
PORTFOLIO_MCP_PORT=8000 \
uv run python -m src.mcp_server
```

The local endpoint is:

```text
http://127.0.0.1:8000/sse
```

Expose it with a tunnel, for example ngrok:

```bash
ngrok http http://127.0.0.1:8000
```

If ngrok gives you:

```text
https://abc123.ngrok-free.app
```

then the ChatGPT MCP URL is:

```text
https://abc123.ngrok-free.app/sse
```

In ChatGPT web:

1. Enable developer mode for MCP/custom apps in workspace or app settings.
2. Create a custom app / MCP connector.
3. Use the public tunnel URL ending in `/sse`.
4. Choose SSE as the protocol.
5. Use no authentication for short local testing only.
6. Scan tools and verify these tools are discovered:
   - `get_portfolio_snapshot`
   - `get_positions`
   - `get_position_detail`
   - `get_transactions`
   - `get_realized_positions`

Example prompt:

```text
Use my portfolio app. Call get_portfolio_snapshot and summarize my current holdings by category.
```

Stop the tunnel when testing is complete. No-auth tunnel testing exposes portfolio
data to anyone with the tunnel URL.

For longer-term ChatGPT usage, deploy the MCP server behind HTTPS with proper
OAuth-compatible authentication. The `streamable-http` endpoint is `/mcp`:

```bash
PORTFOLIO_MCP_TRANSPORT=streamable-http \
PORTFOLIO_MCP_HOST=127.0.0.1 \
PORTFOLIO_MCP_PORT=8000 \
PORTFOLIO_MCP_PATH=/mcp \
PORTFOLIO_MCP_AUTH_TOKEN=local-test-token \
uv run python -m src.mcp_server
```

The current `streamable-http` mode uses a static bearer token, which is useful
for local/API testing but is not the right final auth model for a published
ChatGPT app.
