from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class GitHubMCPClient:
    def __init__(self):
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_GITHUB_TOKEN"}
        )

    async def read_repository_file(self, owner: str, repo: str, path: str):
        """Fetches file content so the Archaeologist can scan for drift."""
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("get_file_contents", {
                    "owner": owner, "repo": repo, "path": path
                })
                return result.content[0].text

    async def create_sync_pr(self, owner: str, repo: str, title: str, branch: str, body: str):
        """
        Used by the Syncer Agent to push the final refactored code.
        Ensures the 'Action' is auditable and governed.
        """
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool("create_pull_request", {
                    "owner": owner, "repo": repo, "title": title, 
                    "head": branch, "base": "main", "body": body
                })