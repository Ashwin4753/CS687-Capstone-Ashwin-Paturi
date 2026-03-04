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
      - write_file(path, content) -> optional
      - create_pull_request(...) -> MCP PR creation
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

        # These should be set by your app (owner/repo), not hardcoded here.
        self.owner: Optional[str] = None
        self.repo: Optional[str] = None

    def set_repo(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo

    async def list_files(self, repo_root: str = "") -> List[str]:
        """
        Returns a list of file paths (best-effort).
        """
        owner, repo = self._require_repo()

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_names = await self._list_tool_names(session)

                # Candidate tools differ by server version
                candidates = ["get_repo_tree", "get_repository_tree", "list_repo_files", "list_files"]
                tool = self._pick_tool(tool_names, candidates)
                if not tool:
                    raise RuntimeError(f"No repo-tree tool found. Available tools: {tool_names}")

                # Some tools want {owner, repo, path} others just {owner, repo}
                payload = {"owner": owner, "repo": repo}
                if repo_root:
                    payload["path"] = repo_root

                result = await session.call_tool(tool, payload)

                # Expect text containing JSON array or structured response
                return self._extract_file_list(result)

    async def read_file(self, path: str) -> str:
        owner, repo = self._require_repo()

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_names = await self._list_tool_names(session)

                candidates = ["get_file_contents", "get_file_content", "read_file", "get_contents"]
                tool = self._pick_tool(tool_names, candidates)
                if not tool:
                    raise RuntimeError(f"No read-file tool found. Available tools: {tool_names}")

                result = await session.call_tool(tool, {"owner": owner, "repo": repo, "path": path})
                if getattr(result, "content", None):
                    return result.content[0].text
                return ""

    async def create_pull_request(self, title: str, head: str, base: str, body: str) -> Any:
        owner, repo = self._require_repo()

        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_names = await self._list_tool_names(session)

                candidates = ["create_pull_request", "open_pull_request"]
                tool = self._pick_tool(tool_names, candidates)
                if not tool:
                    raise RuntimeError(f"No create PR tool found. Available tools: {tool_names}")

                return await session.call_tool(
                    tool,
                    {"owner": owner, "repo": repo, "title": title, "head": head, "base": base, "body": body},
                )

    # --- helpers ---
    def _require_repo(self):
        if not self.owner or not self.repo:
            raise RuntimeError("GitHubMCPClient repo not set. Call set_repo(owner, repo) first.")
        return self.owner, self.repo

    async def _list_tool_names(self, session: ClientSession) -> List[str]:
        tools = await session.list_tools()
        if hasattr(tools, "tools"):
            return [t.name for t in tools.tools]
        return []

    @staticmethod
    def _pick_tool(tool_names: List[str], candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in tool_names:
                return c
        return None

    @staticmethod
    def _extract_file_list(result: Any) -> List[str]:
        """
        Best-effort extraction:
          - If MCP returns JSON text list
          - Or dict with 'files'/'tree'
        """
        if not getattr(result, "content", None):
            return []

        text = result.content[0].text
        if not text:
            return []

        import json

        try:
            data = json.loads(text)
        except Exception:
            return []

        if isinstance(data, list):
            # list of file paths or tree nodes
            files = []
            for x in data:
                if isinstance(x, str):
                    files.append(x)
                elif isinstance(x, dict) and "path" in x:
                    files.append(x["path"])
            return files

        if isinstance(data, dict):
            if "files" in data and isinstance(data["files"], list):
                return [f["path"] if isinstance(f, dict) and "path" in f else str(f) for f in data["files"]]
            if "tree" in data and isinstance(data["tree"], list):
                return [n.get("path") for n in data["tree"] if isinstance(n, dict) and n.get("path")]

        return []