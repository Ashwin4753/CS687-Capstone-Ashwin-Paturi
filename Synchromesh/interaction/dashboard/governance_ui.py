import streamlit as st

from interaction.approval_gate import ApprovalGate

def render_approval_queue(context_store, settings: dict | None = None):
    """
    Governance UI:
      - Uses ApprovalGate to bucket recommendations
      - Allows selecting approvals (change_id)
      - Stores approved IDs in st.session_state["approved_change_ids"]
    """
    st.subheader("🛡️ Governance Gate")

    recs = context_store.shared_memory.get("recommendations", []) or []
    if not recs:
        st.write("No pending recommendations.")
        return

    # Pull governance settings (optional)
    settings = settings or {}
    gov = settings.get("governance", {}) if isinstance(settings, dict) else {}
    auto_approve_low = bool(gov.get("auto_apply_low_risk", False))
    require_approval_for = set([x.upper() for x in gov.get("require_approval_for", ["MEDIUM", "HIGH"])])
    max_files = int(gov.get("max_files_per_sync", 10))
    restricted_dirs = gov.get("restricted_directories", []) or []

    gate = ApprovalGate(
        auto_approve_low_risk=auto_approve_low,
        require_approval_for=require_approval_for,
        max_files_per_sync=max_files,
        restricted_directories=restricted_dirs,
    )

    buckets = gate.process_recommendations(recs)

    # Make sure we have a place to store approvals
    if "approved_change_ids" not in st.session_state:
        st.session_state["approved_change_ids"] = set()

    # Summary
    st.caption(
        f"Autonomous: {len(buckets['autonomous'])} | "
        f"Approval required: {len(buckets['approval_required'])} | "
        f"Blocked: {len(buckets['blocked'])}"
    )

    # Autonomous bucket (LOW-risk, possibly auto-approved)
    if buckets["autonomous"]:
        with st.expander(f"✅ Autonomous (auto-approved) — {len(buckets['autonomous'])} change(s)", expanded=False):
            for rec in buckets["autonomous"][:50]:
                cid = rec.get("change_id")
                st.write(f"- `{cid}` | {rec.get('file_path','')}:{rec.get('line','')} → {rec.get('proposed_token','')}")
                # Ensure auto-approved items are included in approved ids (so rerun can apply)
                st.session_state["approved_change_ids"].add(cid)

            st.caption("These are LOW-risk substitutions approved automatically by policy.")

    # Blocked bucket
    if buckets["blocked"]:
        with st.expander(f"⛔ Blocked — {len(buckets['blocked'])} change(s)", expanded=False):
            for rec in buckets["blocked"][:50]:
                title = f"{rec.get('file_path','')}:{rec.get('line','')} — {rec.get('original_value','')}"
                st.write(f"**{title}**")
                st.caption(rec.get("gate_reason", "Blocked by policy."))

    # Approval required bucket
    approval_required = buckets["approval_required"]

    st.caption(f"Approval required: {len(approval_required)} item(s)")

    if not approval_required:
        st.success("No items require approval. Pipeline can proceed.")
        st.info(f"Selected approvals: {len(st.session_state['approved_change_ids'])}")
        return

    # Render approval required items with checkboxes
    for i, rec in enumerate(approval_required):
        cid = rec.get("change_id")
        title = (
            f"{rec.get('file_path','')}:{rec.get('line','')} — "
            f"{rec.get('original_value','')} → {rec.get('proposed_token','')}"
        )

        with st.expander(title):
            st.write(f"**Risk Level:** {rec.get('risk_level')}")
            if rec.get("gate_reason"):
                st.write(f"**Gate reason:** {rec.get('gate_reason')}")
            if rec.get("risk_reason"):
                st.write(f"**Risk reason:** {rec.get('risk_reason')}")
            if rec.get("reasoning"):
                st.write(f"**Reasoning:** {rec.get('reasoning')}")
            if rec.get("snippet"):
                st.code(rec["snippet"], language="tsx")

            checked = st.checkbox("Approve this change", key=f"approve_{cid}_{i}")
            if checked:
                st.session_state["approved_change_ids"].add(cid)
            else:
                st.session_state["approved_change_ids"].discard(cid)

    st.info(f"Selected approvals: {len(st.session_state['approved_change_ids'])}")