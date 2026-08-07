import time
from datetime import UTC, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme
from src.models.synthetic_engine import SyntheticFraudEngine

st.set_page_config(
    page_title="Volume Load Desk",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_theme("#2E1E0A")

st.markdown(
    "<h1 class='premium-title'>⚡ Traffic Ingestion & Volume Load Desk</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p class='premium-sub'>Stream real-time high-volume traffic profiles to evaluate system throughput, scoring capacity, and risk decision bounds.</p>",
    unsafe_allow_html=True,
)

if "user_token" not in st.session_state and "session_token" in st.query_params:
    st.session_state.user_token = st.query_params["session_token"]
    st.session_state.user_role = st.query_params.get("role", "Compliance Officer")
    st.session_state.username = st.query_params.get("username", "User")
    st.session_state.user_role_id = st.query_params.get("role_id", "N/A")
    st.session_state.user_display_name = f"{st.session_state.username} ({st.session_state.user_role_id})"

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

# Sidebar configuration
scenario = "Standard Volume Stream"
user_id = "usr_sim_889"
delay = 0.5
run_sim = False

if controls_container:
    controls_container.markdown("### ⚡ Traffic Profile Configuration")
    scenario = controls_container.selectbox(
        "Select Traffic Profile Stream",
        [
            "Account Takeover Stream (ATO)",
            "Card Verification Stream (Micro)",
            "High-Velocity Stream",
            "Multi-Account Device Stream",
            "Location Anomaly Stream",
            "Merchant Adjustment Stream",
            "Standard Volume Stream",
        ],
    )

    user_id = controls_container.text_input("Target User ID (Optional)", "usr_sim_889")
    delay = controls_container.slider("Inter-transaction Delay (seconds)", 0.0, 2.0, 0.5)

    engine = SyntheticFraudEngine()

    role = st.session_state.get("user_role", "Compliance Officer")
    if role != "Compliance Officer":
        controls_container.warning(
            "⚠️ Access Denied: Volume Load Desk execution is restricted to Compliance Officers."
        )
        st.info("Select a scenario and toggle user role in the sidebar to test.")
    else:
        run_sim = controls_container.button("Launch Traffic Stream", type="primary", use_container_width=True)

if role == "Compliance Officer" and run_sim:
    st.write("---")
    st.subheader(f"⚡ Processing Traffic Stream: {scenario}")

    events = []
    now_dt = datetime.now(UTC).replace(tzinfo=None)

    # Map selected scenario to SyntheticFraudEngine method
    with st.spinner("Initializing traffic stream..."):
        if scenario == "Account Takeover Stream (ATO)":
            events = engine.generate_account_takeover(user_id, now_dt)
        elif scenario == "Card Verification Stream (Micro)":
            events = engine.generate_card_testing(user_id, now_dt)
        elif scenario == "High-Velocity Stream":
            events = engine.generate_velocity_attack(user_id, now_dt)
        elif scenario == "Multi-Account Device Stream":
            events = engine.generate_device_spoofing(now_dt)
        elif scenario == "Location Anomaly Stream":
            events = engine.generate_location_anomaly(user_id, now_dt)
        elif scenario == "Merchant Adjustment Stream":
            events = engine.generate_merchant_abuse(now_dt)
        else:
            # Benign
            events = [engine.generate_benign_transaction(user_id, now_dt) for _ in range(5)]

    if not events:
        st.error("No events generated for this scenario.")
    else:
        st.info(f"Generated {len(events)} synthetic events. Streaming to scoring pipeline...")

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, event in enumerate(events):
            status_text.text(
                f"Scoring transaction {idx+1}/{len(events)}: ID={event['transaction_id']}..."
            )

            # Format timestamp as string for JSON serialization
            payload = event.copy()
            if isinstance(payload["timestamp"], datetime):
                payload["timestamp"] = payload["timestamp"].isoformat()

            # Post transaction to API endpoint
            res = client.score_transaction(payload)

            if "error" in res:
                results.append(
                    {
                        "tx_id": event["transaction_id"],
                        "sender": event["sender_id"],
                        "amount": event["amount"],
                        "location": f"{event['location_city']}, {event['location_country']}",
                        "status": "API_ERROR",
                        "decision": "N/A",
                        "reasons": [res["error"]],
                        "risk_score": 0.0,
                    }
                )
            else:
                results.append(
                    {
                        "tx_id": event["transaction_id"],
                        "sender": event["sender_id"],
                        "amount": event["amount"],
                        "location": f"{event['location_city']}, {event['location_country']}",
                        "status": res.get("recommendation", "ALLOW"),
                        "decision": res.get("decision_action", "APPROVE"),
                        "reasons": res.get("decision_reasons", ["Benign transaction profile."]),
                        "risk_score": res.get("risk_score", 0.0),
                    }
                )

            progress_bar.progress((idx + 1) / len(events))
            time.sleep(delay)

        status_text.text("Simulation execution complete!")

        # Calculate metrics
        df_res = pd.DataFrame(results)
        total_txs = len(df_res)
        avg_score = df_res["risk_score"].mean()

        # Action distribution
        approved = len(df_res[df_res["decision"] == "APPROVE"])
        blocked = len(df_res[df_res["decision"] == "BLOCK"])
        flagged = len(
            df_res[df_res["decision"].isin(["MANUAL_REVIEW", "REQUEST_VERIFICATION", "ESCALATE"])]
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f"""
                <div class='glass-card' style='border-left: 4px solid #00F0FF;'>
                    <div class='kpi-title'>Total Simulated</div>
                    <div class='kpi-value'>{total_txs}</div>
                    <div class='status-pill status-pill-amber' style='margin-top: 0.5rem; color: #00F0FF !important; background: rgba(0, 240, 255, 0.08) !important; border-color: rgba(0, 240, 255, 0.15) !important;'>Attack Vector Stream</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""
                <div class='glass-card' style='border-left: 4px solid #00FF87;'>
                    <div class='kpi-title'>Approved</div>
                    <div class='kpi-value'>{approved}</div>
                    <div class='status-pill status-pill-green' style='margin-top: 0.5rem;'>{approved/total_txs*100:.1f}% Pass Rate</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""
                <div class='glass-card' style='border-left: 4px solid #FF2E63;'>
                    <div class='kpi-title'>Blocked (Threats)</div>
                    <div class='kpi-value'>{blocked}</div>
                    <div class='status-pill status-pill-red' style='margin-top: 0.5rem;'>{blocked/total_txs*100:.1f}% Block Rate</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f"""
                <div class='glass-card' style='border-left: 4px solid #B388FF;'>
                    <div class='kpi-title'>Average Risk Score</div>
                    <div class='kpi-value'>{avg_score:.1f}%</div>
                    <div class='status-pill status-pill-purple' style='margin-top: 0.5rem;'>System Calibration</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("#### Decision Action Breakdown")
            df_action = pd.DataFrame(
                [
                    {"Action": "Approved", "Count": approved},
                    {"Action": "Blocked", "Count": blocked},
                    {"Action": "Flagged / Review", "Count": flagged},
                ]
            )
            fig_action = px.pie(
                df_action,
                values="Count",
                names="Action",
                hole=0.6,
                color="Action",
                color_discrete_map={
                    "Approved": "#00FF87",
                    "Blocked": "#FF2E63",
                    "Flagged / Review": "#FFB300",
                },
            )
            fig_action.update_traces(textposition="inside", textinfo="percent+value")
            apply_plotly_theme(fig_action)
            fig_action.update_layout(
                showlegend=True, margin={"t": 20, "b": 10, "l": 10, "r": 10}, height=240
            )
            st.plotly_chart(fig_action, use_container_width=True)

        with col_c2:
            st.markdown("#### Transaction Risk Scores")
            fig_scores = px.bar(
                df_res,
                x=df_res.index + 1,
                y="risk_score",
                color="decision",
                color_discrete_map={
                    "APPROVE": "#00FF87",
                    "BLOCK": "#FF2E63",
                    "MANUAL_REVIEW": "#FFB300",
                    "REQUEST_VERIFICATION": "#B388FF",
                    "ESCALATE": "#FF8A00",
                },
                labels={"x": "Sequence", "risk_score": "Risk Score (%)"},
                title="Risk Score by Transaction Sequence",
            )
            apply_plotly_theme(fig_scores)
            fig_scores.update_layout(
                showlegend=False, margin={"t": 30, "b": 10, "l": 10, "r": 10}, height=240
            )
            st.plotly_chart(fig_scores, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Detailed breakdown table
        st.write("### Simulation Execution Log")

        display_rows = []
        for idx, row in df_res.iterrows():
            reasons_str = (
                " | ".join(row["reasons"])
                if isinstance(row["reasons"], list)
                else str(row["reasons"])
            )
            display_rows.append(
                {
                    "Seq": idx + 1,
                    "Transaction ID": row["tx_id"],
                    "Sender": row["sender"],
                    "Amount": f"${row['amount']:.2f}",
                    "Location": row["location"],
                    "ML Recommendation": row["status"],
                    "Decision Action": row["decision"],
                    "Risk Score": f"{row['risk_score']:.1f}%",
                    "Reason Codes": reasons_str,
                }
            )

        st.dataframe(pd.DataFrame(display_rows), use_container_width=True)
else:
    st.info(
        "Select a scenario from the sidebar and click 'Launch Traffic Stream' to start stress testing the platform."
    )
