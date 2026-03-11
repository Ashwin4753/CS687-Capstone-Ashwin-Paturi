import difflib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    from google.adk import Agent  # type: ignore
except Exception:
    Agent = None

@dataclass
class PatchResult:
    file_path: str
    changed: bool
    diff: str
    applied_count: int
    skipped_count: int
    notes: List[str]

class SyncerAgent:
    """
    Syncer Agent

    Responsibilities:
    - Apply APPROVED LOW-risk token substitutions
    - Generate unified diffs for auditability
    - Produce PR draft content with a stable local fallback
    - Respect bounded autonomy (never auto-apply MEDIUM/HIGH)

    Notes:
    - File writes are best-effort and depend on GitHub MCP write support.
    - If write support is unavailable, diffs are still produced for review.
    """

    def __init__(self) -> None:
        self.agent = None

    def _adk_call(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Safe fallback PR body generator for demo/runtime stability.
        """
        context = context or {}
        applied_count = context.get("applied_count", 0)
        skipped_count = context.get("skipped_count", 0)
        files_changed = context.get("files_changed", []) or []

        lines = [
            "## Summary",
            f"- Applied substitutions: {applied_count}",
            f"- Skipped substitutions: {skipped_count}",
            "",
            "## Governance & Safety",
            "- Only approved LOW-risk substitutions were applied automatically.",
            "- MEDIUM/HIGH-risk findings remain subject to human review.",
            "",
            "## Files Changed",
        ]

        if files_changed:
            for file_path in files_changed[:20]:
                lines.append(f"- {file_path}")
        else:
            lines.append("- No files changed.")

        lines.extend(
            [
                "",
                "## Reviewer Guidance",
                "- Verify token substitutions preserve intended visual behavior.",
                "- Review adjacent components for consistency where shared styles are used.",
            ]
        )

        return "\n".join(lines)

    async def apply_token_swaps(
        self,
        recommendations: List[Dict[str, Any]],
        github_mcp: Any,
        require_approved: bool = True,
        approved_key: str = "approved",
    ) -> Dict[str, Any]:
        """
        Applies approved LOW-risk recommendations.
        """
        eligible: List[Dict[str, Any]] = []
        skipped: List[Tuple[Dict[str, Any], str]] = []

        for rec in recommendations:
            risk = str(rec.get("risk_level", "")).upper()
            if risk != "LOW":
                skipped.append((rec, f"Skipped: risk_level={risk}"))
                continue

            if require_approved and not bool(rec.get(approved_key, False)):
                skipped.append((rec, "Skipped: not approved"))
                continue

            if not rec.get("file_path"):
                skipped.append((rec, "Skipped: missing file_path"))
                continue

            if rec.get("span_start") is None or rec.get("span_end") is None:
                skipped.append((rec, "Skipped: missing span_start/span_end"))
                continue

            replacement_text = str(rec.get("replacement_text", "")).strip()
            if not replacement_text or replacement_text == "N/A":
                skipped.append((rec, "Skipped: invalid replacement_text"))
                continue

            eligible.append(rec)

        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for rec in eligible:
            by_file.setdefault(str(rec["file_path"]), []).append(rec)

        patch_results: List[PatchResult] = []
        applied_recommendations: List[Dict[str, Any]] = []
        total_applied = 0
        total_skipped = len(skipped)

        for file_path, file_recs in by_file.items():
            original_content = await self._safe_read_file(github_mcp, file_path)

            (
                updated_content,
                applied_count,
                file_notes,
                applied_recs,
                skipped_in_file,
            ) = self._apply_span_replacements(original_content, file_recs)

            diff = self._make_diff(file_path, original_content, updated_content)
            changed = original_content != updated_content

            if changed:
                await self._safe_write_file_if_available(github_mcp, file_path, updated_content)

            patch_results.append(
                PatchResult(
                    file_path=file_path,
                    changed=changed,
                    diff=diff,
                    applied_count=applied_count,
                    skipped_count=skipped_in_file,
                    notes=file_notes,
                )
            )

            total_applied += applied_count
            applied_recommendations.extend(applied_recs)
            total_skipped += skipped_in_file

        pr_title = f"SynchroMesh: Token sync ({total_applied} substitutions)"
        pr_body = self._adk_call(
            "Write a concise GitHub Pull Request description for an automated design-token synchronization.",
            context={
                "applied_count": total_applied,
                "skipped_count": total_skipped,
                "files_changed": [patch.file_path for patch in patch_results if patch.changed],
                "sample_changes": [
                    {
                        "file": rec.get("file_path"),
                        "line": rec.get("line"),
                        "old": rec.get("original_value"),
                        "new": rec.get("replacement_text"),
                        "token": rec.get("proposed_token"),
                        "change_id": rec.get("change_id"),
                    }
                    for rec in applied_recommendations[:12]
                ],
            },
        )

        pr_payload = {
            "action": "CREATE_PR_DRAFT",
            "title": pr_title,
            "body": pr_body,
            "changes": [
                {
                    "file_path": patch.file_path,
                    "diff": patch.diff[:5000],
                }
                for patch in patch_results
                if patch.changed
            ],
        }

        return {
            "summary": {
                "applied": total_applied,
                "skipped": total_skipped,
                "files_touched": len([patch for patch in patch_results if patch.changed]),
            },
            "patches": [asdict(patch) for patch in patch_results],
            "skipped": [{"rec": rec, "reason": reason} for rec, reason in skipped],
            "applied_recommendations": applied_recommendations,
            "pull_request": pr_payload,
        }

    def _apply_span_replacements(
        self,
        content: str,
        recs: List[Dict[str, Any]],
    ) -> Tuple[str, int, List[str], List[Dict[str, Any]], int]:
        """
        Applies replacements using spans (start/end indices).

        Important:
        - Replacements are applied from end -> start
        - Overlapping spans are skipped
        """
        notes: List[str] = []
        applied = 0
        skipped_in_file = 0
        applied_recommendations: List[Dict[str, Any]] = []

        safe_recs = sorted(
            recs,
            key=lambda rec: int(rec.get("span_start", 0)),
            reverse=True,
        )

        used_spans: List[Tuple[int, int]] = []
        updated = content

        for rec in safe_recs:
            start = int(rec["span_start"])
            end = int(rec["span_end"])
            replacement = str(rec["replacement_text"])

            if start < 0 or end > len(updated) or start >= end:
                notes.append(
                    f"Invalid span for {rec.get('file_path')} at line {rec.get('line')}: {start}-{end}"
                )
                skipped_in_file += 1
                continue

            overlaps = any(
                not (end <= used_start or start >= used_end)
                for used_start, used_end in used_spans
            )
            if overlaps:
                notes.append(
                    f"Skipped overlapping replacement at {rec.get('file_path')}:{rec.get('line')} ({start}-{end})"
                )
                skipped_in_file += 1
                continue

            original_slice = updated[start:end]
            expected_value = str(rec.get("original_value", "")).strip()

            if expected_value and expected_value not in original_slice:
                notes.append(
                    f"Span mismatch warning at line {rec.get('line')}: expected '{expected_value}' "
                    f"not found exactly in slice '{original_slice}'. Applied anyway."
                )

            updated = updated[:start] + replacement + updated[end:]
            used_spans.append((start, end))
            applied += 1
            applied_recommendations.append(rec)

        return updated, applied, notes, applied_recommendations, skipped_in_file

    @staticmethod
    def _make_diff(file_path: str, original: str, updated: str) -> str:
        if original == updated:
            return ""

        original_lines = original.splitlines(keepends=True)
        updated_lines = updated.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            updated_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)

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

    async def _safe_write_file_if_available(self, github: Any, path: str, content: str) -> None:
        """
        Best-effort write support.
        If unavailable, diffs are still returned for governance review.
        """
        fn = getattr(github, "write_file", None)
        if callable(fn):
            await fn(path, content)  # type: ignore[misc]
            return

        fn = getattr(github, "update_file", None)
        if callable(fn):
            await fn(path, content)  # type: ignore[misc]
            return

        return