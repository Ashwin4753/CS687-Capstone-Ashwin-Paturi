from typing import Optional
import streamlit as st

from interaction.approval_gate import ApprovalGate

def _risk_badge(risk: str) -> str:
    risk = str(risk).upper()
    if risk == "LOW":
        return "🟢 LOW"
    if risk == "MEDIUM":
        return "🟠 MEDIUM"
    if risk == "HIGH":
        return "🔴 HIGH"
    return risk

def render_approval_queue(context_store, settings: Optional[dict] = None):
    """
    Detailed governance review module.

    Shown below the main content for the dashboard/detected drift sections.
    """
    st.markdown("### Governance Review")

    memory = getattr(context_store, "shared_memory", {}) or {}
    recommendations = memory.get("recommendations", []) or []

    if not recommendations:
        st.info("No governed recommendations available yet.")
        return

    settings = settings or {}
    governance = settings.get("governance", {}) if isinstance(settings, dict) else {}

    auto_approve_low = bool(governance.get("auto_apply_low_risk", False))
    require_approval_for = {
        x.upper() for x in governance.get("require_approval_for", ["MEDIUM", "HIGH"])
    }
    max_files = int(governance.get("max_files_per_sync", 10))
    restricted_dirs = governance.get("restricted_directories", []) or []

    gate = ApprovalGate(
        auto_approve_low_risk=auto_approve_low,
        require_approval_for=require_approval_for,
        max_files_per_sync=max_files,
        restricted_directories=restricted_dirs,
    )

    buckets = gate.process_recommendations(recommendations)

    if "approved_change_ids" not in st.session_state:
        st.session_state["approved_change_ids"] = set()

    # Governance policy viewer
    with st.expander("Governance Policy Viewer", expanded=False):
        st.write(f"**Auto apply LOW risk:** {auto_approve_low}")
        st.write(f"**Approval required for:** {sorted(require_approval_for)}")
        st.write(f"**Max files per sync:** {max_files}")
        st.write("**Restricted directories:**")
        if restricted_dirs:
            for item in restricted_dirs:
                st.write(f"- `{item}`")
        else:
            st.caption("No restricted directories configured.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Autonomous", len(buckets["autonomous"]))
    c2.metric("Needs Approval", len(buckets["approval_required"]))
    c3.metric("Blocked", len(buckets["blocked"]))

    st.caption(
        f"Policy: auto_apply_low_risk={auto_approve_low} | "
        f"approval_required={sorted(require_approval_for)} | "
        f"max_files_per_sync={max_files}"
    )

    review_tabs = st.tabs(["Needs Approval", "Blocked", "Autonomous"])

    with review_tabs[0]:
        approval_required = buckets["approval_required"]

        if not approval_required:
            st.success("No items currently require approval.")
        else:
            st.caption(f"{len(approval_required)} item(s) currently require review.")

            for index, rec in enumerate(approval_required[:50]):
                change_id = rec.get("change_id")
                title = (
                    f"{_risk_badge(rec.get('risk_level', ''))} | "
                    f"{rec.get('file_path', '')}:{rec.get('line', '')} | "
                    f"{rec.get('proposed_token', '')}"
                )

                with st.expander(title):
                    if change_id:
                        st.write(f"**Change ID:** `{change_id}`")

                    st.write(f"**Original value:** `{rec.get('original_value', '')}`")
                    st.write(f"**Suggested token:** `{rec.get('proposed_token', '')}`")
                    st.write(f"**Suggested replacement:** `{rec.get('replacement_text', '')}`")

                    if rec.get("confidence_score") is not None:
                        st.write(f"**Confidence score:** {rec.get('confidence_score')}")

                    if rec.get("gate_reason"):
                        st.write(f"**Gate reason:** {rec.get('gate_reason')}")

                    if rec.get("risk_reason"):
                        st.write(f"**Risk reason:** {rec.get('risk_reason')}")

                    if rec.get("reasoning"):
                        st.write(f"**Reasoning:** {rec.get('reasoning')}")

                    if rec.get("snippet"):
                        st.code(rec["snippet"], language="tsx")

                    default_checked = bool(change_id in st.session_state["approved_change_ids"]) or bool(
                        rec.get("approved", False)
                    )

                    checked = st.checkbox(
                        "Mark this change for approval",
                        value=default_checked,
                        key=f"gov_review_checkbox_{change_id}_{index}",
                    )

                    if change_id:
                        if checked:
                            st.session_state["approved_change_ids"].add(change_id)
                        else:
                            st.session_state["approved_change_ids"].discard(change_id)

    with review_tabs[1]:
        blocked = buckets["blocked"]

        if not blocked:
            st.info("No blocked items in this run.")
        else:
            st.warning(f"{len(blocked)} change(s) are blocked by governance policy.")

            for rec in blocked[:50]:
                title = (
                    f"{rec.get('file_path', '')}:{rec.get('line', '')} — "
                    f"{rec.get('original_value', '')}"
                )
                with st.expander(title):
                    if rec.get("change_id"):
                        st.write(f"**Change ID:** `{rec.get('change_id')}`")
                    st.write(f"**Risk:** {_risk_badge(rec.get('risk_level', ''))}")
                    st.write(f"**Gate reason:** {rec.get('gate_reason', 'Blocked by policy.')}")
                    if rec.get("snippet"):
                        st.code(rec["snippet"], language="tsx")

    with review_tabs[2]:
        autonomous = buckets["autonomous"]

        if not autonomous:
            st.info("No autonomous items in this run.")
        else:
            st.success(f"{len(autonomous)} low-risk change(s) are auto-approved by policy.")

            for rec in autonomous[:50]:
                change_id = rec.get("change_id")
                with st.expander(
                    f"{rec.get('file_path', '')}:{rec.get('line', '')} → {rec.get('proposed_token', '')}"
                ):
                    if change_id:
                        st.write(f"**Change ID:** `{change_id}`")
                        st.session_state["approved_change_ids"].add(change_id)

                    st.write(f"**Original value:** `{rec.get('original_value', '')}`")
                    st.write(f"**Replacement:** `{rec.get('replacement_text', '')}`")
                    st.write(f"**Risk:** {_risk_badge(rec.get('risk_level', ''))}")

                    if rec.get("confidence_score") is not None:
                        st.write(f"**Confidence score:** {rec.get('confidence_score')}")

                    if rec.get("reasoning"):
                        st.write(f"**Reasoning:** {rec.get('reasoning')}")

                    if rec.get("snippet"):
                        st.code(rec["snippet"], language="tsx")

    st.info(f"Selected approvals: {len(st.session_state['approved_change_ids'])}")