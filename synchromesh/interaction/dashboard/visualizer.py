import math
import streamlit as st
from typing import Any, Dict, List

def _mini_bar(value: int, max_value: int, width: int = 16) -> str:
    if max_value <= 0:
        return ""
    filled = max(1, round((value / max_value) * width)) if value > 0 else 0
    return "█" * filled

def _badge(label: str) -> str:
    return f"<span class='syn-chip'>{label}</span>"

def _stage_icon(status: str) -> str:
    status = str(status).lower()
    if status == "completed":
        return "✔"
    if status in {"awaiting_approval", "pending"}:
        return "⚠"
    if status == "failed":
        return "✖"
    return "•"

def _render_pipeline_grid(pipeline_status: List[Dict[str, Any]], cols_per_row: int = 3) -> None:
    """
    Render all pipeline stages in a wrapped grid so no stage is hidden.
    """
    if not pipeline_status:
        st.info("Pipeline status will appear here after execution.")
        return

    total = len(pipeline_status)
    rows = math.ceil(total / cols_per_row)

    for row_idx in range(rows):
        row_items = pipeline_status[row_idx * cols_per_row : (row_idx + 1) * cols_per_row]
        cols = st.columns(cols_per_row)

        for col_idx in range(cols_per_row):
            with cols[col_idx]:
                if col_idx < len(row_items):
                    stage = row_items[col_idx]
                    st.markdown(
                        f"""
                        <div class="syn-card" style="padding:0.85rem 0.9rem; min-height: 120px;">
                            <div class="syn-card-title" style="font-size:0.98rem;">
                                {_stage_icon(stage.get('status', ''))} {stage.get('stage', '')}
                            </div>
                            <div class="syn-card-subtitle" style="margin-bottom:0;">
                                {stage.get('details', '')}
                            </div>
                            <div style="margin-top:0.45rem; color:#5f6f84; font-size:0.82rem; font-weight:700;">
                                Status: {str(stage.get('status', '')).replace('_', ' ').title()}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.empty()

def render_metrics(context_store):
    """
    Dashboard summary page.
    Enterprise-style overview with pipeline, governance, audit, and evaluation signals.
    """
    memory = getattr(context_store, "shared_memory", {}) or {}
    metrics = memory.get("metrics", {}) or {}
    evaluation = memory.get("evaluation", {}) or {}
    trace_logs = memory.get("trace_logs", []) or []
    pipeline_status = memory.get("pipeline_status", []) or []
    run_timeline = memory.get("run_timeline", []) or []
    outdated_components = memory.get("outdated_components", []) or []

    st.markdown("### Dashboard")

    if not metrics:
        st.info("No metrics yet. Run the pipeline to generate evaluation results.")
        return

    parity = metrics.get("parity_score", 0)
    target = metrics.get("target_parity_score", 95.0)
    risk_counts = metrics.get("risk_counts", {}) or {}

    top1, top2, top3, top4, top5 = st.columns(5)
    top1.metric("Design–Code Parity", f"{parity}%")
    top2.metric("Findings", metrics.get("total_findings", 0))
    top3.metric("Applied Patches", metrics.get("patches_applied", 0))
    top4.metric("Fix Success", f"{metrics.get('fix_success_rate', 0)}%")
    top5.metric("Outdated Modules", metrics.get("outdated_component_count", 0))

    st.caption(
        f"Target parity threshold: {target}% | "
        f"Status: {metrics.get('status', 'UNKNOWN')}"
    )

    progress = 0.0
    if target > 0:
        progress = min(parity / target, 1.0)
    st.progress(progress)

    st.divider()
    st.markdown("### Pipeline Visualization")
    _render_pipeline_grid(pipeline_status, cols_per_row=3)

    left, right = st.columns([1.15, 1])

    with left:
        st.markdown("#### Risk Distribution")
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("LOW", risk_counts.get("LOW", 0))
        rc2.metric("MEDIUM", risk_counts.get("MEDIUM", 0))
        rc3.metric("HIGH", risk_counts.get("HIGH", 0))

        if risk_counts:
            st.bar_chart(
                {
                    "LOW": risk_counts.get("LOW", 0),
                    "MEDIUM": risk_counts.get("MEDIUM", 0),
                    "HIGH": risk_counts.get("HIGH", 0),
                }
            )

    with right:
        st.markdown("#### Governance Snapshot")
        gc1, gc2, gc3 = st.columns(3)
        gc1.metric("Approved", metrics.get("approved_changes_count", 0))
        gc2.metric("Needs Approval", metrics.get("approval_required_count", 0))
        gc3.metric("Blocked", metrics.get("blocked_count", 0))

        st.markdown("#### Safety")
        st.write("**Autonomy Level:** Bounded")
        st.write(
            f"**Human Approval Required:** {'Yes' if metrics.get('approval_required_count', 0) > 0 else 'No'}"
        )
        st.write(f"**Run Timestamp:** `{metrics.get('timestamp', '')}`")

    st.divider()
    st.markdown("### Agent Activity Feed")
    if trace_logs:
        for entry in list(reversed(trace_logs[-8:])):
            agent = entry.get("agent_name", "unknown")
            action = entry.get("action_taken", "")
            file_path = entry.get("file_path", "")
            token = entry.get("token", "")
            line = entry.get("line", "")
            st.write(
                f"**[{agent}]** {action}"
                + (f" — `{file_path}`" if file_path else "")
                + (f" line {line}" if line not in ("", None) else "")
                + (f" — `{token}`" if token else "")
            )
    else:
        st.info("Agent activity feed will appear after a run.")

    if evaluation:
        st.divider()
        st.markdown("### Evaluation & Tier 1 Insights")

        formal_parity = evaluation.get("formal_parity", {}) or {}
        token_coverage = evaluation.get("token_coverage", {}) or {}
        reasoning_stats = evaluation.get("reasoning_stats", {}) or {}
        drift_heatmap = evaluation.get("drift_heatmap", []) or []
        component_impact = evaluation.get("component_impact", []) or []
        ground_truth = evaluation.get("ground_truth_validation", {}) or {}

        i1, i2, i3 = st.columns(3)
        i1.metric("Formal Parity", f"{formal_parity.get('parity_score', 0)}%")
        i2.metric("Token Coverage", f"{token_coverage.get('coverage_score', 0)}%")
        i3.metric("Trace Entries", reasoning_stats.get("entries_total", 0))

        if token_coverage:
            st.caption(
                f"Tokens used: {token_coverage.get('tokens_used_in_recommendations', 0)} / "
                f"{token_coverage.get('total_tokens_available', 0)} available"
            )

        left_insight, right_insight = st.columns([1, 1])

        with left_insight:
            if drift_heatmap:
                st.markdown("#### Drift Hotspots")
                max_drift = max(int(row.get("drift_count", 0)) for row in drift_heatmap[:10]) if drift_heatmap else 0
                for row in drift_heatmap[:8]:
                    file_path = row.get("file_path", "unknown")
                    drift_count = int(row.get("drift_count", 0))
                    bar = _mini_bar(drift_count, max_drift)
                    st.write(f"`{file_path}`  {bar}  ({drift_count})")

            if reasoning_stats:
                st.markdown("#### Explainability Snapshot")
                st.write(f"**With confidence:** {reasoning_stats.get('entries_with_confidence', 0)}")
                st.write(f"**Missing confidence:** {reasoning_stats.get('entries_missing_confidence', 0)}")

                avg_conf = reasoning_stats.get("average_confidence_by_agent", {}) or {}
                if avg_conf:
                    for agent, score in avg_conf.items():
                        st.write(f"**{agent}:** {score}")

        with right_insight:
            if component_impact:
                st.markdown("#### Component Impact Ranking")
                for row in component_impact[:8]:
                    st.write(
                        f"`{row.get('file_path', '')}` — "
                        f"impact={row.get('impact_score', 0)}, "
                        f"drift={row.get('drift_count', 0)}, "
                        f"imports={row.get('import_count', 0)}"
                    )

            if ground_truth:
                st.markdown("#### Ground Truth Validation")
                gt1, gt2 = st.columns(2)
                gt3, gt4 = st.columns(2)
                gt1.metric("Accuracy", f"{ground_truth.get('accuracy', 0)}%")
                gt2.metric("Precision", f"{ground_truth.get('precision', 0)}%")
                gt3.metric("Recall", f"{ground_truth.get('recall', 0)}%")
                gt4.metric("F1 Score", f"{ground_truth.get('f1_score', 0)}%")

    st.divider()
    st.markdown("### Engineering Modernization Audit")
    if outdated_components:
        frontend = [
            item for item in outdated_components
            if str(item.get("type", "")).upper() == "OUTDATED_FRONTEND_COMPONENT"
        ]
        backend = [
            item for item in outdated_components
            if str(item.get("type", "")).upper() == "OUTDATED_BACKEND_MODULE"
        ]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Audit Findings", len(outdated_components))
        c2.metric("Frontend", len(frontend))
        c3.metric("Backend", len(backend))

        left_audit, right_audit = st.columns(2)

        with left_audit:
            st.markdown("#### Frontend")
            if frontend:
                for item in frontend[:8]:
                    st.write(
                        f"- `{item.get('file_path', '')}` — {item.get('reason', '')} "
                        f"({item.get('severity', '')})"
                    )
            else:
                st.caption("No outdated frontend findings.")

        with right_audit:
            st.markdown("#### Backend")
            if backend:
                for item in backend[:8]:
                    st.write(
                        f"- `{item.get('file_path', '')}` — {item.get('reason', '')} "
                        f"({item.get('severity', '')})"
                    )
            else:
                st.caption("No outdated backend findings.")
    else:
        st.info("No engineering modernization audit findings yet.")

    st.divider()
    st.markdown("### Run Timeline")
    if run_timeline:
        for item in run_timeline:
            st.write(f"**{item.get('stage', '')}** — {item.get('duration_s', 0)}s")
    else:
        st.info("Timeline appears after a completed run.")