import os
from datetime import datetime
from typing import Any, Dict, List, Optional

class ModernizationReportGenerator:
    """
    Generates a human-readable modernization report for each pipeline run.

    This report is intended for:
    - demo evidence
    - instructor review
    - audit trail
    - capstone documentation support
    """

    def __init__(self, reports_dir: str = "evaluation/reports"):
        self.reports_dir = reports_dir

    def generate_report(
        self,
        run_id: str,
        repo: str,
        figma_file_id: str,
        findings: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        evaluation: Dict[str, Any],
        sync_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generates a markdown modernization report and returns the file path.
        """
        os.makedirs(self.reports_dir, exist_ok=True)

        report_path = os.path.join(self.reports_dir, f"modernization_{run_id}.md")

        drift_heatmap = evaluation.get("drift_heatmap", []) or []
        token_coverage = evaluation.get("token_coverage", {}) or {}
        component_impact = evaluation.get("component_impact", []) or {}
        formal_parity = evaluation.get("formal_parity", {}) or {}
        reasoning_stats = evaluation.get("reasoning_stats", {}) or {}
        ground_truth_validation = evaluation.get("ground_truth_validation")

        sync_summary = sync_result.get("summary", {}) if sync_result else {}
        pr_payload = sync_result.get("pull_request", {}) if sync_result else {}

        lines: List[str] = []

        lines.append("# SynchroMesh Modernization Report")
        lines.append("")
        lines.append(f"**Run ID:** `{run_id}`")
        lines.append(f"**Generated At:** `{datetime.now().isoformat()}`")
        lines.append(f"**Repository:** `{repo}`")
        lines.append(f"**Figma File ID:** `{figma_file_id}`")
        lines.append("")

        lines.append("## 1. Executive Summary")
        lines.append("")
        lines.append(f"- Total drift findings: **{len(findings)}**")
        lines.append(f"- Total recommendations: **{len(recommendations)}**")
        lines.append(f"- Runtime parity score: **{metrics.get('parity_score', 0)}%**")
        lines.append(f"- Formal parity score: **{formal_parity.get('parity_score', 0)}%**")
        lines.append(f"- Applied patches: **{metrics.get('patches_applied', 0)}**")
        lines.append(f"- Fix success rate: **{metrics.get('fix_success_rate', 0)}%**")
        lines.append(f"- Pipeline status: **{metrics.get('status', 'UNKNOWN')}**")
        lines.append("")

        lines.append("## 2. Governance Summary")
        lines.append("")
        lines.append(f"- Approved changes: **{metrics.get('approved_changes_count', 0)}**")
        lines.append(f"- Approval required: **{metrics.get('approval_required_count', 0)}**")
        lines.append(f"- Blocked changes: **{metrics.get('blocked_count', 0)}**")
        lines.append("")

        risk_counts = metrics.get("risk_counts", {}) or {}
        lines.append("### Risk Distribution")
        lines.append("")
        lines.append(f"- LOW: **{risk_counts.get('LOW', 0)}**")
        lines.append(f"- MEDIUM: **{risk_counts.get('MEDIUM', 0)}**")
        lines.append(f"- HIGH: **{risk_counts.get('HIGH', 0)}**")
        lines.append(f"- UNKNOWN: **{risk_counts.get('UNKNOWN', 0)}**")
        lines.append("")

        lines.append("## 3. Design Token Coverage")
        lines.append("")
        lines.append(f"- Total available tokens: **{token_coverage.get('total_tokens_available', 0)}**")
        lines.append(f"- Tokens used in recommendations: **{token_coverage.get('tokens_used_in_recommendations', 0)}**")
        lines.append(f"- Coverage score: **{token_coverage.get('coverage_score', 0)}%**")
        used_tokens = token_coverage.get("used_tokens", []) or []
        if used_tokens:
            lines.append("")
            lines.append("Used tokens:")
            for token in used_tokens[:20]:
                lines.append(f"- `{token}`")
        lines.append("")

        lines.append("## 4. Drift Heatmap")
        lines.append("")
        if drift_heatmap:
            lines.append("| File Path | Drift Count |")
            lines.append("|---|---:|")
            for row in drift_heatmap[:20]:
                lines.append(f"| `{row.get('file_path', '')}` | {row.get('drift_count', 0)} |")
        else:
            lines.append("No drift heatmap data available.")
        lines.append("")

        lines.append("## 5. Component Impact Analysis")
        lines.append("")
        if component_impact:
            lines.append("| File Path | Drift Count | Import Count | Impact Score |")
            lines.append("|---|---:|---:|---:|")
            for row in component_impact[:20]:
                lines.append(
                    f"| `{row.get('file_path', '')}` | "
                    f"{row.get('drift_count', 0)} | "
                    f"{row.get('import_count', 0)} | "
                    f"{row.get('impact_score', 0)} |"
                )
        else:
            lines.append("No component impact data available.")
        lines.append("")

        lines.append("## 6. Explainability Metrics")
        lines.append("")
        lines.append(f"- Trace entries total: **{reasoning_stats.get('entries_total', 0)}**")
        lines.append(f"- Entries with confidence: **{reasoning_stats.get('entries_with_confidence', 0)}**")
        lines.append(f"- Entries missing confidence: **{reasoning_stats.get('entries_missing_confidence', 0)}**")
        avg_conf = reasoning_stats.get("average_confidence_by_agent", {}) or {}
        if avg_conf:
            lines.append("")
            lines.append("Average confidence by agent:")
            for agent, score in avg_conf.items():
                lines.append(f"- **{agent}**: {score}")
        lines.append("")

        lines.append("## 7. Formal Parity Metrics")
        lines.append("")
        lines.append(f"- Total components/files evaluated: **{formal_parity.get('total_components', 0)}**")
        lines.append(f"- Aligned components/files: **{formal_parity.get('aligned_components', 0)}**")
        lines.append(f"- Components/files with drift: **{formal_parity.get('components_with_drift', 0)}**")
        lines.append(f"- Unknown path findings: **{formal_parity.get('unknown_path_findings', 0)}**")
        lines.append("")

        if ground_truth_validation:
            lines.append("## 8. Ground Truth Validation")
            lines.append("")
            lines.append(f"- Accuracy: **{ground_truth_validation.get('accuracy', 0)}%**")
            lines.append(f"- Precision: **{ground_truth_validation.get('precision', 0)}%**")
            lines.append(f"- Recall: **{ground_truth_validation.get('recall', 0)}%**")
            lines.append(f"- F1 Score: **{ground_truth_validation.get('f1_score', 0)}%**")
            lines.append("")

        lines.append("## 9. Synchronization Results")
        lines.append("")
        if sync_result:
            lines.append(f"- Applied substitutions: **{sync_summary.get('applied', 0)}**")
            lines.append(f"- Skipped substitutions: **{sync_summary.get('skipped', 0)}**")
            lines.append(f"- Files touched: **{sync_summary.get('files_touched', 0)}**")
            lines.append("")
            if pr_payload:
                lines.append("### Pull Request Draft")
                lines.append("")
                lines.append(f"**Title:** {pr_payload.get('title', '')}")
                lines.append("")
                body = pr_payload.get("body", "")
                if body:
                    lines.append(body)
                    lines.append("")
        else:
            lines.append("Synchronization has not been executed yet (awaiting approval or dry run).")
            lines.append("")

        lines.append("## 10. Recommendation Sample")
        lines.append("")
        if recommendations:
            lines.append("| File | Line | Risk | Original | Proposed Token |")
            lines.append("|---|---:|---|---|---|")
            for rec in recommendations[:20]:
                lines.append(
                    f"| `{rec.get('file_path', '')}` | "
                    f"{rec.get('line', '')} | "
                    f"{rec.get('risk_level', '')} | "
                    f"`{rec.get('original_value', '')}` | "
                    f"`{rec.get('proposed_token', '')}` |"
                )
        else:
            lines.append("No recommendations generated.")
        lines.append("")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return report_path