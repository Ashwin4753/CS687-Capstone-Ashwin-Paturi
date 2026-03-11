from __future__ import annotations
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from agents.archaeologist import ArchaeologistAgent
from agents.stylist import StylistAgent
from agents.syncer import SyncerAgent
from core.context_store import ContextStore
from core.state import StateManager
from evaluation.log_analyzer import LogAnalyzer
from evaluation.parity_calculator import ParityCalculator
from evaluation.validator import GroundTruthValidator
from evaluation.report_generator import ModernizationReportGenerator
from interaction.approval_gate import ApprovalGate

class SynchroMeshOrchestrator:
    """
    Central workflow coordinator for SynchroMesh.

    Pipeline:
      1) GitHub MCP lists files and reads code
      2) Archaeologist detects hard-coded drift
      3) Archaeologist computes dependency impact signals
      4) Archaeologist detects outdated frontend/backend modules
      5) Figma MCP provides authoritative design tokens
      6) Stylist maps findings to tokens and assigns risk
      7) ApprovalGate enforces governance policy
      8) Syncer applies approved LOW-risk substitutions and drafts PR info
      9) Runtime + evaluation metrics are computed and exported
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.archaeologist = ArchaeologistAgent()
        self.stylist = StylistAgent()
        self.syncer = SyncerAgent()

        trace_dir = self.config.get("metrics", {}).get("trace_path", "evaluation/traces/")
        outputs_dir = self.config.get("outputs", {}).get("base_path", "outputs/")
        self.context = ContextStore(trace_dir=trace_dir, outputs_dir=outputs_dir)

        self.state = StateManager(config_path=config_path)
        self.log_analyzer = LogAnalyzer()
        self.parity_calculator = ParityCalculator()
        self.validator = GroundTruthValidator()
        self.report_generator = ModernizationReportGenerator()

        governance = self.config.get("governance", {})
        self.approval_gate = ApprovalGate(
            auto_approve_low_risk=bool(governance.get("auto_apply_low_risk", False)),
            require_approval_for=set(
                x.upper() for x in governance.get("require_approval_for", ["MEDIUM", "HIGH"])
            ),
            max_files_per_sync=int(governance.get("max_files_per_sync", 10)),
            restricted_directories=governance.get("restricted_directories", []) or [],
        )

    async def run_sync_pipeline(
        self,
        repo_root: str,
        figma_file_id: str,
        github_mcp_client: Any,
        figma_mcp_client: Any,
        approved_changes: Optional[List[Dict[str, Any]]] = None,
        ground_truth: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a full synchronization run.
        """
        self.context.set_run_context(repo=repo_root, figma_file_id=figma_file_id)

        token_format = self.config.get("design_tokens", {}).get("format", "var(--{token})")
        pipeline_status: List[Dict[str, Any]] = []
        run_timeline: List[Dict[str, Any]] = []

        def mark_stage(name: str, status: str, duration_s: float | None = None, details: str = ""):
            pipeline_status.append(
                {
                    "stage": name,
                    "status": status,
                    "details": details,
                }
            )
            if duration_s is not None:
                run_timeline.append(
                    {
                        "stage": name,
                        "duration_s": round(duration_s, 3),
                    }
                )

        # --- 1) list files ---
        start = time.perf_counter()
        files = await self._safe_list_files(github_mcp_client, repo_root)
        code_files = [
            f for f in files
            if f.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".py"))
        ]
        mark_stage(
            "Repository Scan",
            "completed",
            time.perf_counter() - start,
            f"Discovered {len(code_files)} code files.",
        )

        # --- 2) archaeology: drift findings ---
        start = time.perf_counter()
        all_findings: List[dict] = []
        for file_path in code_files:
            content = await self._safe_read_file(github_mcp_client, file_path)
            findings = self.archaeologist.find_ghost_styles(content, file_path=file_path)
            all_findings.extend(findings)

        self.context.add_detected_drift(all_findings)
        mark_stage(
            "Drift Detection",
            "completed",
            time.perf_counter() - start,
            f"Detected {len(all_findings)} drift finding(s).",
        )

        # --- 3) archaeology: dependency analysis / impact hints ---
        start = time.perf_counter()
        dependency_analysis = await self.archaeologist.analyze_dependencies(
            github_mcp_client=github_mcp_client,
            repo_root=repo_root,
        )
        mark_stage(
            "Dependency Analysis",
            "completed",
            time.perf_counter() - start,
            "Computed lightweight dependency and impact signals.",
        )

        # --- 4) archaeology: outdated component/module audit ---
        start = time.perf_counter()
        outdated_components: List[Dict[str, Any]] = []
        detect_fn = getattr(self.archaeologist, "detect_outdated_components", None)
        if callable(detect_fn):
            try:
                outdated_components = await detect_fn(
                    github_mcp_client=github_mcp_client,
                    repo_root=repo_root,
                )
            except Exception:
                outdated_components = []

        if outdated_components:
            self.context.add_outdated_components(outdated_components)

        mark_stage(
            "Engineering Audit",
            "completed",
            time.perf_counter() - start,
            f"Detected {len(outdated_components)} outdated component/module finding(s).",
        )

        # --- 5) figma tokens ---
        start = time.perf_counter()
        tokens = await self._safe_get_figma_tokens(figma_mcp_client, figma_file_id)
        mark_stage(
            "Design Token Fetch",
            "completed",
            time.perf_counter() - start,
            f"Loaded {len(tokens) if isinstance(tokens, dict) else 0} token(s).",
        )

        # --- 6) stylist recommendations ---
        start = time.perf_counter()
        raw_recommendations = self.stylist.detect_drift(
            ghost_styles=all_findings,
            figma_tokens=tokens,
            token_format=token_format,
        )
        mark_stage(
            "Token Matching",
            "completed",
            time.perf_counter() - start,
            f"Generated {len(raw_recommendations)} recommendation(s).",
        )

        # --- 7) governance ---
        start = time.perf_counter()
        buckets = self.approval_gate.process_recommendations(raw_recommendations)

        governed_recommendations = (
            buckets.get("autonomous", [])
            + buckets.get("approval_required", [])
            + buckets.get("blocked", [])
        )

        approved_lookup = {
            (item.get("file_path"), item.get("line"), item.get("original_value")): True
            for item in (approved_changes or [])
        }

        for rec in governed_recommendations:
            key = (rec.get("file_path"), rec.get("line"), rec.get("original_value"))
            if approved_lookup.get(key, False):
                rec["approved"] = True

        approved_recommendations = [
            rec for rec in governed_recommendations if rec.get("approved", False)
        ]

        self.context.add_recommendations(governed_recommendations)
        self.context.set_approved_changes(approved_recommendations)

        approval_required = [
            rec
            for rec in governed_recommendations
            if (
                str(rec.get("risk_level", "")).upper() in {"MEDIUM", "HIGH"}
                and not rec.get("approved", False)
                and rec not in buckets.get("blocked", [])
            )
        ]

        gov_details = (
            f"Autonomous={len(buckets.get('autonomous', []))}, "
            f"Approval Required={len(buckets.get('approval_required', []))}, "
            f"Blocked={len(buckets.get('blocked', []))}"
        )
        mark_stage(
            "Governance Review",
            "completed" if not approval_required else "awaiting_approval",
            time.perf_counter() - start,
            gov_details,
        )

        # --- 8) trace logs for explainability/evaluation ---
        trace_logs = self._build_trace_logs(governed_recommendations, outdated_components)
        self.context.add_trace_logs(trace_logs)

        # --- Tier 1 feature data ---
        drift_heatmap = self._build_drift_heatmap(all_findings)
        token_coverage = self._build_token_coverage(
            figma_tokens=tokens,
            recommendations=governed_recommendations,
        )
        component_impact = self._build_component_impact(
            drift_heatmap=drift_heatmap,
            dependency_analysis=dependency_analysis,
        )

        # --- initial runtime metrics ---
        runtime_metrics = self.state.compute_metrics(
            total_findings=len(all_findings),
            recommendations=governed_recommendations,
            patches_applied=0,
            outdated_components=outdated_components,
        )

        # --- evaluation metrics ---
        formal_parity = self.parity_calculator.calculate_metrics(
            drift_report=all_findings,
            total_components=len(code_files),
            outdated_components=outdated_components,
        )

        reasoning_stats = self.log_analyzer.extract_reasoning_stats(trace_logs)

        evaluation: Dict[str, Any] = {
            "runtime_metrics": runtime_metrics,
            "formal_parity": formal_parity,
            "reasoning_stats": reasoning_stats,
            "drift_heatmap": drift_heatmap,
            "token_coverage": token_coverage,
            "component_impact": component_impact,
            "dependency_analysis": dependency_analysis,
            "outdated_components": outdated_components,
            "outdated_component_count": len(outdated_components),
            "pipeline_status": pipeline_status,
            "run_timeline": run_timeline,
        }

        if ground_truth:
            evaluation["ground_truth_validation"] = self.validator.verify_accuracy(
                agent_output=governed_recommendations,
                expected_output=ground_truth,
            )

        self.context.set_evaluation(evaluation)
        self.context.set_pipeline_status(pipeline_status)
        self.context.set_run_timeline(run_timeline)

        # --- 9) syncer execution ---
        sync_result: Dict[str, Any] = {
            "summary": {"applied": 0, "skipped": 0, "files_touched": 0},
            "patches": [],
            "skipped": [],
            "applied_recommendations": [],
            "pull_request": {},
        }

        if approved_recommendations:
            start = time.perf_counter()
            sync_result = await self.syncer.apply_token_swaps(
                recommendations=governed_recommendations,
                github_mcp=github_mcp_client,
                require_approved=True,
                approved_key="approved",
            )

            patches_applied = int(sync_result.get("summary", {}).get("applied", 0))
            self.context.add_patches(sync_result.get("patches", []))

            mark_stage(
                "Sync Execution",
                "completed",
                time.perf_counter() - start,
                f"Applied {patches_applied} approved low-risk substitution(s).",
            )
        else:
            patches_applied = 0
            if approval_required:
                mark_stage(
                    "Sync Execution",
                    "pending",
                    0.0,
                    "Waiting for approved LOW-risk changes before sync execution.",
                )
            else:
                mark_stage(
                    "Sync Execution",
                    "completed",
                    0.0,
                    "No approved LOW-risk substitutions available for execution.",
                )

        self.context.set_pipeline_status(pipeline_status)
        self.context.set_run_timeline(run_timeline)

        # --- recompute final runtime metrics ---
        runtime_metrics = self.state.compute_metrics(
            total_findings=len(all_findings),
            recommendations=governed_recommendations,
            patches_applied=patches_applied,
            outdated_components=outdated_components,
        )
        self.context.set_metrics(runtime_metrics)

        evaluation["runtime_metrics"] = runtime_metrics
        evaluation["pipeline_status"] = pipeline_status
        evaluation["run_timeline"] = run_timeline
        self.context.set_evaluation(evaluation)

        report_path = self.report_generator.generate_report(
            run_id=self.context.shared_memory.get("run_id", "unknown"),
            repo=repo_root,
            figma_file_id=figma_file_id,
            findings=all_findings,
            recommendations=governed_recommendations,
            metrics=runtime_metrics,
            evaluation=evaluation,
            sync_result=sync_result,
        )
        self.context.set_report_path(report_path)

        trace_path = self.context.save_session_trace()
        outputs = self.context.export_outputs()

        if approval_required:
            return {
                "status": "PARTIAL_COMPLETED_AWAITING_APPROVAL" if patches_applied > 0 else "AWAITING_APPROVAL",
                "message": "Some MEDIUM/HIGH recommendations still require approval.",
                "needs_approval_count": len(approval_required),
                "metrics": runtime_metrics,
                "evaluation": evaluation,
                "sync_result": sync_result,
                "trace_path": trace_path,
                "report_path": report_path,
                "outputs": outputs,
                "pipeline_status": pipeline_status,
                "run_timeline": run_timeline,
            }

        return {
            "status": "COMPLETED",
            "metrics": runtime_metrics,
            "evaluation": evaluation,
            "sync_result": sync_result,
            "trace_path": trace_path,
            "report_path": report_path,
            "outputs": outputs,
            "pipeline_status": pipeline_status,
            "run_timeline": run_timeline,
        }

    def _build_trace_logs(
        self,
        recommendations: List[Dict[str, Any]],
        outdated_components: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Builds lightweight structured trace logs for runtime explainability.
        """
        trace_logs: List[Dict[str, Any]] = []

        for rec in recommendations:
            risk = str(rec.get("risk_level", "UNKNOWN")).upper()
            confidence = 1.0 if risk == "LOW" else 0.9 if risk == "MEDIUM" else 0.7

            trace_logs.append(
                {
                    "agent_name": "Stylist",
                    "action_taken": f"generated {risk} recommendation",
                    "confidence_score": confidence,
                    "timestamp": datetime.now().isoformat(),
                    "file_path": rec.get("file_path", ""),
                    "line": rec.get("line", ""),
                    "token": rec.get("proposed_token", ""),
                }
            )

        for item in outdated_components or []:
            trace_logs.append(
                {
                    "agent_name": "Archaeologist",
                    "action_taken": "detected outdated component/module",
                    "confidence_score": item.get("confidence_score", 0.8),
                    "timestamp": datetime.now().isoformat(),
                    "file_path": item.get("file_path", ""),
                    "line": item.get("line", ""),
                    "token": item.get("type", ""),
                }
            )

        return trace_logs

    def _build_drift_heatmap(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}

        for finding in findings:
            file_path = str(finding.get("file_path", "unknown"))
            counts[file_path] = counts.get(file_path, 0) + 1

        return [
            {"file_path": file_path, "drift_count": count}
            for file_path, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
        ]

    def _build_token_coverage(
        self,
        figma_tokens: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_tokens_available = len(figma_tokens) if isinstance(figma_tokens, dict) else 0

        used_tokens = {
            rec.get("proposed_token")
            for rec in recommendations
            if rec.get("proposed_token")
            and rec.get("proposed_token") not in {"UNKNOWN_TOKEN", "N/A"}
        }

        coverage_score = 0.0
        if total_tokens_available > 0:
            coverage_score = round((len(used_tokens) / total_tokens_available) * 100, 2)

        return {
            "total_tokens_available": total_tokens_available,
            "tokens_used_in_recommendations": len(used_tokens),
            "coverage_score": coverage_score,
            "used_tokens": sorted(list(used_tokens)),
        }

    def _build_component_impact(
        self,
        drift_heatmap: List[Dict[str, Any]],
        dependency_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        reverse_import_counts = dependency_analysis.get("reverse_import_counts", {}) or {}

        impact_rows: List[Dict[str, Any]] = []
        for row in drift_heatmap:
            file_path = row.get("file_path", "")
            drift_count = int(row.get("drift_count", 0))

            file_name = file_path.split("/")[-1]
            import_count = 0
            for import_key, count in reverse_import_counts.items():
                if file_name and file_name.replace(".tsx", "").replace(".ts", "") in str(import_key):
                    import_count += int(count)

            impact_score = drift_count * max(import_count, 1)

            impact_rows.append(
                {
                    "file_path": file_path,
                    "drift_count": drift_count,
                    "import_count": import_count,
                    "impact_score": impact_score,
                }
            )

        impact_rows.sort(key=lambda item: item["impact_score"], reverse=True)
        return impact_rows

    async def _safe_list_files(self, github: Any, repo_root: str) -> List[str]:
        fn = getattr(github, "list_files", None)
        if callable(fn):
            return await fn(repo_root)

        fn = getattr(github, "get_file_tree", None)
        if callable(fn):
            return await fn(repo_root)

        raise AttributeError(
            "GitHub MCP client must expose list_files(...) or get_file_tree(...)."
        )

    async def _safe_read_file(self, github: Any, path: str) -> str:
        fn = getattr(github, "read_file", None)
        if callable(fn):
            return await fn(path)

        fn = getattr(github, "get_file_content", None)
        if callable(fn):
            return await fn(path)

        raise AttributeError(
            "GitHub MCP client must expose read_file(...) or get_file_content(...)."
        )

    async def _safe_get_figma_tokens(self, figma: Any, figma_file_id: str) -> Dict[str, Any]:
        fn = getattr(figma, "get_tokens", None)
        if callable(fn):
            return await fn(figma_file_id)

        fn = getattr(figma, "fetch_tokens", None)
        if callable(fn):
            return await fn(figma_file_id)

        raise AttributeError(
            "Figma MCP client must expose get_tokens(...) or fetch_tokens(...)."
        )