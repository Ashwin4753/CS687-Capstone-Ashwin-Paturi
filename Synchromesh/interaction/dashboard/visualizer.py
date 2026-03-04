import streamlit as st

def render_metrics(context_store):
    st.subheader("📊 Modernization Metrics")

    metrics = context_store.shared_memory.get("metrics", {}) or {}

    if not metrics:
        st.info("No metrics yet. Run the pipeline to generate evaluation results.")
        return

    parity = metrics.get("parity_score", 0)
    target = metrics.get("target_parity_score", 95.0)

    st.metric(
        label="Design–Code Parity",
        value=f"{parity}%",
        delta=f"Target {target}%",
    )

    # Risk distribution
    risk_counts = metrics.get("risk_counts", {})

    col1, col2, col3 = st.columns(3)

    col1.metric("LOW Risk", risk_counts.get("LOW", 0))
    col2.metric("MEDIUM Risk", risk_counts.get("MEDIUM", 0))
    col3.metric("HIGH Risk", risk_counts.get("HIGH", 0))

    st.divider()

    # Pipeline statistics
    st.subheader("Pipeline Statistics")

    colA, colB, colC = st.columns(3)

    colA.metric("Total Findings", metrics.get("total_findings", 0))
    colB.metric("Drift Instances", metrics.get("drift_instances", 0))
    colC.metric("Applied Patches", metrics.get("patches_applied", 0))

    st.caption(f"Pipeline Status: {metrics.get('status', 'UNKNOWN')}")

    # Optional progress bar (nice for demo)
    progress = min(parity / target, 1.0) if target else 0
    st.progress(progress)

    # Optional simple visualization
    if risk_counts:
        st.subheader("Risk Distribution")
        chart_data = {
            "LOW": risk_counts.get("LOW", 0),
            "MEDIUM": risk_counts.get("MEDIUM", 0),
            "HIGH": risk_counts.get("HIGH", 0),
        }
        st.bar_chart(chart_data)