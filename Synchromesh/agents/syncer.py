import difflib
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
    - Applies APPROVED LOW-risk token substitutions
    - Generates unified diff patch output (capstone-friendly + auditable)
    - Drafts PR payload through GitHub MCP (or returns PR draft if MCP write not available)
    - Uses ADK for PR body + explainability (ADK is core)
    """

    def __init__(self) -> None:
        self.agent = Agent(
            name="Syncer",
            instructions=(
                "You are a DevOps and Refactoring specialist.\n"
                "Apply approved LOW-risk token swaps safely.\n"
                "Generate auditable diffs and clear PR messages.\n"
                "Never apply HIGH-risk changes automatically.\n"
            ),
        )

    # ---------- ADK call helper ----------
    def _adk_call(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
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
            for k in ("output", "text", "message", "content"):
                if k in result and isinstance(result[k], str):
                    return result[k]
            return str(result)
        for attr in ("output", "text", "message", "content"):
            val = getattr(result, attr, None)
            if isinstance(val, str):
                return val
        return str(result)

    # ---------- public API ----------
    async def apply_token_swaps(
        self,
        recommendations: List[Dict[str, Any]],
        github_mcp: Any,
        require_approved: bool = True,
        approved_key: str = "approved",
    ) -> Dict[str, Any]:
        """
        Applies LOW-risk recommendations and returns:
          - patches (diffs)
          - PR draft payload
          - summary stats

        recommendations should include:
          - file_path, span_start, span_end, replacement_text, risk_level
        If require_approved=True, only recommendations with rec[approved_key]==True are applied.
        """
        # Filter bounded autonomy:
        low = []
        skipped = []

        for rec in recommendations:
            risk = str(rec.get("risk_level", "")).upper()
            if risk != "LOW":
                skipped.append((rec, f"Skipped: risk_level={risk}"))
                continue

            if require_approved and not bool(rec.get(approved_key, False)):
                skipped.append((rec, "Skipped: not approved"))
                continue

            # Must have file_path and either spans or a safe pattern:
            if not rec.get("file_path"):
                skipped.append((rec, "Skipped: missing file_path"))
                continue
            if rec.get("span_start") is None or rec.get("span_end") is None:
                skipped.append((rec, "Skipped: missing span_start/span_end (span-safe patching required)"))
                continue
            if not rec.get("replacement_text"):
                skipped.append((rec, "Skipped: missing replacement_text"))
                continue

            low.append(rec)

        # Group by file_path
        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for rec in low:
            by_file.setdefault(rec["file_path"], []).append(rec)

        patch_results: List[PatchResult] = []
        total_applied = 0
        total_skipped = len(skipped)

        for file_path, file_recs in by_file.items():
            original = await self._safe_read_file(github_mcp, file_path)
            updated, applied_count, notes = self._apply_span_replacements(original, file_recs)
            diff = self._make_diff(file_path, original, updated)

            changed = (original != updated)
            if changed:
                # Attempt write via MCP if available; otherwise just return diff
                await self._safe_write_file_if_available(github_mcp, file_path, updated)

            patch_results.append(
                PatchResult(
                    file_path=file_path,
                    changed=changed,
                    diff=diff,
                    applied_count=applied_count,
                    skipped_count=0,
                    notes=notes,
                )
            )
            total_applied += applied_count

        pr_title = f"SynchroMesh: Token sync ({total_applied} substitutions)"
        pr_body = self._adk_call(
            "Write a GitHub Pull Request description for an automated design-token synchronization.\n"
            "Include: summary, safety/governance note, list of changes (by file), and review instructions.\n"
            "Keep it professional and concise.",
            context={
                "applied_count": total_applied,
                "skipped_count": total_skipped,
                "files_changed": [p.file_path for p in patch_results if p.changed],
                "sample_changes": [
                    {
                        "file": r.get("file_path"),
                        "line": r.get("line"),
                        "old": r.get("original_value"),
                        "new": r.get("replacement_text"),
                        "token": r.get("proposed_token"),
                    }
                    for r in low[:12]
                ],
            },
        )

        pr_payload = {
            "action": "CREATE_PR_DRAFT",
            "title": pr_title,
            "body": pr_body,
            "changes": [{"file_path": p.file_path, "diff": p.diff} for p in patch_results if p.changed],
        }

        return {
            "summary": {
                "applied": total_applied,
                "skipped": total_skipped,
                "files_touched": len(by_file),
            },
            "patches": [asdict(p) for p in patch_results],
            "skipped": [{"rec": rec, "reason": reason} for rec, reason in skipped],
            "pull_request": pr_payload,
        }

    # ---------- patching ----------
    def _apply_span_replacements(self, content: str, recs: List[Dict[str, Any]]) -> Tuple[str, int, List[str]]:
        """
        Applies replacements using spans (start/end indices).
        Important: Apply from end->start so indices remain valid.
        """
        notes: List[str] = []
        applied = 0

        # Sort by span_start descending
        safe_recs = sorted(
            recs,
            key=lambda r: int(r.get("span_start", 0)),
            reverse=True,
        )

        updated = content
        for r in safe_recs:
            s = int(r["span_start"])
            e = int(r["span_end"])
            repl = str(r["replacement_text"])

            if s < 0 or e > len(updated) or s >= e:
                notes.append(f"Invalid span for {r.get('file_path')} at line {r.get('line')}: {s}-{e}")
                continue

            original_slice = updated[s:e]
            # Safety: ensure we are replacing what we think
            expected_value = str(r.get("original_value", "")).strip()
            if expected_value and expected_value not in original_slice:
                # still allow (could be normalized) but flag it
                notes.append(
                    f"Span mismatch warning at line {r.get('line')}: expected '{expected_value}' "
                    f"not found exactly in slice '{original_slice}'. Applied anyway."
                )

            updated = updated[:s] + repl + updated[e:]
            applied += 1

        return updated, applied, notes

    @staticmethod
    def _make_diff(file_path: str, original: str, updated: str) -> str:
        if original == updated:
            return ""
        o_lines = original.splitlines(keepends=True)
        u_lines = updated.splitlines(keepends=True)
        diff = difflib.unified_diff(
            o_lines,
            u_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)

    # ---------- MCP I/O ----------
    async def _safe_read_file(self, github: Any, path: str) -> str:
        fn = getattr(github, "read_file", None)
        if callable(fn):
            return await fn(path)  # type: ignore[misc]
        fn = getattr(github, "get_file_content", None)
        if callable(fn):
            return await fn(path)  # type: ignore[misc]
        raise AttributeError("GitHub MCP client must expose read_file(...) or get_file_content(...).")

    async def _safe_write_file_if_available(self, github: Any, path: str, content: str) -> None:
        """
        If your GitHub MCP server supports writing, this will persist changes.
        If not available, it's still OK for capstone: diffs are returned for audit.
        """
        fn = getattr(github, "write_file", None)
        if callable(fn):
            await fn(path, content)  # type: ignore[misc]
            return
        fn = getattr(github, "update_file", None)
        if callable(fn):
            await fn(path, content)  # type: ignore[misc]
            return
        # no write capability — silently skip (diff still returned)
        return