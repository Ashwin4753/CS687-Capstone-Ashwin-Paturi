import streamlit as st
from core.orchestrator import SynchroMeshOrchestrator
from interaction.dashboard.visualizer import render_metrics
from interaction.dashboard.reasoning_panel import render_agent_logs
from interaction.dashboard.governance_ui import render_approval_queue

st.set_page_config(page_title="SynchroMesh Orchestrator", layout="wide")

def main():
    st.title("🕸️ SynchroMesh: Agentic Design-Code Orchestrator")
    
    # Sidebar Configuration
    st.sidebar.header("Configuration")
    repo_url = st.sidebar.text_input("GitHub Repo", "owner/legacy-app")
    figma_id = st.sidebar.text_input("Figma File ID", "v0_design_system")
    
    # Initialize Orchestrator
    orchestrator = SynchroMeshOrchestrator()

    # Layout Columns
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🚀 Start Modernization Pipeline"):
            with st.spinner("Agents are analyzing drift..."):
                # Trigger the Core Pipeline
                status = orchestrator.run_sync_pipeline(repo_url, figma_id)
                st.session_state['pipeline_status'] = status
        
        # Render the Approval Queue (HITL)
        render_approval_queue(orchestrator.context)

    with col2:
        # Render Real-time Metrics & Parity
        render_metrics(orchestrator.context)
        # Render Agent Reasoning
        render_agent_logs(orchestrator.context)

if __name__ == "__main__":
    main()