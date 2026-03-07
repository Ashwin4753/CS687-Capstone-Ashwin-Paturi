import streamlit as st


def _mini_bar(value: int, max_value: int, width: int = 16) -> str:
    if max_value <= 0:
        return ""
    filled = max(1, round((value / max_value) * width)) if value > 0 else 0
    return "█" * filled


def render_metrics(context_store):
    """
    Dashboard summary page only.
    Compact, formal, and closer to an enterprise governance dashboard.
    """
    memory = getattr(context_store, "shared_memory", {}) or {}
    metrics = memory.get("metrics", {}) or {}
    evaluation = memory.get("evaluation", {}) or {}

    st.markdown("### Dashboard")

    if not metrics:
        st.info("No metrics yet. Run the pipeline to generate evaluation results.")
        return

    parity = metrics.get("parity_score", 0)
    target = metrics.get("target_parity_score", 95.0)
    risk_counts = metrics.get("risk_counts", {}) or {}

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Design–Code Parity", f"{parity}%")
    top2.metric("Findings", metrics.get("total_findings", 0))
    top3.metric("Applied Patches", metrics.get("patches_applied", 0))
    top4.metric("Fix Success", f"{metrics.get('fix_success_rate', 0)}%")

    st.caption(
        f"Target parity threshold: {target}% | "
        f"Status: {metrics.get('status', 'UNKNOWN')}"
    )

    progress = 0.0
    if target > 0:
        progress = min(parity / target, 1.0)
    st.progress(progress)

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

        st.markdown("#### Pipeline Statistics")
        st.write(f"**Drift Instances:** {metrics.get('drift_instances', 0)}")
        st.write(f"**Recommendations:** {metrics.get('recommendations_total', 0)}")
        st.write(f"**Run Timestamp:** `{metrics.get('timestamp', '')}`")

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