import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

try:
    from google_adk import Agent
except Exception as e:
    raise ImportError(
        "google_adk is required (core functionality). "
        "Install/enable Google ADK in this environment before running SynchroMesh."
    ) from e


@dataclass
class GhostStyleFinding:
    kind: str  # COLOR_HEX | COLOR_RGB | SIZE | INLINE_STYLE
    value: str
    line: int
    span_start: int
    span_end: int
    snippet: str


class ArchaeologistAgent:
    """
    Archaeologist Agent

    Responsibilities:
    - Scan code content for hard-coded visual values ("ghost styles")
    - Surface lightweight dependency/coupling signals from import usage
    - Use Google ADK for explainability summaries

    Notes:
    - Detection is heuristic and regex-based (not AST-based).
    - Dependency analysis is lightweight and does not fully resolve file paths.
    """

    _HEX_PATTERN = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
    _RGB_PATTERN = re.compile(
        r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(0|1|0?\.\d+)\s*)?\)"
    )
    _SIZE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)(px|rem|em|%)\b")
    _INLINE_STYLE_PATTERN = re.compile(r"\bstyle\s*=\s*\{\{.*?\}\}", re.DOTALL)

    def __init__(self) -> None:
        self.agent = Agent(
            name="Archaeologist",
            instructions=(
                "You are an expert in legacy code analysis.\n"
                "Your goal is to identify hard-coded visual values ('Ghost Styles') such as "
                "colors, sizes, and inline styles that should be replaced by design tokens.\n"
                "When asked, provide concise, explainable summaries of findings and dependency risks.\n"
            ),
        )

    def _adk_call(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Calls the ADK agent in a version-tolerant way.
        """
        payload = {"prompt": prompt, "context": context or {}}

        for method_name in ("run", "invoke", "chat"):
            fn = getattr(self.agent, method_name, None)
            if callable(fn):
                try:
                    result = fn(payload)  # type: ignore[misc]
                    return self._stringify_adk_result(result)
                except TypeError:
                    result = fn(prompt)  # type: ignore[misc]
                    return self._stringify_adk_result(result)

        if callable(self.agent):
            result = self.agent(payload)  # type: ignore[misc]
            return self._stringify_adk_result(result)

        raise RuntimeError("Unable to execute ADK Agent; supported call methods not found.")

    @staticmethod
    def _stringify_adk_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            for key in ("output", "text", "message", "content"):
                if key in result and isinstance(result[key], str):
                    return result[key]
            return str(result)
        for attr in ("output", "text", "message", "content"):
            value = getattr(result, attr, None)
            if isinstance(value, str):
                return value
        return str(result)

    def find_ghost_styles(self, file_content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """
        Detects hard-coded visual values in a file.

        Returns JSON-serializable findings for use by:
        - StylistAgent
        - SyncerAgent
        - ContextStore
        - Dashboard views
        - Evaluation modules
        """
        findings: List[GhostStyleFinding] = []

        def add_finding(kind: str, match_start: int, match_end: int, value: str) -> None:
            line = file_content.count("\n", 0, match_start) + 1
            snippet = self._get_line_snippet(file_content, match_start)
            findings.append(
                GhostStyleFinding(
                    kind=kind,
                    value=value,
                    line=line,
                    span_start=match_start,
                    span_end=match_end,
                    snippet=snippet,
                )
            )

        for match in self._HEX_PATTERN.finditer(file_content):
            add_finding("COLOR_HEX", match.start(), match.end(), match.group())

        for match in self._RGB_PATTERN.finditer(file_content):
            add_finding("COLOR_RGB", match.start(), match.end(), match.group())

        for match in self._SIZE_PATTERN.finditer(file_content):
            add_finding("SIZE", match.start(), match.end(), match.group())

        for match in self._INLINE_STYLE_PATTERN.finditer(file_content):
            add_finding("INLINE_STYLE", match.start(), match.end(), match.group())

        out: List[Dict[str, Any]] = []
        for finding in findings:
            item = asdict(finding)
            item["file_path"] = file_path
            out.append(item)

        return out

    async def analyze_dependencies(self, github_mcp_client: Any, repo_root: str = "") -> Dict[str, Any]:
        """
        Performs lightweight dependency mapping based on import usage.

        Notes:
        - This is not a full AST-based resolver.
        - Reverse import counts are based on import strings, not fully resolved file paths.
        - Good enough for capstone impact analysis and explainability support.
        """
        files = await self._safe_list_files(github_mcp_client, repo_root)
        js_ts_files = [f for f in files if f.endswith((".js", ".jsx", ".ts", ".tsx"))]

        import_re = re.compile(
            r"""(?:
                import\s+(?:[\w*\s{},]+\s+from\s+)?["']([^"']+)["'] |
                require\(\s*["']([^"']+)["']\s*\)
            )""",
            re.VERBOSE,
        )

        reverse_import_counts: Dict[str, int] = {}
        per_file_imports: Dict[str, List[str]] = {}

        for file_path in js_ts_files:
            try:
                content = await self._safe_read_file(github_mcp_client, file_path)
            except Exception:
                continue

            imports: List[str] = []
            for match in import_re.finditer(content):
                imp = match.group(1) or match.group(2)
                if imp:
                    imports.append(imp)

            per_file_imports[file_path] = imports

        for imports in per_file_imports.values():
            for imp in imports:
                reverse_import_counts[imp] = reverse_import_counts.get(imp, 0) + 1

        top_imports = sorted(
            reverse_import_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]

        summary = self._adk_call(
            "Summarize the dependency analysis in 4-6 bullets. "
            "Focus on coupling, shared components, and areas that may be riskier to refactor.",
            context={
                "file_count": len(files),
                "js_ts_file_count": len(js_ts_files),
                "top_imports": top_imports,
            },
        )

        return {
            "file_count": len(files),
            "js_ts_file_count": len(js_ts_files),
            "reverse_import_counts": reverse_import_counts,
            "top_imports": top_imports,
            "analysis_summary": summary,
        }

    @staticmethod
    def _get_line_snippet(text: str, index: int, max_len: int = 220) -> str:
        line_start = text.rfind("\n", 0, index)
        line_end = text.find("\n", index)

        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        if line_end == -1:
            line_end = len(text)

        snippet = text[line_start:line_end].strip()
        if len(snippet) > max_len:
            snippet = snippet[: max_len - 3] + "..."
        return snippet

    async def _safe_list_files(self, github: Any, repo_root: str) -> List[str]:
        fn = getattr(github, "list_files", None)
        if callable(fn):
            return await fn(repo_root)  # type: ignore[misc]

        fn = getattr(github, "get_file_tree", None)
        if callable(fn):
            return await fn(repo_root)  # type: ignore[misc]

        raise AttributeError(
            "GitHub MCP client must expose list_files(...) or get_file_tree(...)."
        )

    async def _safe_read_file(self, github: Any, path: str) -> str:
        fn = getattr(github, "read_file", None)
        if callable(fn):
            return await fn(path)  # type: ignore[misc]

        fn = getattr(github, "get_file_content", None)
        if callable(fn):
            return await fn(path)  # type: ignore[misc]

        raise AttributeError(
            "GitHub MCP client must expose read_file(...) or get_file_content(...)."
        )