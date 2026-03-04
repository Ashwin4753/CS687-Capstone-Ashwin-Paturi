from __future__ import annotations
from typing import Any, Dict, List, Optional
import yaml
from agents.archaeologist import ArchaeologistAgent
from agents.stylist import StylistAgent
from agents.syncer import SyncerAgent
from core.context_store import ContextStore
from core.state import StateManager

class SynchroMeshOrchestrator:
    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.archaeologist = ArchaeologistAgent()
        self.stylist = StylistAgent()
        self.syncer = SyncerAgent()

        trace_dir = self.config.get("metrics", {}).get("trace_path", "evaluation/traces/")
        outputs_dir = "outputs"
        self.context = ContextStore(trace_dir=trace_dir, outputs_dir=outputs_dir)

        self.state = StateManager(config_path=config_path)

    async def run_sync_pipeline(
        self,
        repo_root: str,
        figma_file_id: str,
        github_mcp_client: Any,
        figma_mcp_client: Any,
        approved_changes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        End-to-end pipeline:
          1) GitHub MCP: list files + read code
          2) Archaeologist: detect drift
          3) Figma MCP: fetch tokens
          4) Stylist: match drift to tokens + risk tiers
          5) Governance: decide apply vs await approval
          6) Syncer: apply approved LOW swaps + emit diffs/PR draft
          7) Metrics + traces + outputs
        """
        self.context.set_run_context(repo=repo_root, figma_file_id=figma_file_id)

        # --- settings ---
        governance = self.config.get("governance", {})
        auto_apply_low = bool(governance.get("auto_apply_low_risk", True))
        require_approval_for = set([x.upper() for x in governance.get("require_approval_for", ["MEDIUM", "HIGH"])])
        max_files = int(governance.get("max_files_per_sync", 10))
        restricted_dirs = governance.get("restricted_directories", []) or []

        token_format = self.config.get("design_tokens", {}).get("format", "var(--{token})")

        # --- 1) list files ---
        files = await self._safe_list_files(github_mcp_client, repo_root)
        code_files = [f for f in files if f.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".scss"))]

        # Restrict directories
        def is_restricted(path: str) -> bool:
            return any(path.startswith(d.strip("/")) or path.startswith(d) for d in restricted_dirs)

        code_files = [f for f in code_files if not is_restricted(f)]
        code_files = code_files[: max(1, max_files)]  # cap to avoid huge runs in capstone demo

        # --- 2) archaeology ---
        all_findings: List[dict] = []
        for fp in code_files:
            content = await self._safe_read_file(github_mcp_client, fp)
            findings = self.archaeologist.find_ghost_styles(content, file_path=fp)
            all_findings.extend(findings)

        self.context.add_detected_drift(all_findings)

        # --- 3) tokens ---
        tokens = await self._safe_get_figma_tokens(figma_mcp_client, figma_file_id)

        # --- 4) stylist recommendations ---
        recommendations = self.stylist.detect_drift(all_findings, tokens, token_format=token_format)
        self.context.add_recommendations(recommendations)

        # --- 5) governance decision ---
        # if we have any MEDIUM/HIGH, we can still proceed if user supplied approved_changes
        needs_approval = [r for r in recommendations if str(r.get("risk_level", "")).upper() in require_approval_for]

        if needs_approval and not approved_changes:
            # Export partial outputs (drift + recommendations) for dashboard review
            metrics = self.state.compute_metrics(
                total_findings=len(all_findings),
                recommendations=recommendations,
                patches_applied=0,
            )
            self.context.set_metrics(metrics)
            trace_path = self.context.save_session_trace()
            outputs = self.context.export_outputs()

            return {
                "status": "AWAITING_APPROVAL",
                "message": "Approval required for MEDIUM/HIGH recommendations.",
                "needs_approval_count": len(needs_approval),
                "trace_path": trace_path,
                "outputs": outputs,
            }

        # If approvals provided, mark approved changes and merge flag into recs
        approved = approved_changes or []
        approved_lookup = {(a.get("file_path"), a.get("line"), a.get("original_value")): True for a in approved}

        for r in recommendations:
            key = (r.get("file_path"), r.get("line"), r.get("original_value"))
            r["approved"] = bool(approved_lookup.get(key, False))

        self.context.set_approved_changes([r for r in recommendations if r.get("approved")])

        # --- 6) execution ---
        # Apply only LOW (and approved if policy says so)
        if auto_apply_low:
            sync_result = await self.syncer.apply_token_swaps(
                recommendations=recommendations,
                github_mcp=github_mcp_client,
                require_approved=True,  # still require explicit approval for auditability
                approved_key="approved",
            )
        else:
            sync_result = {
                "summary": {"applied": 0, "skipped": len(recommendations), "files_touched": 0},
                "patches": [],
                "skipped": [{"rec": r, "reason": "auto_apply_low_risk=false"} for r in recommendations],
                "pull_request": None,
            }

        patches_applied = int(sync_result.get("summary", {}).get("applied", 0))
        self.context.add_patches(sync_result.get("patches", []))

        # --- 7) metrics + export ---
        metrics = self.state.compute_metrics(
            total_findings=len(all_findings),
            recommendations=recommendations,
            patches_applied=patches_applied,
        )
        self.context.set_metrics(metrics)

        trace_path = self.context.save_session_trace()
        outputs = self.context.export_outputs()

        return {
            "status": "COMPLETED",
            "metrics": metrics,
            "sync_result": sync_result,
            "trace_path": trace_path,
            "outputs": outputs,
        }

    # ---- MCP helper adapters (version-tolerant) ----
    async def _safe_list_files(self, github: Any, repo_root: str) -> List[str]:
        fn = getattr(github, "list_files", None)
        if callable(fn):
            return await fn(repo_root)
        fn = getattr(github, "get_file_tree", None)
        if callable(fn):
            return await fn(repo_root)
        raise AttributeError("GitHub MCP client must expose list_files(...) or get_file_tree(...).")

    async def _safe_read_file(self, github: Any, path: str) -> str:
        fn = getattr(github, "read_file", None)
        if callable(fn):
            return await fn(path)
        fn = getattr(github, "get_file_content", None)
        if callable(fn):
            return await fn(path)
        raise AttributeError("GitHub MCP client must expose read_file(...) or get_file_content(...).")

    async def _safe_get_figma_tokens(self, figma: Any, figma_file_id: str) -> Dict[str, Any]:
        fn = getattr(figma, "get_tokens", None)
        if callable(fn):
            return await fn(figma_file_id)
        fn = getattr(figma, "fetch_tokens", None)
        if callable(fn):
            return await fn(figma_file_id)
        raise AttributeError("Figma MCP client must expose get_tokens(...) or fetch_tokens(...).")