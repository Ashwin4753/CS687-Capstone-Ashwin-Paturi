import streamlit as st

def render_approval_queue(context_store):
    st.subheader("🛡️ Governance Gate")
    recs = context_store.shared_memory.get("recommendations", [])

    if not recs:
        st.write("No pending recommendations.")
        return

    for i, rec in enumerate(recs):
        with st.expander(f"Change {i+1}: {rec['original_value']} → {rec['proposed_token']}"):
            st.write(f"**Risk Level:** {rec['risk_level']}")
            st.write(f"**Reasoning:** {rec['reasoning']}")
            
            col_a, col_b = st.columns(2)
            if col_a.button("✅ Approve", key=f"app_{i}"):
                st.success("Change authorized for Syncer.")
            if col_b.button("❌ Reject", key=f"rej_{i}"):
                st.error("Change dismissed.")