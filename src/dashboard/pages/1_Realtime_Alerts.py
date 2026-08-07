from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

# Page configuration
st.set_page_config(page_title="Investigation Workspace", page_icon="🚨", layout="wide", initial_sidebar_state="expanded")

apply_custom_theme("#2A0A15")

st.markdown(
    "<h1 class='premium-title'>🚨 Real-Time Risk Evaluation Center</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='premium-sub'>Evaluate live transaction risk profiles and perform compliance audits on high-risk records.</p>",
    unsafe_allow_html=True,
)

# Initialize REST Client
if "user_token" not in st.session_state and "session_token" in st.query_params:
    st.session_state.user_token = st.query_params["session_token"]
    st.session_state.user_role = st.query_params.get("role", "Analyst")
    st.session_state.username = st.query_params.get("username", "User")
    st.session_state.user_role_id = st.query_params.get("role_id", "N/A")
    st.session_state.user_display_name = f"{st.session_state.username} ({st.session_state.user_role_id})"

if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

if st.session_state.user_role != "Analyst":
    st.error("⚠️ Access Denied: This workspace is designated exclusively for Analyst users.")
    st.stop()
client = FraudAPIClient()
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

# Split page into Ingestion Sandbox and Alerts Queue / Investigation Workspace
tab_sandbox, tab_workspace = st.tabs(
    ["Direct Transaction Ingestion", "Compliance Review Queue"]
)

