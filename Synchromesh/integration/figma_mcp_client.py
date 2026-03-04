import json
import os
from typing import Any, Dict, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class FigmaMCPClient:
    """
    MCP client wrapper for Figma.

    Public methods used by orchestrator:
      - get_tokens(figma_file_id) -> Dict[token_name, token_value]
    """

    def __init__(self, server_path: str = "npx"):
        token = os.getenv("FIGMA_ACCESS_TOKEN") or os.getenv("FIGMA_API_KEY")
        if not token:
            raise RuntimeError(
                "Missing FIGMA_ACCESS_TOKEN (or FIGMA_API_KEY) in environment. "
                "Do not hardcode secrets in code."
            )

        self.server_params = StdioServerParameters(
            command=server_path,
            args=["-y", "@modelcontextprotocol/server-figma"],
            env={"FIGMA_ACCESS_TOKEN": token},
        )

    async def get_tokens(self, file_key: str) -> Dict[str, Any]:
        raw = await self._call_tokens_tool(file_key=file_key)
        return self.normalize_tokens(raw)

    async def _call_tokens_tool(self, file_key: str) -> Any:
        """
        Calls whichever token tool exists on the MCP Figma server.
        Tool names can vary by server version; we discover tools first.
        """
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools] if hasattr(tools, "tools") else []

                # Try likely tool names in order
                candidates = [
                    "get_file_tokens",
                    "get_design_tokens",
                    "get_tokens",
                    "get_file_design_tokens",
                ]

                selected = None
                for c in candidates:
                    if c in tool_names:
                        selected = c
                        break

                if not selected:
                    raise RuntimeError(
                        f"Figma MCP server is running but no known token tool found. "
                        f"Available tools: {tool_names}"
                    )

                result = await session.call_tool(selected, {"file_key": file_key})

                # result.content usually contains one text payload
                if getattr(result, "content", None):
                    # Many MCP servers return a text JSON blob
                    return result.content[0].text
                return {}

    def normalize_tokens(self, raw_data: Any) -> Dict[str, Any]:
        """
        Normalizes MCP output into a token map:
          { token_name: token_value }

        Supports:
          - raw_data as JSON string
          - raw_data as dict
        """
        if raw_data is None:
            return {}

        if isinstance(raw_data, str):
            raw_data = raw_data.strip()
            if not raw_data:
                return {}
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                # If not JSON, we can't parse reliably
                return {}

        if not isinstance(raw_data, dict):
            return {}

        # Handle common shapes:
        # 1) {"tokens": [{"name": "...", "value": "..."}]}
        # 2) {"tokens": {"color.primary": "#fff", ...}}
        # 3) nested dict categories
        tokens: Dict[str, Any] = {}

        if "tokens" in raw_data:
            t = raw_data["tokens"]
            if isinstance(t, list):
                for item in t:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        tokens[str(item["name"])] = item["value"]
                return tokens
            if isinstance(t, dict):
                # could already be a map
                for k, v in t.items():
                    tokens[str(k)] = v
                return tokens

        # fallback: treat entire dict as token map/nested map
        def walk(prefix: str, obj: Any):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    walk(f"{prefix}{k}." if prefix else f"{k}.", v)
            else:
                name = prefix[:-1] if prefix.endswith(".") else prefix
                tokens[name] = obj

        walk("", raw_data)
        return tokens