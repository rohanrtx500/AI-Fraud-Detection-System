import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

# Page configuration
st.set_page_config(page_title="Fraud Investigation Workspace", page_icon="🛡️", layout="wide")

apply_custom_theme("#1A1A24")


# Instantiate client
if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

client = FraudAPIClient()
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

st.markdown(
    "<h1 class='premium-title'>💼 Case Management Workspace</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='premium-sub'>Enterprise case management hub, timeline trackers, analyst notebooks, and evidence archives.</p>",
    unsafe_allow_html=True,
)

# Fetch metrics
metrics = client.get_cases_metrics()
if not metrics or "status_distribution" not in metrics:
    metrics = {
        "status_distribution": {"OPEN": 0, "INVESTIGATING": 0, "ESCALATED": 0, "RESOLVED": 0, "FALSE_POSITIVE": 0},
        "priority_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
        "analyst_workload": {},
    }

# Render KPI cards
col_open, col_inv, col_esc, col_res, col_fp = st.columns(5)
with col_open:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #FF2E63;'>
            <p class='kpi-title'>OPEN CASES</p>
            <h2 class='kpi-value'>{metrics["status_distribution"].get("OPEN", 0)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_inv:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #3B82F6;'>
            <p class='kpi-title'>UNDER INVESTIGATION</p>
            <h2 class='kpi-value'>{metrics["status_distribution"].get("INVESTIGATING", 0)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_esc:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #FFB300;'>
            <p class='kpi-title'>ESCALATED VERDICTS</p>
            <h2 class='kpi-value'>{metrics["status_distribution"].get("ESCALATED", 0)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_res:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #00FF87;'>
            <p class='kpi-title'>RESOLVED FRAUD</p>
            <h2 class='kpi-value'>{metrics["status_distribution"].get("RESOLVED", 0)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_fp:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #64748B;'>
            <p class='kpi-title'>FALSE POSITIVES</p>
            <h2 class='kpi-value'>{metrics["status_distribution"].get("FALSE_POSITIVE", 0)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Tabs definitions
tab_queue, tab_search, tab_workload = st.tabs(
    [
        "📂 Active Cases Queue & Analyst Audit Desk",
        "🔍 Unified Workspace Search",
        "📊 Analyst Workloads & Operational Health",
    ]
)

# ----------------- Tab 1: Queue and Audit Desk -----------------
with tab_queue:
    # Sidebar-like filters inside column structure
    col_filt1, col_filt2, col_filt3 = st.columns(3)
    with col_filt1:
        f_status = st.selectbox(
            "Status Filter",
            ["All", "OPEN", "INVESTIGATING", "ESCALATED", "RESOLVED", "FALSE_POSITIVE"],
        )
    with col_filt2:
        f_priority = st.selectbox("Priority Filter", ["All", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
    with col_filt3:
        f_analyst = st.text_input("Analyst Filter (e.g. analyst_rohan, unassigned)", "")

    # Retrieve filtered cases
    status_arg = None if f_status == "All" else f_status
    priority_arg = None if f_priority == "All" else f_priority
    analyst_arg = None
    if f_analyst.strip():
        analyst_arg = f_analyst.strip()

    cases_list = client.get_cases(status=status_arg, priority=priority_arg, analyst=analyst_arg)

    if not cases_list:
        st.warning(
            "No cases found matching the criteria. Verify API server liveness or create a case from the Ingestion sandbox."
        )
    else:
        # Construct DataFrame to show
        cases_df = pd.DataFrame(
            [
                {
                    "Case ID": c["case_id"],
                    "Alert ID": c["alert_id"],
                    "Analyst": c["analyst"] or "Unassigned",
                    "Priority": c["priority"],
                    "Status": c["status"],
                    "Created At": c["created_at"].split(".")[0].replace("T", " "),
                }
                for c in cases_list
            ]
        )
        st.dataframe(cases_df, use_container_width=True)

        st.markdown("---")
        # Detail inspector selection
        st.subheader("🕵️ Case Investigator & Audit Desk")
        selected_case_id = st.selectbox(
            "Select Case ID to Investigate", cases_df["Case ID"].tolist()
        )

        if selected_case_id:
            # Fetch details
            case_detail = client.get_case_details(selected_case_id)
            if not case_detail:
                st.error("Failed to fetch details for case.")
            else:
                col_case_meta, col_tx_meta = st.columns(2)

                # Case Metadata Update Form
                with col_case_meta:
                    st.markdown("### **Case Properties**")
                    st.write(f"**Alert ID**: `{case_detail['alert_id']}`")
                    st.write(f"**Created At**: `{case_detail['created_at'].replace('T', ' ')}`")
                    st.write(
                        f"**Resolved At**: `{case_detail['resolved_at'].replace('T', ' ') if case_detail['resolved_at'] else 'N/A'}`"
                    )

                    role = st.session_state.get("user_role", "Compliance Officer")
                    if role == "Auditor":
                        st.warning(
                            "⚠️ Access Denied: Auditors have read-only access to case properties."
                        )
                    else:
                        with st.form("update_case_form"):
                            st.markdown("**Update Case Verdict & Assignment**")
                            c_status = st.selectbox(
                                "Status",
                                [
                                    "OPEN",
                                    "INVESTIGATING",
                                    "ESCALATED",
                                    "RESOLVED",
                                    "FALSE_POSITIVE",
                                ],
                                index=[
                                    "OPEN",
                                    "INVESTIGATING",
                                    "ESCALATED",
                                    "RESOLVED",
                                    "FALSE_POSITIVE",
                                ].index(case_detail["status"]),
                            )
                            c_priority = st.selectbox(
                                "Priority",
                                ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                                index=["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(
                                    case_detail["priority"]
                                ),
                            )
                            c_analyst = st.text_input(
                                "Assigned Analyst Username", case_detail["analyst"] or ""
                            )
                            c_actor = st.text_input(
                                "Authorizing Investigator Signature",
                                st.session_state.get("user_display_name", st.session_state.username),
                            )

                            submit_update = st.form_submit_button("Commit Updates")
                            if submit_update:
                                update_res = client.update_case(
                                    case_id=selected_case_id,
                                    status=c_status,
                                    priority=c_priority,
                                    analyst=c_analyst if c_analyst.strip() else None,
                                    actor=c_actor,
                                )
                                if update_res:
                                    st.success("Case updated successfully!")
                                    st.rerun()

                # Ingested Transaction Details
                with col_tx_meta:
                    st.markdown("### **Target Transaction Insights**")
                    assessment = case_detail.get("assessment", {})
                    transaction = assessment.get("transaction", {})

                    if not transaction:
                        st.info("No transaction metadata available for this case alert.")
                    else:
                        st.write(f"**Transaction ID**: `{transaction.get('transaction_id')}`")
                        st.write(f"**User ID**: `{transaction.get('sender_id')}`")
                        st.write(f"**Merchant ID**: `{transaction.get('receiver_id')}`")
                        st.write(
                            f"**Amount**: `${transaction.get('amount'):,.2f} {transaction.get('currency')}`"
                        )
                        st.write(f"**MCC Category**: `{transaction.get('merchant_category')}`")
                        st.write(
                            f"**IP Location**: `{transaction.get('location_city')}, {transaction.get('location_country')}`"
                        )
                        st.write(f"**Device Fingerprint**: `{transaction.get('device_id')}`")
                        st.write(
                            f"**API Risk Probability**: `{assessment.get('risk_score')}%` ({assessment.get('recommendation')})"
                        )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")

                # Analyst Notebook & Note categories
                col_notes, col_timeline = st.columns([1, 1])

                with col_notes:
                    st.subheader("📝 Analyst Notebook")

                    role = st.session_state.get("user_role", "Compliance Officer")
                    if role == "Auditor":
                        st.warning(
                            "⚠️ Access Denied: Auditors have read-only access to analyst notebook."
                        )
                    else:
                        # Note form
                        with st.form("add_note_form"):
                            st.markdown("**Add Analyst Entry**")
                            note_cat = st.selectbox(
                                "Category",
                                ["GENERAL", "TRANSACTION", "BEHAVIORAL", "GRAPH", "COMPLIANCE"],
                            )
                            note_content = st.text_area("Observations & Evidence Narrative")
                            note_author = st.text_input(
                                "Analyst Initials",
                                c_actor if "c_actor" in locals() else st.session_state.get("user_display_name", st.session_state.username),
                            )
                            submit_note = st.form_submit_button("Post Entry")

                            if submit_note:
                                if not note_content.strip():
                                    st.error("Note content cannot be empty.")
                                else:
                                    note_res = client.add_case_note(
                                        case_id=selected_case_id,
                                        category=note_cat,
                                        content=note_content,
                                        author=note_author,
                                    )
                                    if note_res:
                                        st.success("Note entry recorded!")
                                        st.rerun()

                    # List notes
                    st.markdown("#### Note Records")
                    notes = case_detail.get("notes", [])
                    if not notes:
                        st.info("No notes logged on this case yet.")
                    else:
                        for note in sorted(notes, key=lambda x: x["created_at"], reverse=True):
                            created_ts = note["created_at"].split(".")[0].replace("T", " ")
                            st.markdown(
                                f"""
                                <div class='note-card'>
                                    <span style='font-size: 0.8rem; background-color: #E2E8F0; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600;'>{note["category"]}</span>
                                    <p style='margin: 0.5rem 0; font-size: 0.95rem; color: #1E293B;'>{note["content"]}</p>
                                    <span style='font-size: 0.75rem; color: #64748B;'>Written by <b>{note["author"]}</b> at {created_ts}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                # Timeline logs
                with col_timeline:
                    st.subheader("⏳ Investigation Timeline")
                    timeline = case_detail.get("timeline_events", [])
                    if not timeline:
                        st.info("No events logged on this case timeline.")
                    else:
                        for event in sorted(timeline, key=lambda x: x["created_at"], reverse=True):
                            event_ts = event["created_at"].split(".")[0].replace("T", " ")
                            icon = "🚩"
                            if event["event_type"] == "CASE_CREATED":
                                icon = "🆕"
                            elif event["event_type"] == "ANALYST_ASSIGNED":
                                icon = "👤"
                            elif event["event_type"] == "NOTE_ADDED":
                                icon = "📝"
                            elif event["event_type"] == "EVIDENCE_ATTACHED":
                                icon = "📎"
                            elif event["event_type"] == "STATUS_CHANGED":
                                icon = "⚙️"

                            st.markdown(
                                f"""
                                <div class='timeline-log'>
                                    <p style='margin: 0; font-weight: 700; color: #0F172A;'>{icon} {event["event_type"]}</p>
                                    <p style='margin: 0.2rem 0; font-size: 0.9rem; color: #334155;'>{event["description"]}</p>
                                    <span style='font-size: 0.75rem; color: #64748B;'>Action by <b>{event["actor"]}</b> at {event_ts}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("---")

                # Evidence management
                st.subheader("📎 Evidence Files & Attachments")

                # File upload form
                role = st.session_state.get("user_role", "Compliance Officer")
                if role == "Auditor":
                    st.warning(
                        "⚠️ Access Denied: Auditors have read-only access to evidence attachments."
                    )
                else:
                    evidence_file = st.file_uploader(
                        "Upload evidence file (Screenshots, PDFs, transaction CSV logs)",
                        type=["png", "jpg", "jpeg", "pdf", "csv"],
                    )
                    if evidence_file:
                        uploader_sig = st.text_input(
                            "Uploader Analyst Signature",
                            c_actor if "c_actor" in locals() else st.session_state.get("user_display_name", st.session_state.username),
                            key="evidence_uploader_sig",
                        )
                        if st.button("Upload Evidence Attachment"):
                            with st.spinner("Uploading file..."):
                                # Read bytes
                                file_bytes = evidence_file.read()
                                upload_res = client.upload_evidence(
                                    case_id=selected_case_id,
                                    filename=evidence_file.name,
                                    file_bytes=file_bytes,
                                    mime_type=evidence_file.type,
                                    uploaded_by=uploader_sig,
                                )
                                if upload_res:
                                    st.success(
                                        f"Successfully attached file {evidence_file.name} to case!"
                                    )
                                    st.rerun()

                # List evidence
                evidence = case_detail.get("evidence", [])
                if not evidence:
                    st.info("No evidence files attached to this case.")
                else:
                    for ev in evidence:
                        ev_ts = ev["uploaded_at"].split(".")[0].replace("T", " ")
                        st.markdown(
                            f"📎 **{ev['filename']}** ({ev['file_type']}) - Uploaded by `{ev['uploaded_by']}` at `{ev_ts}`"
                        )

                        # Add a download button pointing to the REST API download endpoint
                        download_url = f"{client.base_url}/cases/evidence/{ev['evidence_id']}/file"
                        st.markdown(
                            f'<a href="{download_url}" target="_blank" style="background-color: #3B82F6; color: white; padding: 0.3rem 0.8rem; text-decoration: none; border-radius: 4px; font-size: 0.85rem; font-weight: 600;">📥 Download File</a>',
                            unsafe_allow_html=True,
                        )
                        st.write("")

# ----------------- Tab 2: Search -----------------
with tab_search:
    st.subheader("🔍 Unified Workspace Search")
    st.write(
        "Perform system-wide queries matching case IDs, assigned analyst, transaction IDs, sender/receiver accounts, device IDs, or merchants."
    )

    search_q = st.text_input("Enter Search Term", "", placeholder="e.g. usr_100155, alert_1029...")

    if search_q.strip():
        with st.spinner("Searching workspace records..."):
            results = client.search_workspace(search_q.strip())

        col_res_cases, col_res_txs = st.columns(2)

        with col_res_cases:
            st.markdown("#### Matching Cases")
            cases = results.get("cases", [])
            if not cases:
                st.info("No matching cases found.")
            else:
                for c in cases:
                    st.markdown(
                        f"""
                        <div style='background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;'>
                            <strong>Case ID:</strong> <code>{c["case_id"]}</code><br>
                            <strong>Status:</strong> {c["status"]} | <strong>Priority:</strong> {c["priority"]}<br>
                            <strong>Analyst:</strong> {c["analyst"] or "Unassigned"}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with col_res_txs:
            st.markdown("#### Matching Transactions")
            txs = results.get("transactions", [])
            if not txs:
                st.info("No matching transactions found.")
            else:
                for t in txs:
                    st.markdown(
                        f"""
                        <div style='background-color: rgba(15, 23, 42, 0.45); border: 1px solid rgba(255, 255, 255, 0.05); padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;'>
                            <strong>Transaction ID:</strong> <code>{t["transaction_id"]}</code><br>
                            <strong>Sender Account:</strong> <code>{t["sender_id"]}</code><br>
                            <strong>Receiver Account:</strong> <code>{t["receiver_id"]}</code><br>
                            <strong>Amount:</strong> ${t["amount"]:.2f} | <strong>Device:</strong> <code>{t["device_id"]}</code>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

# ----------------- Tab 3: Workloads -----------------
with tab_workload:
    st.subheader("📊 Analyst Workloads & Operational Health")

    # Render Workload stats charts
    col_chart_left, col_chart_mid, col_chart_right = st.columns(3)

    # Priority distribution chart
    with col_chart_left:
        st.markdown("#### Queue Load by Priority")
        df_prio = pd.DataFrame(
            list(metrics["priority_distribution"].items()), columns=["Priority", "Count"]
        )
        fig_prio = px.bar(
            df_prio,
            x="Count",
            y="Priority",
            orientation="h",
            color="Priority",
            color_discrete_map={
                "LOW": "#00FF87",
                "MEDIUM": "#3B82F6",
                "HIGH": "#FFB300",
                "CRITICAL": "#FF2E63",
            },
        )
        apply_plotly_theme(fig_prio)
        st.plotly_chart(fig_prio, use_container_width=True)

    # Funnel chart of case progression
    with col_chart_mid:
        st.markdown("#### Case Lifecycle Funnel")
        s_dist = metrics.get("status_distribution", {})
        total_cases = sum(s_dist.values())
        investigating = (
            s_dist.get("INVESTIGATING", 0)
            + s_dist.get("ESCALATED", 0)
            + s_dist.get("RESOLVED", 0)
            + s_dist.get("FALSE_POSITIVE", 0)
        )
        escalated = s_dist.get("ESCALATED", 0) + s_dist.get("RESOLVED", 0)
        resolved = s_dist.get("RESOLVED", 0) + s_dist.get("FALSE_POSITIVE", 0)

        fig_funnel = go.Figure(
            go.Funnel(
                y=["Total Ingested", "Investigated", "Escalated", "Resolved/Closed"],
                x=[total_cases, investigating, escalated, resolved],
                textinfo="value+percent initial",
                connector={"fillcolor": "rgba(255,255,255,0.1)"},
                marker={"color": ["#3B82F6", "#8B5CF6", "#FFB300", "#00FF87"]},
            )
        )
        fig_funnel.update_layout(margin={"t": 30, "b": 10, "l": 10, "r": 10}, height=280)
        apply_plotly_theme(fig_funnel)
        st.plotly_chart(fig_funnel, use_container_width=True)

    # Workloads distribution chart
    with col_chart_right:
        st.markdown("#### Active Workload per Analyst")
        df_work = pd.DataFrame(
            list(metrics["analyst_workload"].items()), columns=["Analyst", "Active Cases"]
        )
        fig_work = px.pie(
            df_work,
            values="Active Cases",
            names="Analyst",
            hole=0.5,
            color_discrete_sequence=["#00F0FF", "#3B82F6", "#8B5CF6", "#B388FF"],
        )
        apply_plotly_theme(fig_work)
        st.plotly_chart(fig_work, use_container_width=True)

    st.markdown("---")
    st.subheader("🏆 Analyst Performance Leaderboard & Scorecards")
    st.write(
        "Tracks resolution efficiency, true positive rates, and audit accuracy across compliance personnel."
    )

    # Fetch monthly reports summary from API
    rep_summary = client.get_reports_summary(window="monthly")
    analysts_perf = rep_summary.get("analyst_performance", [])
    if not analysts_perf:
        analysts_perf = [
            {
                "analyst": "analyst_rohan",
                "assigned_cases": 45,
                "resolved_cases": 40,
                "false_positives": 5,
                "true_positives": 35,
                "average_resolution_time_hours": 1.5,
                "accuracy_rate": 0.875,
            },
            {
                "analyst": "analyst_clara",
                "assigned_cases": 32,
                "resolved_cases": 30,
                "false_positives": 3,
                "true_positives": 27,
                "average_resolution_time_hours": 1.2,
                "accuracy_rate": 0.900,
            },
            {
                "analyst": "Unassigned",
                "assigned_cases": 8,
                "resolved_cases": 0,
                "false_positives": 0,
                "true_positives": 0,
                "average_resolution_time_hours": 0.0,
                "accuracy_rate": 0.0,
            },
        ]

    df_leaderboard = pd.DataFrame(analysts_perf)
    df_leaderboard["Accuracy Rate"] = df_leaderboard["accuracy_rate"].map(
        lambda x: f"{x * 100:.1f}%"
    )
    df_leaderboard["Avg Resolution Time (hrs)"] = df_leaderboard["average_resolution_time_hours"]

    df_show = df_leaderboard[
        [
            "analyst",
            "assigned_cases",
            "resolved_cases",
            "true_positives",
            "false_positives",
            "Accuracy Rate",
            "Avg Resolution Time (hrs)",
        ]
    ]
    df_show.columns = [
        "Analyst",
        "Assigned Cases",
        "Resolved Cases",
        "True Positives (Fraud)",
        "False Positives",
        "Accuracy Rate",
        "Avg Resolution Time (Hours)",
    ]
    st.dataframe(df_show, use_container_width=True)
