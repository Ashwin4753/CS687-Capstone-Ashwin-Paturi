import streamlit as st

def render_agent_logs(context_store):
    st.subheader("🤖 Agent Reasoning Traces")
    
    # Simulating logs from the Context Store
    logs = [
        {"agent": "Archaeologist", "msg": "Detected hard-coded hex #3b82f6 in Button.tsx"},
        {"agent": "Stylist", "msg": "Mapping #3b82f6 to 'var(--primary-blue)' based on Figma tokens."},
        {"agent": "Syncer", "msg": "Awaiting governance approval for PR generation."}
    ]

    for log in logs:
        st.caption(f"**{log['agent']}:** {log['msg']}")