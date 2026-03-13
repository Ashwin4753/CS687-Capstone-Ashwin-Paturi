import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class FigmaMCPClient:
    """
    MCP client wrapper for Figma.

    Public methods used by orchestrator:
      - get_tokens(figma_file_id) -> Dict[token_name, token_value]
      - list_available_tools() -> List[str]
      - health_check() -> bool
    """

    def __init__(self, server_path: str = "npx", timeout_seconds: int = 15):
        token = os.getenv("FIGMA_ACCESS_TOKEN") or os.getenv("FIGMA_API_KEY")
        if not token:
            raise RuntimeError(
                "Missing FIGMA_ACCESS_TOKEN (or FIGMA_API_KEY) in environment. "
                "Do not hardcode secrets in code."
            )

        self.timeout_seconds = timeout_seconds
        self.server_params = StdioServerParameters(
            command=server_path,
            args=["-y", "@modelcontextprotocol/server-figma"],
            env={"FIGMA_ACCESS_TOKEN": token},
        )

    async def get_tokens(self, file_key: str) -> Dict[str, Any]:
        if not file_key or not str(file_key).strip():
            raise ValueError("file_key must be a non-empty string.")

        raw = await self._call_tokens_tool(file_key=str(file_key).strip())
        return self.normalize_tokens(raw)

    async def list_available_tools(self) -> List[str]:
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=self.timeout_seconds)
                    tools = await asyncio.wait_for(session.list_tools(), timeout=self.timeout_seconds)
                    if hasattr(tools, "tools"):
                        return [t.name for t in tools.tools]
                    return []
        except Exception as e:
            raise RuntimeError(f"Figma MCP tool listing failed: {e}") from e

    async def health_check(self) -> bool:
        """
        Best-effort MCP connectivity check.
        Returns True if tools can be listed successfully.
        """
        try:
            tools = await self.list_available_tools()
            return len(tools) > 0
        except Exception:
            return False

    async def _call_tokens_tool(self, file_key: str) -> Any:
        """
        Calls whichever token tool exists on the MCP Figma server.
        Tool names can vary by server version; we discover tools first.
        Also tries multiple possible parameter names.
        """
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=self.timeout_seconds)

                    tools = await asyncio.wait_for(session.list_tools(), timeout=self.timeout_seconds)
                    tool_names = [t.name for t in tools.tools] if hasattr(tools, "tools") else []

                    candidates = [
                        "get_file_tokens",
                        "get_design_tokens",
                        "get_tokens",
                        "get_file_design_tokens",
                    ]

                    selected: Optional[str] = None
                    for candidate in candidates:
                        if candidate in tool_names:
                            selected = candidate
                            break

                    if not selected:
                        raise RuntimeError(
                            "Figma MCP server is running but no known token tool was found. "
                            f"Available tools: {tool_names}"
                        )

                    payload_candidates = [
                        {"file_key": file_key},
                        {"fileKey": file_key},
                        {"file_id": file_key},
                        {"fileId": file_key},
                    ]

                    last_error = None
                    for payload in payload_candidates:
                        try:
                            result = await asyncio.wait_for(
                                session.call_tool(selected, payload),
                                timeout=self.timeout_seconds,
                            )
                            return self._extract_content(result)
                        except Exception as e:
                            last_error = e

                    raise RuntimeError(
                        f"Unable to call Figma MCP tool '{selected}' with known payload formats."
                    ) from last_error
        except Exception as e:
            raise RuntimeError(
                f"Figma MCP token fetch failed for file '{file_key}'. "
                "Check token validity, MCP server compatibility, and tool availability."
            ) from e

    @staticmethod
    def _extract_content(result: Any) -> Any:
        """
        Safely extracts text/data from MCP tool result.
        """
        if result is None:
            return {}

        content = getattr(result, "content", None)
        if not content:
            return {}

        extracted: List[Any] = []

        for item in content:
            if hasattr(item, "text"):
                extracted.append(item.text)
            elif isinstance(item, dict):
                extracted.append(item)
            else:
                extracted.append(str(item))

        if len(extracted) == 1:
            return extracted[0]
        return extracted

    def normalize_tokens(self, raw_data: Any) -> Dict[str, Any]:
        """
        Normalizes MCP output into a token map:
          { token_name: token_value }

        Supported input shapes:
          - JSON string
          - dict
          - list containing one JSON string
        """
        if raw_data is None:
            return {}

        if isinstance(raw_data, list) and len(raw_data) == 1:
            raw_data = raw_data[0]

        if isinstance(raw_data, str):
            raw_data = raw_data.strip()
            if not raw_data:
                return {}
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                return {}

        if not isinstance(raw_data, dict):
            return {}

        tokens: Dict[str, Any] = {}

        # Shape 1: {"tokens": [{"name": "...", "value": "..."}]}
        if "tokens" in raw_data:
            token_block = raw_data["tokens"]

            if isinstance(token_block, list):
                for item in token_block:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        tokens[str(item["name"])] = item["value"]
                if tokens:
                    return tokens

            if isinstance(token_block, dict):
                for k, v in token_block.items():
                    tokens[str(k)] = v
                if tokens:
                    return tokens

        # Shape 2: nested token-style dictionaries
        def is_token_value(value: Any) -> bool:
            return isinstance(value, (str, int, float))

        def walk(prefix: str, obj: Any) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    walk(f"{prefix}{k}." if prefix else f"{k}.", v)
            else:
                if is_token_value(obj):
                    name = prefix[:-1] if prefix.endswith(".") else prefix
                    tokens[name] = obj

        walk("", raw_data)
        return tokens