import streamlit as st

def _risk_badge(risk: str) -> str:
    risk = str(risk).upper()
    if risk == "LOW":
        return "🟢 LOW"
    if risk == "MEDIUM":
        return "🟠 MEDIUM"
    if risk == "HIGH":
        return "🔴 HIGH"
    return risk

def _agent_badge(agent_name: str) -> str:
    name = str(agent_name).strip().lower()
    if name == "archaeologist":
        return "🧭 Archaeologist Agent"
    if name == "stylist":
        return "🎨 Stylist Agent"
    if name == "syncer":
        return "🔁 Syncer Agent"
    return f"🤖 {agent_name}"

def render_agent_logs(context_store):
    """
    Dedicated review logs page.
    Formal and segmented layout for run metadata, recommendation reasoning,
    structured trace logs, and architecture context.
    """
    st.markdown("### Review Logs")

    memory = getattr(context_store, "shared_memory", {}) or {}
    recommendations = memory.get("recommendations", []) or []
    trace_logs = memory.get("trace_logs", []) or []
    evaluation = memory.get("evaluation", {}) or {}
    reasoning_stats = evaluation.get("reasoning_stats", {}) or {}
    pipeline_status = memory.get("pipeline_status", []) or []
    run_timeline = memory.get("run_timeline", []) or []

    if not recommendations and not trace_logs:
        st.info("No reasoning or trace data available yet. Run the pipeline to generate audit evidence.")
        return

    top_cols = st.columns([1, 1, 1, 1])
    top_cols[0].metric("Recommendations", len(recommendations))
    top_cols[1].metric("Trace Logs", len(trace_logs))
    top_cols[2].metric("Run ID", memory.get("run_id", "—"))
    top_cols[3].metric("Repo", memory.get("repo", "—"))

    meta_tab, rec_tab, trace_tab, arch_tab = st.tabs(
        ["Run Summary", "Recommendation Reasoning", "Structured Trace Logs", "Architecture"]
    )

    with meta_tab:
        left, right = st.columns([1.2, 1])

        with left:
            st.markdown("#### Run Metadata")
            st.write(f"**Run ID:** `{memory.get('run_id', '')}`")
            st.write(f"**Repo:** `{memory.get('repo', '')}`")
            st.write(f"**Figma File ID:** `{memory.get('figma_file_id', '')}`")
            st.write(f"**Session Start:** `{memory.get('session_start', '')}`")
            if memory.get("run_start"):
                st.write(f"**Run Start:** `{memory.get('run_start', '')}`")
            if memory.get("report_path"):
                st.write(f"**Report Path:** `{memory.get('report_path', '')}`")

        with right:
            st.markdown("#### Explainability Summary")
            if reasoning_stats:
                st.write(f"**Trace entries total:** {reasoning_stats.get('entries_total', 0)}")
                st.write(f"**Entries with confidence:** {reasoning_stats.get('entries_with_confidence', 0)}")
                st.write(f"**Entries missing confidence:** {reasoning_stats.get('entries_missing_confidence', 0)}")

                avg_conf = reasoning_stats.get("average_confidence_by_agent", {}) or {}
                if avg_conf:
                    st.markdown("**Average confidence by agent**")
                    for agent, score in avg_conf.items():
                        st.write(f"- **{agent}**: {score}")

                action_counts = reasoning_stats.get("action_counts_by_agent", {}) or {}
                if action_counts:
                    st.markdown("**Action counts by agent**")
                    for agent, count in action_counts.items():
                        st.write(f"- **{agent}**: {count}")

        if pipeline_status:
            st.markdown("#### Pipeline Status")
            for item in pipeline_status:
                st.write(f"- **{item.get('stage', '')}** — {item.get('status', '')} — {item.get('details', '')}")

        if run_timeline:
            st.markdown("#### Run Timeline")
            for item in run_timeline:
                st.write(f"- **{item.get('stage', '')}** — {item.get('duration_s', 0)}s")

    with rec_tab:
        if not recommendations:
            st.info("No governed recommendations available.")
        else:
            filter_col, search_col = st.columns([1, 2])

            with filter_col:
                risk_filter = st.multiselect(
                    "Risk Filter",
                    options=["LOW", "MEDIUM", "HIGH"],
                    default=["HIGH", "MEDIUM", "LOW"],
                    key="reasoning_risk_filter_ui",
                )

            with search_col:
                search = st.text_input(
                    "Search recommendations (file / token / value / reasoning)",
                    "",
                    key="reasoning_search_ui",
                )

            if not risk_filter:
                risk_filter = ["LOW", "MEDIUM", "HIGH"]

            risk_filter_set = {risk.upper() for risk in risk_filter}
            search_l = search.strip().lower()

            filtered = []
            for rec in reversed(recommendations):
                risk = str(rec.get("risk_level", "")).upper()
                if risk and risk not in risk_filter_set:
                    continue

                if search_l:
                    haystack = " ".join(
                        [
                            str(rec.get("file_path", "")),
                            str(rec.get("proposed_token", "")),
                            str(rec.get("original_value", "")),
                            str(rec.get("replacement_text", "")),
                            str(rec.get("snippet", "")),
                            str(rec.get("reasoning", "")),
                        ]
                    ).lower()
                    if search_l not in haystack:
                        continue

                filtered.append(rec)

            st.caption(f"Showing {len(filtered)} of {len(recommendations)} recommendation(s)")

            for rec in filtered[:50]:
                file_path = rec.get("file_path", "")
                line = rec.get("line", "")
                risk = rec.get("risk_level", "?")
                change_id = rec.get("change_id", "")
                approved = bool(rec.get("approved", False))

                header = (
                    f"{_risk_badge(risk)} | "
                    f"{file_path}:{line} | "
                    f"{'✅ approved' if approved else '⏳ pending'}"
                )

                with st.expander(header):
                    top_info_left, top_info_right = st.columns([1, 1])

                    with top_info_left:
                        if change_id:
                            st.write(f"**Change ID:** `{change_id}`")
                        st.write(f"**Original:** `{rec.get('original_value', '')}`")
                        st.write(f"**Proposed Token:** `{rec.get('proposed_token', '')}`")
                        st.write(f"**Replacement:** `{rec.get('replacement_text', '')}`")

                    with top_info_right:
                        if rec.get("token_found") is not None:
                            st.write(f"**Token Found:** {rec.get('token_found')}")
                        if rec.get("confidence_score") is not None:
                            st.write(f"**Confidence Score:** {rec.get('confidence_score')}")
                        if rec.get("gate_reason"):
                            st.write(f"**Gate Reason:** {rec.get('gate_reason')}")
                        if rec.get("risk_reason"):
                            st.write(f"**Risk Reason:** {rec.get('risk_reason')}")

                    if rec.get("reasoning"):
                        st.markdown(f"**{_agent_badge('Stylist')} Reasoning**")
                        st.write(rec.get("reasoning"))

                    if rec.get("snippet"):
                        st.markdown("**Code Snippet**")
                        st.code(rec["snippet"], language="tsx")

                    if rec.get("approved_by") or rec.get("approved_at"):
                        st.caption(
                            f"Approved by `{rec.get('approved_by', '')}` at `{rec.get('approved_at', '')}`"
                        )

    with trace_tab:
        if not trace_logs:
            st.info("No structured trace logs available for this run.")
        else:
            st.caption(f"Showing {len(trace_logs)} trace log entrie(s)")

            for entry in reversed(trace_logs[:100]):
                agent_name = entry.get("agent_name", "unknown")
                action = entry.get("action_taken", "")
                timestamp = entry.get("timestamp", "")
                confidence = entry.get("confidence_score", "")

                header = f"{_agent_badge(agent_name)} | {action} | {timestamp}"

                with st.expander(header):
                    left, right = st.columns([1, 1])

                    with left:
                        st.write(f"**Agent:** {agent_name}")
                        st.write(f"**Action:** {action}")
                        if confidence != "":
                            st.write(f"**Confidence:** {confidence}")

                    with right:
                        if entry.get("file_path"):
                            st.write(f"**File:** `{entry.get('file_path')}`")
                        if entry.get("line") not in (None, ""):
                            st.write(f"**Line:** {entry.get('line')}")
                        if entry.get("token"):
                            st.write(f"**Token:** `{entry.get('token')}`")
                        if timestamp:
                            st.write(f"**Timestamp:** `{timestamp}`")

    with arch_tab:
        st.markdown("#### System Architecture")
        st.code(
            """SynchroMesh
├── Orchestrator
│   ├── Archaeologist Agent
│   ├── Stylist Agent
│   └── Syncer Agent
├── Governance Layer
├── MCP Integration
│   ├── Figma MCP
│   └── GitHub MCP
└── Evaluation + Reporting""",
            language="text",
        )
        st.caption("This view is included to support architecture-level demo and Q&A discussion.")