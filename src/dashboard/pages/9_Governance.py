import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

st.set_page_config(page_title="Governance & Compliance Center", page_icon="⚖️", layout="wide")

apply_custom_theme("#1F2421")

st.markdown(
    "<h1 class='premium-title'>⚖️ Enterprise Governance, Risk & Compliance (GRC)</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p class='premium-sub'>System audit trail logs, override resolution tracking, and Role-Based Access Control (RBAC) policy enforcement.</p>",
    unsafe_allow_html=True,
)

if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

if st.session_state.user_role != "Compliance Officer":
    st.error("⚠️ Access Denied: This workspace is designated exclusively for Compliance Officer users.")
    st.stop()
client = FraudAPIClient()
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

tab_audit, tab_policy = st.tabs(["📋 System Audit Trail Logs", "🛡️ RBAC Policy Matrix"])

with tab_audit:
    st.markdown("### 📋 System Override Audit Trail Logs")
    st.write(
        "Real-time trail tracking of status changes, reviewer overrides, and true/false positive decisions."
    )

    # Load from database
    logs = client.get_audit_logs()

    if not logs:
        st.info("📭 No audit trail entries yet. Override decisions, reviewer actions, and status changes will be recorded here automatically.")
        st.stop()

    df_logs = pd.DataFrame(logs)

    # Governance Analytics Charts
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        df_action = df_logs.groupby("action_taken").size().reset_index(name="Count")
        fig_action = px.bar(
            df_action,
            x="Count",
            y="action_taken",
            orientation="h",
            color="action_taken",
            color_discrete_sequence=["#FF2E63", "#00FF87", "#FFB300", "#00F0FF", "#B388FF"],
            title="Logged Override Decisions",
            labels={"action_taken": "Action Taken", "Count": "Frequency"},
        )
        apply_plotly_theme(fig_action)
        fig_action.update_layout(
            showlegend=False,
            margin={"t": 40, "b": 10, "l": 10, "r": 10},
            height=200,
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_action, use_container_width=True)

    with col_chart2:
        df_reviewer = df_logs.groupby("reviewer_id").size().reset_index(name="Count")
        fig_reviewer = px.bar(
            df_reviewer,
            x="reviewer_id",
            y="Count",
            color="reviewer_id",
            color_discrete_sequence=["#00F0FF", "#3B82F6", "#8B5CF6"],
            title="Audit Action Count by Reviewer",
            labels={"reviewer_id": "Reviewer ID", "Count": "Actions"},
        )
        apply_plotly_theme(fig_reviewer)
        fig_reviewer.update_layout(
            showlegend=False, margin={"t": 40, "b": 10, "l": 10, "r": 10}, height=200
        )
        st.plotly_chart(fig_reviewer, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Rename cols for professional look
    df_show = df_logs[["logged_at", "reviewer_id", "action_taken", "notes", "assessment_id"]].copy()
    df_show.columns = [
        "Timestamp",
        "Reviewer / Actor",
        "Action Taken",
        "Notes / Justification",
        "Assessment ID",
    ]
    df_show["Timestamp"] = df_show["Timestamp"].map(lambda x: x.replace("T", " ").split(".")[0])

    st.dataframe(df_show, use_container_width=True)

with tab_policy:
    st.markdown("### 🛡️ RBAC Permissions Policy Matrix")
    st.write("Configured permissions mapping user roles to database action capabilities.")

    policy_data = [
        {
            "Capabilities": "View Alerts / Workspace Queue",
            "Auditor": "✅ Read-Only",
            "Analyst": "✅ View & Inspect",
            "Compliance Officer": "✅ View & Inspect",
        },
        {
            "Capabilities": "Update Case Status / Add Note / Attach Evidence",
            "Auditor": "❌ Denied",
            "Analyst": "✅ Write Access",
            "Compliance Officer": "✅ Write Access",
        },
        {
            "Capabilities": "Stress Test Simulators",
            "Auditor": "❌ Denied",
            "Analyst": "❌ Denied",
            "Compliance Officer": "✅ Execute Runs",
        },
        {
            "Capabilities": "Manage IP / Device Blacklists",
            "Auditor": "❌ Denied",
            "Analyst": "❌ Denied",
            "Compliance Officer": "✅ Read / Write",
        },
        {
            "Capabilities": "Download Executive Reports (PDF/Excel)",
            "Auditor": "❌ Denied",
            "Analyst": "❌ Denied",
            "Compliance Officer": "✅ Generate & Download",
        },
    ]
    st.table(pd.DataFrame(policy_data))

    st.info(
        "To test RBAC enforcement, toggle your role in the sidebar and navigate to different pages (e.g. Reports or Simulation Lab) to observe blocked options."
    )
