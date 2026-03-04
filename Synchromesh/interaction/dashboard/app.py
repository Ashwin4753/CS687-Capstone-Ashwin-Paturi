import os
import asyncio
import streamlit as st

from core.orchestrator import SynchroMeshOrchestrator
from integration.github_mcp_client import GitHubMCPClient
from integration.figma_mcp_client import FigmaMCPClient
from interaction.dashboard.visualizer import render_metrics
from interaction.dashboard.reasoning_panel import render_agent_logs
from interaction.dashboard.governance_ui import render_approval_queue

st.set_page_config(page_title="SynchroMesh Orchestrator", layout="wide")

def _run_async(coro):
    """
    Streamlit-safe async runner.

    Avoids: 'asyncio.run() cannot be called from a running event loop'
    """
    try:
        return asyncio.run(coro)
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

# --------- Mock Clients (offline demo mode) ----------
class MockFigmaClient:
    async def get_tokens(self, figma_file_id: str):
        return {
            "color.primary.500": "#3b82f6",
            "color.white": "#ffffff",
            "spacing.2": "8px",
            "spacing.3": "12px",
        }

class MockGitHubClient:
    def set_repo(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo

    async def list_files(self, repo_root: str = ""):
        return ["src/components/Button.tsx"]

    async def read_file(self, path: str):
        return "const primaryBtn = { color: '#3b82f6', margin: '12px' };"

    async def write_file(self, path: str, content: str):
        return

def _make_clients(mode: str, owner: str, repo: str):
    """
    real  -> MCP clients (GitHub/Figma servers must be running)
    mock  -> local demo clients
    """
    if mode == "real":
        gh = GitHubMCPClient()
        gh.set_repo(owner, repo)
        fg = FigmaMCPClient()
        return gh, fg
    else:
        gh = MockGitHubClient()
        gh.set_repo(owner, repo)
        fg = MockFigmaClient()
        return gh, fg

def _build_approved_changes(approved_ids: set, recommendations: list[dict]) -> list[dict]:
    """
    Orchestrator expects a compact list of approvals:
      [{"file_path":..., "line":..., "original_value":...}, ...]
    """
    approved_changes = []
    for r in recommendations:
        cid = r.get("change_id")
        if cid and cid in approved_ids:
            approved_changes.append(
                {
                    "file_path": r.get("file_path"),
                    "line": r.get("line"),
                    "original_value": r.get("original_value"),
                }
            )
    return approved_changes

def main():
    st.title("🕸️ SynchroMesh: Agentic Design–Code Orchestrator")

    # Persist orchestrator across Streamlit reruns
    if "orchestrator" not in st.session_state:
        st.session_state["orchestrator"] = SynchroMeshOrchestrator()
    orchestrator: SynchroMeshOrchestrator = st.session_state["orchestrator"]

    # Ensure approvals storage exists
    if "approved_change_ids" not in st.session_state:
        st.session_state["approved_change_ids"] = set()

    # Mode: real vs mock (set by main.py; defaults to mock)
    mode = (os.getenv("SYNCHROMESH_MODE") or "mock").strip().lower()

    st.sidebar.header("Configuration")
    st.sidebar.caption(f"Mode: **{mode.upper()}**")

    repo_root = st.sidebar.text_input("Repo Root (path or identifier)", "./target_repo")
    figma_file_id = st.sidebar.text_input("Figma File ID", "v0_design_system")
    owner = st.sidebar.text_input("GitHub Owner", "owner")
    repo = st.sidebar.text_input("GitHub Repo", "legacy-app")

    github_client, figma_client = _make_clients(mode, owner, repo)

    col1, col2 = st.columns([2, 1])

    with col1:
        start_col, rerun_col = st.columns(2)

        with start_col:
            if st.button("🚀 Start Pipeline", use_container_width=True):
                with st.spinner("Agents are analyzing drift via MCP + ADK..."):
                    result = _run_async(
                        orchestrator.run_sync_pipeline(
                            repo_root=repo_root,
                            figma_file_id=figma_file_id,
                            github_mcp_client=github_client,
                            figma_mcp_client=figma_client,
                            approved_changes=None,
                        )
                    )
                    st.session_state["last_result"] = result

                st.success(f"Pipeline finished with status: {result.get('status')}")
                if result.get("status") == "AWAITING_APPROVAL":
                    st.warning("Approval is required for MEDIUM/HIGH items. Review the queue below.")
                if result.get("outputs"):
                    st.caption(f"Outputs written: {result['outputs']}")

        # Governance queue (IMPORTANT: pass orchestrator.config so ApprovalGate policies apply)
        render_approval_queue(orchestrator.context, settings=orchestrator.config)

        with rerun_col:
            if st.button("✅ Apply Approved Changes (Re-run)", use_container_width=True):
                recs = orchestrator.context.shared_memory.get("recommendations", []) or []
                approved_ids = st.session_state.get("approved_change_ids", set())

                approved_changes = _build_approved_changes(approved_ids, recs)

                with st.spinner("Re-running pipeline with approvals..."):
                    result = _run_async(
                        orchestrator.run_sync_pipeline(
                            repo_root=repo_root,
                            figma_file_id=figma_file_id,
                            github_mcp_client=github_client,
                            figma_mcp_client=figma_client,
                            approved_changes=approved_changes,
                        )
                    )
                    st.session_state["last_result"] = result

                st.success(f"Re-run finished with status: {result.get('status')}")
                if result.get("outputs"):
                    st.caption(f"Outputs written: {result['outputs']}")

        # Show PR draft / diffs if available
        last = st.session_state.get("last_result", {}) if isinstance(st.session_state.get("last_result", {}), dict) else {}
        sync_result = last.get("sync_result", {}) if isinstance(last, dict) else {}
        pr = sync_result.get("pull_request") if isinstance(sync_result, dict) else None

        if pr:
            st.subheader("🧾 Pull Request Draft")
            st.write(f"**Title:** {pr.get('title')}")
            st.text_area("Body", pr.get("body", ""), height=220)

        patches = sync_result.get("patches", []) if isinstance(sync_result, dict) else []
        if patches:
            st.subheader("🧩 Patches")
            for p in patches:
                if p.get("diff"):
                    with st.expander(f"Diff: {p.get('file_path')}"):
                        st.code(p["diff"], language="diff")

    with col2:
        render_metrics(orchestrator.context)
        render_agent_logs(orchestrator.context)

if __name__ == "__main__":
    main()