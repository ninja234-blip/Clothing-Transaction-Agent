"""Expose the shopping tools as an MCP server (pip install mcp).
Run:  python -m clothing_agent.mcp_server
Then point any MCP client (Claude Desktop, ADK's MCPToolset, ...) at it over stdio."""
from mcp.server.fastmcp import FastMCP
from . import tools

mcp = FastMCP("clothing-store")
for fn in (tools.search_products, tools.get_recommendations, tools.add_to_cart, tools.view_cart,
           tools.check_transaction_safety, tools.create_checkout, tools.confirm_payment):
    mcp.tool()(fn)

if __name__ == "__main__":
    mcp.run()
