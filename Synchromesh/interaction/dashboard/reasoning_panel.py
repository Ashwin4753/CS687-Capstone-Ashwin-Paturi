import streamlit as st

def render_agent_logs(context_store):
    st.subheader("🤖 Agent Reasoning & Audit")

    mem = context_store.shared_memory
    recs = mem.get("recommendations", []) or []

    # Run metadata (helps for report screenshots)
    with st.expander("Run Metadata", expanded=False):
        st.write(f"**Run ID:** `{mem.get('run_id', '')}`")
        st.write(f"**Repo:** `{mem.get('repo', '')}`")
        st.write(f"**Figma File ID:** `{mem.get('figma_file_id', '')}`")
        st.write(f"**Session start:** `{mem.get('session_start', '')}`")

    if not recs:
        st.info("No reasoning yet. Run the pipeline to generate recommendations.")
        return

    # Filters
    col_a, col_b = st.columns([1, 2])
    with col_a:
        risk_filter = st.multiselect(
            "Risk filter",
            options=["LOW", "MEDIUM", "HIGH"],
            default=["HIGH", "MEDIUM", "LOW"],
        )
    with col_b:
        search = st.text_input("Search (file/token/value)", "")

    risk_filter_set = {r.upper() for r in risk_filter}
    search_l = search.strip().lower()

    # Sort newest first (you can keep chronological if you prefer)
    filtered = []
    for rec in reversed(recs):
        risk = str(rec.get("risk_level", "")).upper()
        if risk and risk not in risk_filter_set:
            continue

        if search_l:
            hay = " ".join(
                [
                    str(rec.get("file_path", "")),
                    str(rec.get("proposed_token", "")),
                    str(rec.get("original_value", "")),
                    str(rec.get("replacement_text", "")),
                    str(rec.get("snippet", "")),
                ]
            ).lower()
            if search_l not in hay:
                continue

        filtered.append(rec)

    st.caption(f"Showing {len(filtered)} of {len(recs)} recommendation(s)")

    # Show latest 50 to keep UI fast
    for rec in filtered[:50]:
        file_path = rec.get("file_path", "")
        line = rec.get("line", "")
        risk = rec.get("risk_level", "?")
        cid = rec.get("change_id", "")
        approved = rec.get("approved", False)

        header = f"{risk} | {file_path}:{line} | {'✅ approved' if approved else '⏳ pending'}"
        with st.expander(header):
            if cid:
                st.write(f"**Change ID:** `{cid}`")

            st.write(f"**Original:** `{rec.get('original_value','')}`")
            st.write(f"**Proposed token:** `{rec.get('proposed_token','')}`")
            st.write(f"**Replacement:** `{rec.get('replacement_text','')}`")

            if rec.get("gate_reason"):
                st.write(f"**Gate reason:** {rec.get('gate_reason')}")

            if rec.get("risk_reason"):
                st.write(f"**Risk reason:** {rec.get('risk_reason')}")

            if rec.get("reasoning"):
                st.write(f"**Agent reasoning (ADK):** {rec.get('reasoning')}")

            if rec.get("snippet"):
                st.code(rec["snippet"], language="tsx")

            # Audit info (if present)
            if rec.get("approved_by") or rec.get("approved_at"):
                st.caption(
                    f"Approved by `{rec.get('approved_by','')}` at `{rec.get('approved_at','')}`"
                )