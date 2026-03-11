import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

try:
    from google.adk import Agent  # type: ignore
except Exception:
    Agent = None

@dataclass
class GhostStyleFinding:
    kind: str  # COLOR_HEX | COLOR_RGB | SIZE | INLINE_STYLE
    value: str
    line: int
    span_start: int
    span_end: int
    snippet: str

@dataclass
class OutdatedComponentFinding:
    type: str  # OUTDATED_FRONTEND_COMPONENT | OUTDATED_BACKEND_MODULE
    file_path: str
    reason: str
    severity: str  # LOW | MEDIUM | HIGH
    confidence_score: float
    line: Optional[int] = None
    snippet: str = ""

class ArchaeologistAgent:
    """
    Archaeologist Agent

    Responsibilities:
    - Scan code content for hard-coded visual values ("ghost styles")
    - Surface lightweight dependency/coupling signals from import usage
    - Detect outdated frontend components and backend modules
    - Provide explainability summaries with a stable local fallback

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

    _TODO_PATTERN = re.compile(r"\bTODO\b", re.IGNORECASE)
    _FIXME_PATTERN = re.compile(r"\bFIXME\b", re.IGNORECASE)
    _DEBUG_PRINT_PATTERN = re.compile(r"\bprint\s*\(")
    _CONSOLE_LOG_PATTERN = re.compile(r"\bconsole\.log\s*\(")
    _INLINE_STYLE_JSX_PATTERN = re.compile(r"\bstyle\s*=\s*\{\{.*?\}\}", re.DOTALL)
    _DEPRECATED_IMPORT_PATTERN = re.compile(
        r"""(?:
            import\s+(?:[\w*\s{},]+\s+from\s+)?["']([^"']+)["'] |
            require\(\s*["']([^"']+)["']\s*\)
        )""",
        re.VERBOSE,
    )

    def __init__(self) -> None:
        self.agent = None

    def _adk_call(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Safe fallback explanation generator for demo/runtime stability.
        """
        context = context or {}
        file_count = context.get("file_count", 0)
        js_ts_file_count = context.get("js_ts_file_count", 0)
        top_imports = context.get("top_imports", []) or []

        if top_imports:
            preview = ", ".join([f"{name} ({count})" for name, count in top_imports[:3]])
            return (
                f"Dependency analysis completed across {file_count} files "
                f"({js_ts_file_count} JS/TS files). The most frequently referenced imports are "
                f"{preview}, suggesting these areas may have broader refactor impact."
            )

        return (
            f"Dependency analysis completed across {file_count} files "
            f"({js_ts_file_count} JS/TS files). No dominant shared imports were identified."
        )

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

    async def detect_outdated_components(
        self,
        github_mcp_client: Any,
        repo_root: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Detects outdated frontend components and backend modules using heuristic rules.

        Frontend examples:
        - inline style usage
        - hardcoded color values
        - console.log in UI code

        Backend examples:
        - print statements
        - TODO / FIXME markers
        - broad exception swallowing
        """
        files = await self._safe_list_files(github_mcp_client, repo_root)
        findings: List[OutdatedComponentFinding] = []

        for file_path in files:
            normalized = str(file_path).replace("\\", "/").lower()

            if not normalized.endswith(
                (".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".py")
            ):
                continue

            try:
                content = await self._safe_read_file(github_mcp_client, file_path)
            except Exception:
                continue

            # Frontend heuristics
            if normalized.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".scss")):
                findings.extend(self._scan_frontend_outdated_patterns(content, file_path))

            # Backend heuristics
            if normalized.endswith(".py") or (
                normalized.endswith((".ts", ".js"))
                and any(token in normalized for token in ["/api/", "/server/", "/backend/", "/services/"])
            ):
                findings.extend(self._scan_backend_outdated_patterns(content, file_path))

        return [asdict(item) for item in findings]

    def _scan_frontend_outdated_patterns(
        self,
        content: str,
        file_path: str,
    ) -> List[OutdatedComponentFinding]:
        out: List[OutdatedComponentFinding] = []

        for match in self._INLINE_STYLE_JSX_PATTERN.finditer(content):
            out.append(
                OutdatedComponentFinding(
                    type="OUTDATED_FRONTEND_COMPONENT",
                    file_path=file_path,
                    reason="Inline style usage detected (legacy styling pattern).",
                    severity="MEDIUM",
                    confidence_score=0.88,
                    line=self._line_from_index(content, match.start()),
                    snippet=self._get_line_snippet(content, match.start()),
                )
            )

        for match in self._HEX_PATTERN.finditer(content):
            out.append(
                OutdatedComponentFinding(
                    type="OUTDATED_FRONTEND_COMPONENT",
                    file_path=file_path,
                    reason="Hardcoded color value detected instead of tokenized styling.",
                    severity="LOW",
                    confidence_score=0.82,
                    line=self._line_from_index(content, match.start()),
                    snippet=self._get_line_snippet(content, match.start()),
                )
            )

        for match in self._CONSOLE_LOG_PATTERN.finditer(content):
            out.append(
                OutdatedComponentFinding(
                    type="OUTDATED_FRONTEND_COMPONENT",
                    file_path=file_path,
                    reason="console.log statement detected in frontend component.",
                    severity="LOW",
                    confidence_score=0.78,
                    line=self._line_from_index(content, match.start()),
                    snippet=self._get_line_snippet(content, match.start()),
                )
            )

        return self._deduplicate_outdated_findings(out)

    def _scan_backend_outdated_patterns(
        self,
        content: str,
        file_path: str,
    ) -> List[OutdatedComponentFinding]:
        out: List[OutdatedComponentFinding] = []

        for match in self._DEBUG_PRINT_PATTERN.finditer(content):
            out.append(
                OutdatedComponentFinding(
                    type="OUTDATED_BACKEND_MODULE",
                    file_path=file_path,
                    reason="Debug print statement detected in backend/module code.",
                    severity="LOW",
                    confidence_score=0.8,
                    line=self._line_from_index(content, match.start()),
                    snippet=self._get_line_snippet(content, match.start()),
                )
            )

        for match in self._TODO_PATTERN.finditer(content):
            out.append(
                OutdatedComponentFinding(
                    type="OUTDATED_BACKEND_MODULE",
                    file_path=file_path,
                    reason="TODO marker suggests incomplete or deferred modernization work.",
                    severity="LOW",
                    confidence_score=0.76,
                    line=self._line_from_index(content, match.start()),
                    snippet=self._get_line_snippet(content, match.start()),
                )
            )

        for match in self._FIXME_PATTERN.finditer(content):
            out.append(
                OutdatedComponentFinding(
                    type="OUTDATED_BACKEND_MODULE",
                    file_path=file_path,
                    reason="FIXME marker suggests known technical debt or unresolved issue.",
                    severity="MEDIUM",
                    confidence_score=0.81,
                    line=self._line_from_index(content, match.start()),
                    snippet=self._get_line_snippet(content, match.start()),
                )
            )

        broad_except = re.finditer(r"except\s+Exception\s*:", content)
        for match in broad_except:
            out.append(
                OutdatedComponentFinding(
                    type="OUTDATED_BACKEND_MODULE",
                    file_path=file_path,
                    reason="Broad exception handling pattern detected.",
                    severity="MEDIUM",
                    confidence_score=0.79,
                    line=self._line_from_index(content, match.start()),
                    snippet=self._get_line_snippet(content, match.start()),
                )
            )

        return self._deduplicate_outdated_findings(out)

    @staticmethod
    def _deduplicate_outdated_findings(
        findings: List[OutdatedComponentFinding],
    ) -> List[OutdatedComponentFinding]:
        seen = set()
        deduped: List[OutdatedComponentFinding] = []

        for item in findings:
            key = (item.type, item.file_path, item.reason, item.line, item.snippet)
            if key not in seen:
                seen.add(key)
                deduped.append(item)

        return deduped

    @staticmethod
    def _line_from_index(text: str, index: int) -> int:
        return text.count("\n", 0, index) + 1

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