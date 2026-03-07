import os
import asyncio
import streamlit as st

from core.orchestrator import SynchroMeshOrchestrator
from integration.github_mcp_client import GitHubMCPClient
from integration.figma_mcp_client import FigmaMCPClient
from interaction.dashboard.visualizer import render_metrics
from interaction.dashboard.reasoning_panel import render_agent_logs
from interaction.dashboard.governance_ui import render_approval_queue

st.set_page_config(
    page_title="SynchroMesh Governance Dashboard",
    layout="wide",
)


def _run_async(coro):
    """
    Streamlit-safe async runner.
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
            "border.radius.md": "8px",
        }


class MockGitHubClient:
    def set_repo(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo

    async def list_files(self, repo_root: str = ""):
        return [
            "src/components/Button.tsx",
            "src/components/Card.tsx",
            "src/components/Navbar.tsx",
        ]

    async def read_file(self, path: str):
        if "Button" in path:
            return "const primaryBtn = { color: '#3b82f6', margin: '12px' };"
        if "Card" in path:
            return "const card = { borderRadius: '8px', padding: '12px' };"
        return "const nav = { color: 'rgb(59,130,246)' };"

    async def write_file(self, path: str, content: str):
        return


def _make_clients(mode: str, owner: str, repo: str):
    """
    real  -> MCP clients
    mock  -> local demo clients
    """
    if mode == "real":
        github = GitHubMCPClient()
        github.set_repo(owner, repo)
        figma = FigmaMCPClient()
        return github, figma

    github = MockGitHubClient()
    github.set_repo(owner, repo)
    figma = MockFigmaClient()
    return github, figma


def _build_approved_changes(approved_ids: set, recommendations: list[dict]) -> list[dict]:
    approved_changes = []

    for rec in recommendations:
        change_id = rec.get("change_id")
        if change_id and change_id in approved_ids:
            approved_changes.append(
                {
                    "file_path": rec.get("file_path"),
                    "line": rec.get("line"),
                    "original_value": rec.get("original_value"),
                }
            )

    return approved_changes


def _risk_badge(risk: str) -> str:
    risk = str(risk).upper()
    if risk == "LOW":
        return "🟢 LOW"
    if risk == "MEDIUM":
        return "🟠 MEDIUM"
    if risk == "HIGH":
        return "🔴 HIGH"
    return risk


def _build_review_rows(recommendations: list[dict]) -> list[dict]:
    rows = []
    for rec in recommendations:
        rows.append(
            {
                "change_id": rec.get("change_id", ""),
                "selected": rec.get("change_id", "") in st.session_state.get("approved_change_ids", set()),
                "token_name": rec.get("proposed_token", ""),
                "affected_file": rec.get("file_path", ""),
                "line": rec.get("line", ""),
                "risk_level": rec.get("risk_level", ""),
                "risk_badge": _risk_badge(rec.get("risk_level", "")),
                "suggested_action": rec.get("replacement_text", ""),
                "original_value": rec.get("original_value", ""),
                "reasoning": rec.get("reasoning", ""),
            }
        )
    return rows


def _render_sidebar(orchestrator: SynchroMeshOrchestrator, mode: str):
    st.sidebar.markdown("## SynchroMesh")
    st.sidebar.caption("Governance Dashboard")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Detected Drift",
            "Sync Workflow",
            "Review Logs",
            "Documentation",
            "Settings",
        ],
        index=0,
    )

    st.sidebar.divider()
    st.sidebar.markdown("### Configuration")
    st.sidebar.caption(f"Mode: **{mode.upper()}**")

    default_repo_root = (
        orchestrator.config.get("mcp", {})
        .get("github", {})
        .get("repo_root", "./target_repo")
    )

    repo_root = st.sidebar.text_input("Repo Root", default_repo_root)
    figma_file_id = st.sidebar.text_input("Figma File ID", "v0_design_system")
    owner = st.sidebar.text_input("GitHub Owner", "owner")
    repo = st.sidebar.text_input("GitHub Repo", "legacy-app")

    st.sidebar.divider()
    st.sidebar.markdown("### System Status")
    st.sidebar.write(f"**Run ID:** `{orchestrator.context.shared_memory.get('run_id', '')}`")
    st.sidebar.write(f"**Selected approvals:** {len(st.session_state.get('approved_change_ids', set()))}")

    return page, repo_root, figma_file_id, owner, repo


def _render_detected_tokens_table(recommendations: list[dict]):
    st.markdown("### Detected Design Drift")

    if not recommendations:
        st.info("No recommendations available yet. Start the pipeline to populate this table.")
        return

    rows = _build_review_rows(recommendations)

    show_count = st.selectbox("Show", [5, 10, 20, 50], index=1, key="table_show_count")
    visible_rows = rows[:show_count]

    header_cols = st.columns([0.7, 2.0, 2.0, 1.1, 2.2])
    header_cols[0].markdown("**Select**")
    header_cols[1].markdown("**Token Name**")
    header_cols[2].markdown("**Affected File**")
    header_cols[3].markdown("**Risk Level**")
    header_cols[4].markdown("**Suggested Action**")

    st.divider()

    if "approved_change_ids" not in st.session_state:
        st.session_state["approved_change_ids"] = set()

    for idx, row in enumerate(visible_rows):
        cols = st.columns([0.7, 2.0, 2.0, 1.1, 2.2])

        checked = cols[0].checkbox(
            "",
            value=row["selected"],
            key=f"table_select_{row['change_id']}_{idx}",
        )

        if row["change_id"]:
            if checked:
                st.session_state["approved_change_ids"].add(row["change_id"])
            else:
                st.session_state["approved_change_ids"].discard(row["change_id"])

        cols[1].write(f"`{row['token_name']}`")
        cols[2].write(f"`{row['affected_file']}`")
        cols[3].write(row["risk_badge"])
        cols[4].write(row["suggested_action"])

    st.caption(f"Showing {len(visible_rows)} of {len(rows)} detected recommendation(s).")


def _render_approval_controls(context_store):
    st.markdown("### Approval Controls")

    recommendations = context_store.shared_memory.get("recommendations", []) or []
    selected_ids = st.session_state.get("approved_change_ids", set())
    selected_recs = [
        rec for rec in recommendations
        if rec.get("change_id") in selected_ids
    ]

    st.metric("Changes Selected", len(selected_recs))

    comment = st.text_area(
        "Comments",
        placeholder="Reason / optional approval note",
        key="approval_comment_box",
        height=100,
    )

    st.markdown("#### Summary")
    if selected_recs:
        sample = selected_recs[0]
        st.write(f"**Primary file:** `{sample.get('file_path', '')}`")
        st.write(f"**Risk:** {_risk_badge(sample.get('risk_level', ''))}")
        if sample.get("reasoning"):
            st.caption(sample.get("reasoning"))
    else:
        st.caption("Select one or more changes from the review table to inspect them here.")

    st.markdown("#### Notes")
    st.caption("• LOW-risk changes can proceed automatically when policy allows.")
    st.caption("• MEDIUM/HIGH-risk changes should be reviewed before rerun.")
    if comment.strip():
        st.info(f"Approval note captured: {comment.strip()}")

    approve_col, reject_col = st.columns(2)
    approve_col.button("✅ Approve Changes", use_container_width=True, disabled=True)
    reject_col.button("❌ Reject Changes", use_container_width=True, disabled=True)

    st.caption("Approval actions are finalized when you use the re-run control.")


def _render_bottom_tabs(last_result: dict, context_store):
    sync_result = last_result.get("sync_result", {}) if isinstance(last_result, dict) else {}
    if not isinstance(sync_result, dict):
        sync_result = {}

    evaluation = last_result.get("evaluation", {}) if isinstance(last_result, dict) else {}
    if not isinstance(evaluation, dict):
        evaluation = {}

    tabs = st.tabs(
        [
            "Agent Reasoning",
            "Patches",
            "PR Draft",
            "Evaluation",
            "Report",
        ]
    )

    with tabs[0]:
        render_agent_logs(context_store)

    with tabs[1]:
        patches = sync_result.get("patches", [])
        if isinstance(patches, list) and patches:
            for patch in patches:
                if patch.get("diff"):
                    with st.expander(f"Diff: {patch.get('file_path')}"):
                        st.code(patch["diff"], language="diff")
        else:
            st.info("No patches available for this run.")

    with tabs[2]:
        pr = sync_result.get("pull_request")
        if isinstance(pr, dict):
            st.write(f"**Title:** {pr.get('title')}")
            st.text_area("Body", pr.get("body", ""), height=220, key="pr_body_preview")
        else:
            st.info("No PR draft available yet.")

    with tabs[3]:
        if evaluation:
            formal_parity = evaluation.get("formal_parity", {}) or {}
            token_coverage = evaluation.get("token_coverage", {}) or {}
            reasoning_stats = evaluation.get("reasoning_stats", {}) or {}

            st.write(f"**Formal parity:** {formal_parity.get('parity_score', 0)}%")
            st.write(f"**Token coverage:** {token_coverage.get('coverage_score', 0)}%")
            st.write(f"**Trace entries:** {reasoning_stats.get('entries_total', 0)}")
        else:
            st.info("No evaluation snapshot available yet.")

    with tabs[4]:
        report_path = last_result.get("report_path") if isinstance(last_result, dict) else None
        if report_path:
            st.code(report_path)
        else:
            st.info("No modernization report generated yet.")


def main():
    st.markdown("## SynchroMesh")
    st.caption("Governance Dashboard")

    if "orchestrator" not in st.session_state:
        st.session_state["orchestrator"] = SynchroMeshOrchestrator()

    orchestrator: SynchroMeshOrchestrator = st.session_state["orchestrator"]

    if "approved_change_ids" not in st.session_state:
        st.session_state["approved_change_ids"] = set()

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = {}

    mode = (os.getenv("SYNCHROMESH_MODE") or "mock").strip().lower()

    page, repo_root, figma_file_id, owner, repo = _render_sidebar(orchestrator, mode)

    try:
        github_client, figma_client = _make_clients(mode, owner, repo)
    except Exception as e:
        st.error(f"Failed to initialize clients in {mode.upper()} mode: {e}")
        st.info("Switch to mock mode or check environment variables / MCP setup.")
        return

    if page != "Dashboard":
        st.info(f"'{page}' view is reserved for the next UI iteration. Use Dashboard for the live workflow.")
        return

    action_col1, action_col2 = st.columns([1, 1])

    with action_col1:
        if st.button("🚀 Start Pipeline", use_container_width=True):
            st.session_state["approved_change_ids"] = set()

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

    with action_col2:
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

    render_metrics(orchestrator.context)

    main_col, side_col = st.columns([3.2, 1.3])

    with main_col:
        _render_detected_tokens_table(
            orchestrator.context.shared_memory.get("recommendations", []) or []
        )

        st.markdown("### Review Each Detected Drift")
        render_approval_queue(orchestrator.context, settings=orchestrator.config)

    with side_col:
        _render_approval_controls(orchestrator.context)

    st.divider()
    _render_bottom_tabs(st.session_state.get("last_result", {}), orchestrator.context)


if __name__ == "__main__":
    main()