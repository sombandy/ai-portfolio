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
URL over HTTPS using streamable HTTP. For quick personal testing, run the server
locally and expose it through a temporary ngrok tunnel.

This endpoint returns private portfolio data without authenticating callers. Do
not share the ngrok URL, and stop ngrok as soon as testing is complete.

### 1. Start the local MCP server

```bash
TRANSACTIONS_SHEET=your-google-sheet-id \
PORTFOLIO_MCP_TRANSPORT=streamable-http \
uv run python -m src.mcp_server
```

The local endpoint is:

```text
http://127.0.0.1:8000/mcp
```

The HTTP defaults are `127.0.0.1:8000`, path `/mcp`, and no authentication.
Setting `PORTFOLIO_MCP_AUTH_TOKEN` enables the optional static bearer-token
mode for non-ChatGPT testing.

### 2. Expose it through ngrok

```bash
ngrok http 8000 --host-header=rewrite --inspect=false
```

`--host-header=rewrite` presents the request to FastMCP as local traffic, so its
DNS-rebinding protection remains enabled without configuring every temporary
ngrok hostname in the application.

### 3. Verify the local and ngrok endpoints

Launch MCP Inspector:

```bash
npx @modelcontextprotocol/inspector@latest
```

In the Inspector UI, select **Streamable HTTP**, enter
`http://127.0.0.1:8000/mcp`, connect, list the tools, and call one of them.

Then repeat the check with the public URL.

If ngrok gives you:

```text
https://abc123.ngrok-free.app
```

then the ChatGPT MCP URL is:

```text
https://abc123.ngrok-free.app/mcp
```

The randomly assigned ngrok URL may change when ngrok restarts. If it changes,
edit or recreate the ChatGPT app connection.

### 4. Connect it to ChatGPT

In ChatGPT web:

1. Open **Settings → Apps → Advanced settings** and enable **Developer mode**.
   Workspace policy and account plan can affect whether this setting is shown.
2. Open **Settings → Apps → Create**. In managed workspaces, an admin may need
   to create or allow the app from workspace settings.
3. Enter a name such as `My Portfolio` and the public ngrok URL ending in
   `/mcp`.
4. Choose **No authentication**, then scan tools.
5. Verify these tools are discovered:
   - `get_portfolio_snapshot`
   - `get_positions`
   - `get_position_detail`
   - `get_transactions`
   - `get_realized_positions`
6. Create a new chat, enable `My Portfolio` from the tools/apps menu, and test a
   prompt.

Example prompt:

```text
Use my portfolio app. Call get_portfolio_snapshot and summarize my current holdings by category.
```

Stop the tunnel when testing is complete. No-auth tunnel testing exposes portfolio
data to anyone with the tunnel URL.

For longer-term ChatGPT usage, deploy the MCP server behind HTTPS with proper
OAuth-compatible authentication. The current static bearer-token mode remains
available for non-ChatGPT API testing:

```bash
PORTFOLIO_MCP_TRANSPORT=streamable-http \
PORTFOLIO_MCP_HOST=127.0.0.1 \
PORTFOLIO_MCP_PORT=8000 \
PORTFOLIO_MCP_PATH=/mcp \
PORTFOLIO_MCP_AUTH_TOKEN=local-test-token \
uv run python -m src.mcp_server
```

ChatGPT does not send arbitrary custom API keys to MCP servers. A persistent
ChatGPT deployment should replace anonymous access with the MCP OAuth 2.1 flow;
the static token is not the final authentication model.
