import streamlit as st

def render_agent_logs(context_store):
    st.subheader("🤖 Agent Reasoning Traces")
    
    # Simulating logs from the Context Store
    logs = [
        {"agent": "Archaeologist", "msg": "Detected hard-coded hex var(--color.primary.500) in Button.tsx"},
        {"agent": "Stylist", "msg": "Mapping var(--color.primary.500) to 'var(--primary-blue)' based on Figma tokens."},
        {"agent": "Syncer", "msg": "Awaiting governance approval for PR generation."}
    ]

    for log in logs:
        st.caption(f"**{log['agent']}:** {log['msg']}")