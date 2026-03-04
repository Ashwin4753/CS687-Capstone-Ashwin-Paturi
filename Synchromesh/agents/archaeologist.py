import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

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
    - Scans file content for hard-coded styles (ghost styles)
    - Optionally analyzes lightweight import-dependencies for risk support
    - Uses Google ADK Agent for explainable summaries (ADK is core)
    """
    # --- regex patterns (capstone-safe coverage) ---
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
                "You are an expert in Legacy Code Analysis.\n"
                "Your goal is to identify 'Ghost Styles' (hard-coded values like colors/sizes/inline styles)\n"
                "that should be replaced by design tokens.\n"
                "When asked, provide a concise explanation of findings and potential risk factors.\n"
            ),
        )

    # ---------- ADK call helper ----------
    def _adk_call(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Calls the ADK Agent in a version-tolerant way.
        ADK method names may vary; we try common ones.
        """
        payload = {"prompt": prompt, "context": context or {}}

        for method_name in ("run", "invoke", "chat"):
            fn = getattr(self.agent, method_name, None)
            if callable(fn):
                try:
                    result = fn(payload)  # type: ignore[misc]
                    return self._stringify_adk_result(result)
                except TypeError:
                    # Some ADK versions accept raw prompt instead of dict.
                    result = fn(prompt)  # type: ignore[misc]
                    return self._stringify_adk_result(result)

        if callable(self.agent):
            result = self.agent(payload)  # type: ignore[misc]
            return self._stringify_adk_result(result)

        # If none matched, fail loudly (ADK required).
        raise RuntimeError("Unable to execute ADK Agent; supported call methods not found.")

    @staticmethod
    def _stringify_adk_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        # Common patterns: {"output": "..."} or object with .output/.text
        if isinstance(result, dict):
            for k in ("output", "text", "message", "content"):
                if k in result and isinstance(result[k], str):
                    return result[k]
            return str(result)
        for attr in ("output", "text", "message", "content"):
            val = getattr(result, attr, None)
            if isinstance(val, str):
                return val
        return str(result)

    # ---------- core detection ----------
    def find_ghost_styles(self, file_content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """
        Detect hard-coded style values.
        Returns a list of dicts (JSON-serializable), ready for ContextStore / dashboard.
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

        # Hex colors
        for m in self._HEX_PATTERN.finditer(file_content):
            add_finding("COLOR_HEX", m.start(), m.end(), m.group())

        # rgb/rgba
        for m in self._RGB_PATTERN.finditer(file_content):
            add_finding("COLOR_RGB", m.start(), m.end(), m.group())

        # sizes: px/rem/em/%
        for m in self._SIZE_PATTERN.finditer(file_content):
            add_finding("SIZE", m.start(), m.end(), m.group())

        # inline style blocks (React)
        for m in self._INLINE_STYLE_PATTERN.finditer(file_content):
            # Inline style is usually HIGH risk; still useful to detect and show.
            add_finding("INLINE_STYLE", m.start(), m.end(), m.group())

        # Convert to dicts and include file_path
        out: List[Dict[str, Any]] = []
        for f in findings:
            d = asdict(f)
            d["file_path"] = file_path
            out.append(d)

        return out

    async def analyze_dependencies(self, github_mcp_client: Any, repo_root: str = "") -> Dict[str, Any]:
        """
        Lightweight dependency mapping:
        - lists repository files
        - builds reverse import counts (how many files import a given file)
        This is NOT a full AST graph; it's capstone-appropriate and explainable.

        Expected github_mcp_client interface (one of):
          - await github_mcp_client.list_files(repo_root) -> List[str]
          - await github_mcp_client.read_file(path) -> str
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

        for fp in js_ts_files:
            try:
                content = await self._safe_read_file(github_mcp_client, fp)
            except Exception:
                continue

            imports: List[str] = []
            for m in import_re.finditer(content):
                imp = m.group(1) or m.group(2)
                if not imp:
                    continue
                imports.append(imp)

            per_file_imports[fp] = imports

        # Very simple reverse count: if a file imports "./x", increment count for resolved file-ish key
        for importer, imports in per_file_imports.items():
            for imp in imports:
                key = imp
                reverse_import_counts[key] = reverse_import_counts.get(key, 0) + 1

        # Explainability from ADK
        summary = self._adk_call(
            "Summarize the dependency analysis results in 4-6 bullets, focusing on risk signals "
            "(high coupling / many importers / likely shared components).",
            context={
                "file_count": len(files),
                "js_ts_file_count": len(js_ts_files),
                "top_imports": sorted(reverse_import_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            },
        )

        return {
            "file_count": len(files),
            "js_ts_file_count": len(js_ts_files),
            "reverse_import_counts": reverse_import_counts,
            "analysis_summary": summary,
        }

    # ---------- helpers ----------
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
        raise AttributeError("GitHub MCP client must expose list_files(...) or get_file_tree(...).")

    async def _safe_read_file(self, github: Any, path: str) -> str:
        fn = getattr(github, "read_file", None)
        if callable(fn):
            return await fn(path)  # type: ignore[misc]
        fn = getattr(github, "get_file_content", None)
        if callable(fn):
            return await fn(path)  # type: ignore[misc]
        raise AttributeError("GitHub MCP client must expose read_file(...) or get_file_content(...).")