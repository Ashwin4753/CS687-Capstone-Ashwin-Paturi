import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class FigmaMCPClient:
    def __init__(self, server_path: str = "npx"):
        # Parameters to run the Figma MCP server (standardized node package)
        self.server_params = StdioServerParameters(
            command=server_path,
            args=["-y", "@modelcontextprotocol/server-figma"],
            env={"FIGMA_ACCESS_TOKEN": "YOUR_FIGMA_TOKEN"}
        )

    async def fetch_design_tokens(self, file_key: str):
        """
        Calls the 'get_file_tokens' tool from the Figma MCP server.
        This provides the 'Source of Truth' for the Stylist Agent.
        """
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List available tools on the Figma server
                tools = await session.list_tools()
                
                # Execute the specific tool to get tokens
                result = await session.call_tool("get_file_tokens", {"file_key": file_key})
                return result.content[0].text if result.content else {}

    def normalize_tokens(self, raw_data: str):
        """Converts raw MCP output into a {hex: token_name} mapping."""
        # Logic to parse Figma JSON into a flat map for the agents
        return {"#3b82f6": "var(--primary-blue)", "#ffffff": "var(--white)"}