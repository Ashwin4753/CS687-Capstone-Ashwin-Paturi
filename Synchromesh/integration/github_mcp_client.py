import json
import os
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitHubMCPClient:
    """
    MCP client wrapper for GitHub.

    Public methods used by orchestrator/agents:
      - list_files(repo_root) -> List[str]
      - read_file(path) -> str
      - write_file(path, content) -> optional best-effort
      - create_pull_request(...) -> MCP PR creation
      - list_available_tools() -> List[str]
      - health_check() -> bool
    """

    def __init__(self, server_path: str = "npx"):
        token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError(
                "Missing GITHUB_PERSONAL_ACCESS_TOKEN (or GITHUB_TOKEN) in environment. "
                "Do not hardcode secrets in code."
            )

        self.server_params = StdioServerParameters(
            command=server_path,
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
        )

        self.owner: Optional[str] = None
        self.repo: Optional[str] = None

    def set_repo(self, owner: str, repo: str):
        owner = str(owner).strip()
        repo = str(repo).strip()

        if not owner or not repo:
            raise ValueError("Both owner and repo must be non-empty strings.")

        self.owner = owner
        self.repo = repo

    async def list_available_tools(self) -> List[str]:
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await self._list_tool_names(session)

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

    async def list_files(self, repo_root: str = "") -> List[str]:
        """
        Returns a list of repository file paths (best-effort).
        """
        owner, repo = self._require_repo()

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_names = await self._list_tool_names(session)

                candidates = [
                    "get_repo_tree",
                    "get_repository_tree",
                    "list_repo_files",
                    "list_files",
                ]
                tool = self._pick_tool(tool_names, candidates)
                if not tool:
                    raise RuntimeError(
                        f"No repo-tree/list-files tool found. Available tools: {tool_names}"
                    )

                payload_candidates = [
                    {"owner": owner, "repo": repo, "path": repo_root} if repo_root else {"owner": owner, "repo": repo},
                    {"owner": owner, "repo": repo, "directory": repo_root} if repo_root else {"owner": owner, "repo": repo},
                    {"owner": owner, "repo": repo, "root": repo_root} if repo_root else {"owner": owner, "repo": repo},
                    {"owner": owner, "repo": repo},
                ]

                last_error = None
                for payload in payload_candidates:
                    try:
                        result = await session.call_tool(tool, payload)
                        files = self._extract_file_list(result)
                        if files:
                            return files
                    except Exception as e:
                        last_error = e

                if last_error:
                    raise RuntimeError(
                        f"Failed to list files using tool '{tool}' with known payload formats."
                    ) from last_error

                return []

    async def read_file(self, path: str) -> str:
        owner, repo = self._require_repo()

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_names = await self._list_tool_names(session)

                candidates = [
                    "get_file_contents",
                    "get_file_content",
                    "read_file",
                    "get_contents",
                ]
                tool = self._pick_tool(tool_names, candidates)
                if not tool:
                    raise RuntimeError(
                        f"No read-file tool found. Available tools: {tool_names}"
                    )

                result = await session.call_tool(
                    tool,
                    {"owner": owner, "repo": repo, "path": path},
                )
                return self._extract_text_content(result)

    async def write_file(self, path: str, content: str) -> None:
        """
        Optional best-effort write support.

        Not all GitHub MCP servers expose file-write/update tools.
        If unsupported, this method raises no error and simply returns.
        """
        owner, repo = self._require_repo()

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_names = await self._list_tool_names(session)

                candidates = [
                    "update_file",
                    "write_file",
                    "put_file_contents",
                    "create_or_update_file",
                ]
                tool = self._pick_tool(tool_names, candidates)
                if not tool:
                    return

                payload_candidates = [
                    {"owner": owner, "repo": repo, "path": path, "content": content},
                    {"owner": owner, "repo": repo, "file_path": path, "content": content},
                ]

                for payload in payload_candidates:
                    try:
                        await session.call_tool(tool, payload)
                        return
                    except Exception:
                        continue

                return

    async def create_pull_request(self, title: str, head: str, base: str, body: str) -> Any:
        owner, repo = self._require_repo()

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_names = await self._list_tool_names(session)

                candidates = ["create_pull_request", "open_pull_request"]
                tool = self._pick_tool(tool_names, candidates)
                if not tool:
                    raise RuntimeError(
                        f"No create-pull-request tool found. Available tools: {tool_names}"
                    )

                return await session.call_tool(
                    tool,
                    {
                        "owner": owner,
                        "repo": repo,
                        "title": title,
                        "head": head,
                        "base": base,
                        "body": body,
                    },
                )

    def _require_repo(self):
        if not self.owner or not self.repo:
            raise RuntimeError(
                "GitHubMCPClient repo not set. Call set_repo(owner, repo) first."
            )
        return self.owner, self.repo

    async def _list_tool_names(self, session: ClientSession) -> List[str]:
        tools = await session.list_tools()
        if hasattr(tools, "tools"):
            return [t.name for t in tools.tools]
        return []

    @staticmethod
    def _pick_tool(tool_names: List[str], candidates: List[str]) -> Optional[str]:
        for candidate in candidates:
            if candidate in tool_names:
                return candidate
        return None

    @staticmethod
    def _extract_text_content(result: Any) -> str:
        """
        Safely extracts textual content from MCP result.
        """
        if result is None:
            return ""

        content = getattr(result, "content", None)
        if not content:
            return ""

        parts: List[str] = []
        for item in content:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, dict):
                parts.append(json.dumps(item))
            else:
                parts.append(str(item))

        return "\n".join(parts).strip()

    @staticmethod
    def _extract_file_list(result: Any) -> List[str]:
        """
        Best-effort extraction of repository file paths.
        Supports:
          - JSON text list
          - JSON dict with 'files', 'tree', or 'items'
          - list of dict nodes with 'path'
        """
        raw_text = GitHubMCPClient._extract_text_content(result)
        if not raw_text:
            return []

        try:
            data = json.loads(raw_text)
        except Exception:
            return []

        if isinstance(data, list):
            files: List[str] = []
            for item in data:
                if isinstance(item, str):
                    files.append(item)
                elif isinstance(item, dict) and "path" in item:
                    files.append(str(item["path"]))
            return files

        if isinstance(data, dict):
            if "files" in data and isinstance(data["files"], list):
                out: List[str] = []
                for item in data["files"]:
                    if isinstance(item, dict) and "path" in item:
                        out.append(str(item["path"]))
                    else:
                        out.append(str(item))
                return out

            if "tree" in data and isinstance(data["tree"], list):
                out: List[str] = []
                for node in data["tree"]:
                    if isinstance(node, dict) and node.get("path"):
                        out.append(str(node["path"]))
                return out

            if "items" in data and isinstance(data["items"], list):
                out: List[str] = []
                for node in data["items"]:
                    if isinstance(node, dict) and node.get("path"):
                        out.append(str(node["path"]))
                return out

        return []