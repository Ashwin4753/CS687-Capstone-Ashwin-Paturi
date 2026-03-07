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


def _inject_theme():
    st.markdown(
        """
        <style>
        .stApp {
            background: #eef2f7;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #08152f 0%, #0b1a3d 100%);
            border-right: 1px solid rgba(255,255,255,0.05);
        }

        section[data-testid="stSidebar"] * {
            color: #f3f6fb !important;
        }

        section[data-testid="stSidebar"] .stTextInput label,
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stRadio label {
            color: #d6deeb !important;
            font-weight: 600;
        }

        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
            max-width: 1380px;
        }

        .syn-page-title {
            font-size: 2.25rem;
            font-weight: 800;
            color: #18263f;
            margin-bottom: 0.2rem;
            line-height: 1.1;
        }

        .syn-page-subtitle {
            color: #6f7b8d;
            font-size: 1rem;
            margin-bottom: 1.15rem;
        }

        .syn-top-strip {
            background: #ffffff;
            border: 1px solid #d8e0ea;
            border-radius: 14px;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
        }

        .syn-chip {
            display: inline-block;
            padding: 0.42rem 0.9rem;
            border-radius: 999px;
            font-size: 0.86rem;
            font-weight: 700;
            border: 1px solid #c8d4e2;
            background: #f6f9fc;
            color: #2d4a7b;
            margin-right: 0.55rem;
            margin-bottom: 0.2rem;
        }

        .syn-card {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 18px;
            padding: 1rem 1rem 0.95rem 1rem;
            box-shadow: 0 3px 12px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }

        .syn-card-title {
            color: #1d2c45;
            font-size: 1.1rem;
            font-weight: 800;
            margin-bottom: 0.15rem;
        }

        .syn-card-subtitle {
            color: #728094;
            font-size: 0.93rem;
            margin-bottom: 0.7rem;
        }

        .syn-soft-note {
            background: #f7fafc;
            border: 1px dashed #cad5e3;
            border-radius: 12px;
            padding: 0.85rem 0.95rem;
            color: #586579;
            font-size: 0.93rem;
        }

        .syn-section-gap {
            margin-top: 0.4rem;
        }

        .syn-risk-pill {
            display: inline-block;
            padding: 0.22rem 0.62rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 800;
            border: 1px solid transparent;
        }

        .syn-risk-low {
            background: #dff5e5;
            color: #247147;
            border-color: #c8ebd4;
        }

        .syn-risk-medium {
            background: #fff0c8;
            color: #9a6a00;
            border-color: #ffe3a0;
        }

        .syn-risk-high {
            background: #fde0e0;
            color: #a23535;
            border-color: #f7c8c8;
        }

        .syn-table-head {
            color: #64748b;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            margin-bottom: 0.35rem;
        }

        .syn-table-row {
            padding: 0.58rem 0.15rem;
            border-top: 1px solid #edf2f7;
        }

        .syn-table-value {
            color: #243247;
            font-size: 0.92rem;
            font-weight: 600;
        }

        .syn-table-muted {
            color: #5f6f84;
            font-size: 0.9rem;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d9e2ec;
            border-radius: 16px;
            padding: 0.7rem 0.7rem 0.55rem 0.7rem;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.03);
        }

        .stButton > button {
            border-radius: 10px;
            font-weight: 700;
            min-height: 2.75rem;
            border: 1px solid #cdd7e3;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 0.42rem 0.82rem;
            background: #f6f8fb;
        }

        .stTabs [aria-selected="true"] {
            background: #ffffff !important;
            color: #1f3f73 !important;
            border: 1px solid #d9e2ec !important;
        }

        .stRadio > div {
            gap: 0.2rem;
        }

        code {
            white-space: pre-wrap !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


# -----------------------------
# Mock clients for stable demo
# -----------------------------
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
        return '<span class="syn-risk-pill syn-risk-low">LOW</span>'
    if risk == "MEDIUM":
        return '<span class="syn-risk-pill syn-risk-medium">MEDIUM</span>'
    if risk == "HIGH":
        return '<span class="syn-risk-pill syn-risk-high">HIGH</span>'
    return f'<span class="syn-risk-pill">{risk}</span>'


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
    st.sidebar.caption("Agentic Governance Dashboard")

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


def _render_page_header(orchestrator: SynchroMeshOrchestrator, mode: str, owner: str, repo: str):
    st.markdown('<div class="syn-page-title">SynchroMesh</div>', unsafe_allow_html=True)
    st.markdown('<div class="syn-page-subtitle">Governance Dashboard</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="syn-top-strip">
            <span class="syn-chip">Mode: {mode.upper()}</span>
            <span class="syn-chip">Owner: {owner}</span>
            <span class="syn-chip">Repo: {repo}</span>
            <span class="syn-chip">Run ID: {orchestrator.context.shared_memory.get("run_id", "")}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_run_controls(orchestrator, github_client, figma_client, repo_root, figma_file_id):
    st.markdown('<div class="syn-card">', unsafe_allow_html=True)
    st.markdown('<div class="syn-card-title">Run Controls</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="syn-card-subtitle">Launch a new analysis run or re-run with the currently selected approvals.</div>',
        unsafe_allow_html=True,
    )

    action_col1, action_col2 = st.columns([1, 1])

    with action_col1:
        if st.button("🚀 Start Pipeline", use_container_width=True):
            st.session_state["approved_change_ids"] = set()

            with st.spinner("Agents are analyzing drift via MCP + reasoning layer..."):
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

    st.markdown("</div>", unsafe_allow_html=True)


def _render_detected_drift_table(recommendations: list[dict]):
    st.markdown('<div class="syn-card">', unsafe_allow_html=True)
    st.markdown('<div class="syn-card-title">Detected Design Tokens</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="syn-card-subtitle">Review drift findings and select the governed changes you want to carry into the next run.</div>',
        unsafe_allow_html=True,
    )

    if not recommendations:
        st.info("No recommendations available yet. Start the pipeline to populate this table.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    rows = _build_review_rows(recommendations)

    top_left, top_right = st.columns([1, 5])
    with top_left:
        show_count = st.selectbox("Show", [5, 10, 20, 50], index=1, key="table_show_count")
    with top_right:
        st.write("")

    visible_rows = rows[:show_count]

    header_cols = st.columns([0.7, 1.8, 2.2, 1.0, 2.2])
    header_cols[0].markdown('<div class="syn-table-head">Select</div>', unsafe_allow_html=True)
    header_cols[1].markdown('<div class="syn-table-head">Token Name</div>', unsafe_allow_html=True)
    header_cols[2].markdown('<div class="syn-table-head">Affected File</div>', unsafe_allow_html=True)
    header_cols[3].markdown('<div class="syn-table-head">Risk Level</div>', unsafe_allow_html=True)
    header_cols[4].markdown('<div class="syn-table-head">Suggested Action</div>', unsafe_allow_html=True)

    if "approved_change_ids" not in st.session_state:
        st.session_state["approved_change_ids"] = set()

    for idx, row in enumerate(visible_rows):
        st.markdown('<div class="syn-table-row">', unsafe_allow_html=True)
        cols = st.columns([0.7, 1.8, 2.2, 1.0, 2.2])

        checked = cols[0].checkbox(
            f"Select change {idx + 1}",
            value=row["selected"],
            key=f"table_select_{row['change_id']}_{idx}",
            label_visibility="collapsed",
        )

        if row["change_id"]:
            if checked:
                st.session_state["approved_change_ids"].add(row["change_id"])
            else:
                st.session_state["approved_change_ids"].discard(row["change_id"])

        cols[1].markdown(f"<span class='syn-table-value'><code>{row['token_name']}</code></span>", unsafe_allow_html=True)
        cols[2].markdown(f"<span class='syn-table-muted'><code>{row['affected_file']}</code></span>", unsafe_allow_html=True)
        cols[3].markdown(row["risk_badge"], unsafe_allow_html=True)
        cols[4].markdown(f"<span class='syn-table-muted'>{row['suggested_action']}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.caption(f"Showing {len(visible_rows)} of {len(rows)} recommendation(s).")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_approval_controls(context_store):
    st.markdown('<div class="syn-card">', unsafe_allow_html=True)
    st.markdown('<div class="syn-card-title">Approval Controls</div>', unsafe_allow_html=True)

    recommendations = context_store.shared_memory.get("recommendations", []) or []
    selected_ids = st.session_state.get("approved_change_ids", set())
    selected_recs = [rec for rec in recommendations if rec.get("change_id") in selected_ids]

    st.metric("Changes selected", len(selected_recs))

    comment = st.text_area(
        "Comments",
        placeholder="Reason / optional approval note",
        key="approval_comment_box",
        height=120,
    )

    st.markdown("##### Summary")
    if selected_recs:
        sample = selected_recs[0]
        st.write(f"**Primary file:** `{sample.get('file_path', '')}`")
        st.write(f"**Risk:** {sample.get('risk_level', '')}")
        if sample.get("reasoning"):
            st.caption(sample.get("reasoning"))
    else:
        st.markdown(
            '<div class="syn-soft-note">Select one or more rows from the detected drift table to review them here.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("##### Notes")
    st.caption("• LOW-risk changes can proceed automatically when policy allows.")
    st.caption("• MEDIUM/HIGH-risk changes should be reviewed before rerun.")
    if comment.strip():
        st.info(f"Approval note captured: {comment.strip()}")

    approve_col, reject_col = st.columns(2)
    approve_col.button("✅ Approve Changes", use_container_width=True, disabled=True)
    reject_col.button("❌ Reject Changes", use_container_width=True, disabled=True)

    st.caption("Selections are applied when you use the re-run control.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_sync_workflow_page(last_result: dict, context_store):
    sync_result = last_result.get("sync_result", {}) if isinstance(last_result, dict) else {}
    if not isinstance(sync_result, dict):
        sync_result = {}

    st.markdown('<div class="syn-card">', unsafe_allow_html=True)
    st.markdown('<div class="syn-card-title">Sync Workflow</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="syn-card-subtitle">Review patch output, PR draft content, and synchronization artifacts generated by the latest run.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    tabs = st.tabs(["Patches", "PR Draft", "Workflow Summary"])

    with tabs[0]:
        patches = sync_result.get("patches", [])
        if isinstance(patches, list) and patches:
            for patch in patches:
                with st.expander(f"{patch.get('file_path', 'patch')}"):
                    if patch.get("diff"):
                        st.code(patch["diff"], language="diff")
                    if patch.get("notes"):
                        st.write("**Notes:**")
                        for note in patch["notes"]:
                            st.write(f"- {note}")
        else:
            st.info("No patches available for this run.")

    with tabs[1]:
        pr = sync_result.get("pull_request")
        if isinstance(pr, dict):
            st.write(f"**Title:** {pr.get('title')}")
            st.text_area("Body", pr.get("body", ""), height=260, key="sync_pr_body")
        else:
            st.info("No PR draft available yet.")

    with tabs[2]:
        summary = sync_result.get("summary", {}) if isinstance(sync_result, dict) else {}
        if summary:
            c1, c2, c3 = st.columns(3)
            c1.metric("Applied", summary.get("applied", 0))
            c2.metric("Skipped", summary.get("skipped", 0))
            c3.metric("Files touched", summary.get("files_touched", 0))
        else:
            st.info("No sync workflow summary available yet.")


def _render_documentation_page(last_result: dict, context_store):
    evaluation = last_result.get("evaluation", {}) if isinstance(last_result, dict) else {}
    if not isinstance(evaluation, dict):
        evaluation = {}

    st.markdown('<div class="syn-card">', unsafe_allow_html=True)
    st.markdown('<div class="syn-card-title">Documentation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="syn-card-subtitle">Generated reports, evaluation snapshots, and export references from the latest run.</div>',
        unsafe_allow_html=True,
    )

    report_path = last_result.get("report_path") if isinstance(last_result, dict) else None
    if report_path:
        st.write(f"**Modernization report:** `{report_path}`")

    outputs = last_result.get("outputs", {}) if isinstance(last_result, dict) else {}
    if isinstance(outputs, dict) and outputs:
        st.write("**Exported outputs:**")
        for name, path in outputs.items():
            st.write(f"- `{name}` → `{path}`")

    if evaluation:
        st.markdown("##### Evaluation Snapshot")
        formal_parity = evaluation.get("formal_parity", {}) or {}
        token_coverage = evaluation.get("token_coverage", {}) or {}
        reasoning_stats = evaluation.get("reasoning_stats", {}) or {}

        c1, c2, c3 = st.columns(3)
        c1.metric("Formal Parity", f"{formal_parity.get('parity_score', 0)}%")
        c2.metric("Token Coverage", f"{token_coverage.get('coverage_score', 0)}%")
        c3.metric("Trace Entries", reasoning_stats.get("entries_total", 0))

    st.markdown("</div>", unsafe_allow_html=True)


def _render_settings_page(repo_root: str, figma_file_id: str, owner: str, repo: str, mode: str):
    st.markdown('<div class="syn-card">', unsafe_allow_html=True)
    st.markdown('<div class="syn-card-title">Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="syn-card-subtitle">Current runtime configuration exposed to the dashboard session.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.write(f"**Mode:** {mode.upper()}")
        st.write(f"**Repo root:** `{repo_root}`")
        st.write(f"**Figma file ID:** `{figma_file_id}`")
    with right:
        st.write(f"**GitHub owner:** `{owner}`")
        st.write(f"**GitHub repo:** `{repo}`")

    st.markdown(
        '<div class="syn-soft-note">Update these values from the sidebar configuration controls before launching the next pipeline run.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    _inject_theme()

    if "orchestrator" not in st.session_state:
        st.session_state["orchestrator"] = SynchroMeshOrchestrator()

    orchestrator: SynchroMeshOrchestrator = st.session_state["orchestrator"]

    if "approved_change_ids" not in st.session_state:
        st.session_state["approved_change_ids"] = set()

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = {}

    mode = (os.getenv("SYNCHROMESH_MODE") or "mock").strip().lower()

    page, repo_root, figma_file_id, owner, repo = _render_sidebar(orchestrator, mode)
    _render_page_header(orchestrator, mode, owner, repo)

    try:
        github_client, figma_client = _make_clients(mode, owner, repo)
    except Exception as e:
        st.error(f"Failed to initialize clients in {mode.upper()} mode: {e}")
        st.info("Switch to mock mode or check environment variables / MCP setup.")
        return

    last_result = st.session_state.get("last_result", {})

    if page == "Dashboard":
        _render_run_controls(orchestrator, github_client, figma_client, repo_root, figma_file_id)
        render_metrics(orchestrator.context)

    elif page == "Detected Drift":
        left_col, right_col = st.columns([3.2, 1.35])
        with left_col:
            _render_detected_drift_table(
                orchestrator.context.shared_memory.get("recommendations", []) or []
            )
        with right_col:
            _render_approval_controls(orchestrator.context)

    elif page == "Sync Workflow":
        _render_sync_workflow_page(last_result, orchestrator.context)

    elif page == "Review Logs":
        render_agent_logs(orchestrator.context)

    elif page == "Documentation":
        _render_documentation_page(last_result, orchestrator.context)

    elif page == "Settings":
        _render_settings_page(repo_root, figma_file_id, owner, repo, mode)

    st.markdown('<div class="syn-section-gap"></div>', unsafe_allow_html=True)

    if page in {"Dashboard", "Detected Drift"}:
        render_approval_queue(orchestrator.context, settings=orchestrator.config)


if __name__ == "__main__":
    main()