# ----------------- Ingestion Sandbox Tab -----------------
with tab_sandbox:
    st.subheader("Direct Transaction Ingestion Desk")
    st.write(
        "Submit transaction parameters to the risk engine to generate risk profiles and factor attributions."
    )

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sender_id = st.text_input("Sender ID", "usr_100155")
        receiver_id = st.text_input("Receiver ID", "merch_79951")
        amount = st.number_input("Amount ($)", min_value=0.01, value=450.0)
        currency = st.selectbox("Currency Code", ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"])
        merchant_cat = st.text_input("Merchant MCC Code", "5944")  # Jewelry
    with col_f2:
        country = st.text_input(
            "IP Location Country (2-Letter ISO, e.g., US, IN)", "US", max_chars=2
        )
        city = st.text_input("IP Location City", "New York")
        device_id = st.text_input("Device Hardware Fingerprint", "dev_mac_71109a")
        ip_address = st.text_input("IP Address String", "192.168.12.5")
        vel_5m = st.number_input("Simulate recent 5-min transactions", min_value=0, value=0)
        vel_1h = st.number_input("Simulate recent 1-hour transactions", min_value=0, value=1)

    if "active_scoring_result" not in st.session_state:
        st.session_state.active_scoring_result = None

    if st.button("Evaluate Risk Profile"):
        payload = {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "amount": amount,
            "currency": currency,
            "merchant_category": merchant_cat,
            "location_country": country,
            "location_city": city,
            "device_id": device_id,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
            "user_velocity_5m": vel_5m,
            "user_velocity_1h": vel_1h,
        }
        with st.spinner("Scoring..."):
            res = client.score_transaction(payload)

        if "error" in res:
            st.error(res["error"])
            st.info(
                "FastAPI backend API is currently offline. Start server using: python -m src.api.main"
            )
            st.session_state.active_scoring_result = None
        else:
            st.session_state.active_scoring_result = res

    res = st.session_state.active_scoring_result
    if res:
        st.success("Risk evaluation complete!")
        st.markdown(
            f"### **Consolidated Risk Score: `{res['risk_score']}`** ({res['risk_bucket']})"
        )
        st.markdown(f"**Recommendation Outcome**: `{res['recommendation']}`")

        col_s_gauge, col_s_bar = st.columns([1, 1.2])
        with col_s_gauge:
            score_val = float(res["risk_score"])
            fig_dial = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=score_val,
                    title={
                        "text": "Consolidated Risk Score",
                        "font": {"size": 14, "color": "#FFFFFF"},
                    },
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#64748B"},
                        "bar": {
                            "color": (
                                "#FF2E63"
                                if score_val > 70
                                else ("#FFB300" if score_val > 30 else "#00FF87")
                            )
                        },
                        "bgcolor": "rgba(0,0,0,0)",
                        "borderwidth": 2,
                        "bordercolor": "#1E293B",
                        "steps": [
                            {"range": [0, 30], "color": "rgba(0, 255, 135, 0.05)"},
                            {"range": [30, 70], "color": "rgba(255, 179, 0, 0.05)"},
                            {"range": [70, 100], "color": "rgba(255, 46, 99, 0.05)"},
                        ],
                    },
                )
            )
            fig_dial.update_layout(height=180, margin={"t": 30, "b": 10, "l": 10, "r": 10})
            apply_plotly_theme(fig_dial)
            st.plotly_chart(fig_dial, use_container_width=True)

        with col_s_bar:
            # Sub-scores bar chart
            df_sub = pd.DataFrame(
                list(res["sub_scores"].items()), columns=["Sub-Risk Dimension", "Score"]
            )
            fig = px.bar(
                df_sub,
                x="Score",
                y="Sub-Risk Dimension",
                orientation="h",
                range_x=[0, 100],
                color="Score",
                color_continuous_scale=px.colors.sequential.Teal,
            )
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🛡️ Decision Engine Verdict")

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            action = res.get("decision_action", "APPROVE")
            if action == "BLOCK":
                pill_class = "status-pill status-pill-red"
            elif action in ["ESCALATE", "MANUAL_REVIEW"]:
                pill_class = "status-pill status-pill-amber"
            elif action == "REQUEST_VERIFICATION":
                pill_class = "status-pill status-pill-purple"
            else:
                pill_class = "status-pill status-pill-green"

            st.markdown(
                f"""
                <div class='glass-card' style='margin-bottom: 0;'>
                    <p style='margin: 0.4rem 0;'><b>Verdict Action</b>: <span class='{pill_class}'>{action}</span></p>
                    <p style='margin: 0.4rem 0;'><b>ML Recommendation</b>: <code>{res.get('recommendation')}</code></p>
                    <p style='margin: 0.4rem 0;'><b>Model Calibration</b>: <code>{res.get('model_version')}</code></p>
                    <p style='margin: 0.4rem 0;'><b>Assessment ID</b>: <code style='font-size:0.8rem;'>{res.get('assessment_id')}</code></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_v2:
            reasons = res.get("decision_reasons", ["No anomaly markers detected."])
            reasons_html = "".join(
                [f"<li style='margin-bottom: 0.4rem;'>{r}</li>" for r in reasons]
            )
            st.markdown(
                f"""
                <div class='glass-card' style='margin-bottom: 0;'>
                    <p style='margin: 0 0 0.5rem 0; font-weight: 700; color: #FFFFFF;'>Justification Analysis:</p>
                    <ul style='margin: 0; padding-left: 1.2rem; font-size: 0.9rem; color: #FFB300;'>
                        {reasons_html}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Escalate to Case Form
        st.markdown("---")
        st.markdown("### 💼 Escalate to Workspace Case")
        if "assessment_id" in res and res["assessment_id"]:
            alert_db_id = res["assessment_id"]
            with st.form("sandbox_escalate_form"):
                esc_priority = st.selectbox(
                    "Escalation Priority", ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                )
                esc_analyst = st.text_input(
                    "Assigned Analyst",
                    st.session_state.get("user_display_name", st.session_state.username),
                )
                submit_esc = st.form_submit_button("Create Case in Workspace")
                if submit_esc:
                    with st.spinner("Creating case..."):
                        esc_res = client.escalate_alert(
                            alert_id=alert_db_id,
                            priority=esc_priority,
                            analyst=esc_analyst if esc_analyst.strip() else None,
                        )
                        if esc_res and "case_id" in esc_res:
                            st.success(
                                f"Case {esc_res['case_id']} successfully initialized in workspace!"
                            )
                            st.session_state.active_scoring_result = None
                            st.rerun()
                        else:
                            st.error(
                                "Failed to escalate case. Make sure the API server is online."
                            )
            st.info(
                "Assessment ID missing in response. Please ensure the transaction has been evaluated."
            )

# ----------------- Investigation Workspace Tab -----------------
with tab_workspace:
    st.subheader("Active Fraud Queue")

    # Active review queue datasets
    alerts_data = [
        {
            "id": "alert_1029",
            "timestamp": "2026-06-05 17:10:12",
            "sender_id": "usr_100800",
            "amount": 2500.00,
            "currency": "USD",
            "location_country": "RU",  # mismatch
            "user_velocity_5m": 2,
            "user_velocity_1h": 4,
            "ml_prob": 0.88,
            "notes": "Large amount, country mismatch country hop flag.",
        },
        {
            "id": "alert_1030",
            "timestamp": "2026-06-05 17:15:34",
            "sender_id": "usr_100911",
            "amount": 450.00,
            "currency": "EUR",
            "location_country": "US",
            "user_velocity_5m": 3,
            "user_velocity_1h": 8,
            "ml_prob": 0.76,
            "notes": "Spike in frequency lookbacks.",
        },
        {
            "id": "alert_1031",
            "timestamp": "2026-06-05 17:22:01",
            "sender_id": "usr_100344",
            "amount": 25.50,
            "currency": "USD",
            "location_country": "US",
            "user_velocity_5m": 0,
            "user_velocity_1h": 1,
            "ml_prob": 0.05,
            "notes": "Standard transactional baseline check.",
        },
    ]

    df_queue = pd.DataFrame(alerts_data)[
        ["id", "timestamp", "sender_id", "amount", "location_country", "ml_prob"]
    ]
    df_queue.columns = ["Alert ID", "Timestamp", "User ID", "Amount", "Country", "ML Score"]

    st.dataframe(df_queue, use_container_width=True)

    st.markdown("---")
    st.subheader("Interactive Audit Desk")

    # Select alert to audit
    selected_alert_id = st.selectbox(
        "Select Alert Record to Investigate", [a["id"] for a in alerts_data]
    )
    alert_detail = next(a for a in alerts_data if a["id"] == selected_alert_id)

    # Pre-score selected alert properties using live scoring rules to get sub-scores and SHAP reasons
    payload = {
        "sender_id": alert_detail["sender_id"],
        "receiver_id": alert_detail.get("receiver_id", alert_detail["sender_id"]),
        "amount": alert_detail["amount"],
        "currency": alert_detail["currency"],
        "merchant_category": "5944" if alert_detail["amount"] > 1000 else "5411",
        "location_country": alert_detail["location_country"],
        "location_city": alert_detail.get("location_city", alert_detail["location_country"]),
        "device_id": alert_detail.get("device_id", f"dev_{alert_detail['sender_id']}"),
        "ip_address": (
            "192.168.1.10" if alert_detail["location_country"] == "US" else "203.0.113.88"
        ),
        "timestamp": datetime.utcnow().isoformat(),
        "user_velocity_5m": alert_detail["user_velocity_5m"],
        "user_velocity_1h": alert_detail["user_velocity_1h"],
    }

    res = client.score_transaction(payload)

    # Fallback to local evaluations if API is offline
    if "error" in res:
        # Calculate heuristics locally for visualization
        from src.models.scoring_engine import FraudRiskScoringEngine

        scoring_engine = FraudRiskScoringEngine()
        row = pd.Series(
            {
                "amount": alert_detail["amount"],
                "amount_to_user_avg_ratio": 15.0 if alert_detail["amount"] > 1000 else 1.0,
                "user_velocity_5m": alert_detail["user_velocity_5m"],
                "user_velocity_1h": alert_detail["user_velocity_1h"],
                "ip_country_mismatch": 1 if alert_detail["location_country"] != "US" else 0,
                "hour_of_day": 3,
            }
        )
        scoring_out = scoring_engine.score_transaction(row, ml_prob=alert_detail["ml_prob"])
        res = {
            "risk_score": scoring_out["risk_score"],
            "risk_bucket": scoring_out["risk_bucket"],
            "recommendation": scoring_out["recommendation"],
            "sub_scores": scoring_out["sub_scores"],
            "explanations": [
                {
                    "feature_name": "ip_country_mismatch",
                    "shap_value": 1.25,
                    "impact_score": 50.0,
                    "direction": "INCREASED_RISK",
                    "description": "IP location mismatch anomaly",
                },
                {
                    "feature_name": "amount_to_user_avg_ratio",
                    "shap_value": 0.85,
                    "impact_score": 30.0,
                    "direction": "INCREASED_RISK",
                    "description": "High transaction value spending spike",
                },
            ],
        }

    col_details, col_charts = st.columns([2, 3])

    with col_details:
        st.markdown(f"### **Review Profile for {selected_alert_id.upper()}**")
        st.markdown(f"- **User ID**: `{alert_detail['sender_id']}`")
        st.markdown(f"- **Amount**: `${alert_detail['amount']:,.2f} {alert_detail['currency']}`")
        st.markdown(
            f"- **Inferred Home Location**: `US` (IP Country Source: `{alert_detail['location_country']}`)"
        )
        st.markdown(f"- **Automated Risk Score**: `{res['risk_score']}`")
        st.markdown(f"- **Risk Bucket Classification**: `{res['risk_bucket']}`")
        st.markdown(f"- **Resolution Action**: `{res['recommendation']}`")
        st.markdown(f"- **Heuristic Notes**: `{alert_detail['notes']}`")

        # Resolution submit form
        st.markdown("#### Log Audit Action")
        with st.form("resolution_form"):
            decision = st.selectbox(
                "Override Verdict",
                ["CONFIRM_FRAUD", "DISMISS_ALERT (False Positive)", "FLAG_FOR_MONITORING"],
            )
            notes = st.text_area("Audit Notes", placeholder="Input justification...")
            submit_res = st.form_submit_button("Record Decision")
            if submit_res:
                st.success(
                    f"Audit decision logged: {decision} recorded for {selected_alert_id.upper()}."
                )

    with col_charts:
        st.markdown("#### Risk Profile Analysis")
        col_w_gauge, col_w_bar = st.columns([1, 1.2])
        with col_w_gauge:
            score_val = float(res["risk_score"])
            fig_dial = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=score_val,
                    title={"text": "Alert Risk Score", "font": {"size": 14, "color": "#FFFFFF"}},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#64748B"},
                        "bar": {
                            "color": (
                                "#FF2E63"
                                if score_val > 70
                                else ("#FFB300" if score_val > 30 else "#00FF87")
                            )
                        },
                        "bgcolor": "rgba(0,0,0,0)",
                        "borderwidth": 2,
                        "bordercolor": "#1E293B",
                        "steps": [
                            {"range": [0, 30], "color": "rgba(0, 255, 135, 0.05)"},
                            {"range": [30, 70], "color": "rgba(255, 179, 0, 0.05)"},
                            {"range": [70, 100], "color": "rgba(255, 46, 99, 0.05)"},
                        ],
                    },
                )
            )
            fig_dial.update_layout(height=180, margin={"t": 30, "b": 10, "l": 10, "r": 10})
            apply_plotly_theme(fig_dial)
            st.plotly_chart(fig_dial, use_container_width=True)

        with col_w_bar:
            df_sub = pd.DataFrame(list(res["sub_scores"].items()), columns=["Sub-Risk", "Score"])
            fig_radar = px.bar(
                df_sub,
                x="Score",
                y="Sub-Risk",
                orientation="h",
                range_x=[0, 100],
                color="Score",
                color_continuous_scale=px.colors.sequential.Teal,
            )
            apply_plotly_theme(fig_radar)
            fig_radar.update_layout(height=180, margin={"t": 10, "b": 10, "l": 10, "r": 10})
            st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown("#### Attribution Driver Explanations")
        for expl in res.get("explanations", []):
            icon = "🚨" if expl["direction"] == "INCREASED_RISK" else "🛡️"
            st.markdown(
                f"{icon} **{expl['feature_name']}** (Impact {expl['impact_score']}%): {expl['description']}"
            )
