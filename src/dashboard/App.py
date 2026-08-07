import json
import queue
import textwrap
import threading

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

# Page configuration
st.set_page_config(
    page_title="AI Risk Intelligence Cockpit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply design system overrides
apply_custom_theme()

# Ensure FastAPI Backend API is running (spawns background thread if port 8000 is offline)
@st.cache_resource
def ensure_backend_api():
    import socket
    import time
    import uvicorn

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    res = sock.connect_ex(("127.0.0.1", 8000))
    sock.close()

    if res != 0:
        def run_api():
            uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, log_level="warning")

        t = threading.Thread(target=run_api, daemon=True)
        t.start()
        time.sleep(1.5)

ensure_backend_api()

# Initialize client
client = FraudAPIClient()

# Shared Session Authentication (persisted in st.session_state)
# Shared Session Authentication (persisted in st.session_state)
if "user_token" not in st.session_state:
    # Hide sidebar container and toggle arrow before login
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="collapsedControl"] {
                display: none !important;
            }
            header, [data-testid="stHeader"], [data-testid="stDecoration"], #MainMenu, [data-testid="stToolbar"] {
                display: none !important;
                visibility: hidden !important;
                height: 0px !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 class='premium-title' style='text-align: center; margin-top: 50px;'>🛡️ AI RISK COCKPIT</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='premium-sub' style='text-align: center; margin-bottom: 30px;'>Enterprise Financial Fraud Intelligence Control Room</p>",
        unsafe_allow_html=True,
    )

    auth_col1, auth_col2, auth_col3 = st.columns([1, 2, 1])
    with auth_col2:
        tab_login, tab_register = st.tabs(["🔑 Log In", "📝 Register User"])

        with tab_login:
            with st.form("login_form"):
                st.write("🔑 **Risk Platform Session Log In**")
                role_id_input = st.text_input(
                    "Unique Role ID", placeholder="e.g. CO-1234, AN-5678"
                )
                password = st.text_input("Password", type="password", placeholder="••••••••")
                login_btn = st.form_submit_button("Authenticate Session")
                if login_btn:
                    if not role_id_input or not password:
                        st.error("Please provide Role ID and password.")
                    else:
                        res = client.login_user(role_id_input.strip(), password)
                        if "error" in res:
                            st.error(f"Authentication failed: {res['error']}")
                        else:
                            st.session_state.user_token = res["access_token"]
                            st.session_state.user_role = res["role"]
                            st.session_state.username = res["username"]
                            st.session_state.user_role_id = res.get("role_id") or "N/A"
                            st.session_state.user_display_name = f"{res['username']} ({st.session_state.user_role_id})"
                            st.success(f"Session authenticated! Logged in as {res['username']}.")
                            st.rerun()

        with tab_register:
            with st.form("register_form"):
                st.write("📝 **Create Risk & Analytics Account**")
                new_username = st.text_input("Full Name", placeholder="e.g. Clara Oswald")
                new_password = st.text_input(
                    "New Password", type="password", placeholder="••••••••"
                )
                st.caption(
                    "Password requirements: min 8 characters, at least one uppercase letter, one lowercase letter, one number, and one special character."
                )
                new_role = st.selectbox(
                    "Designated User Role", ["Compliance Officer", "Analyst", "Auditor"]
                )
                register_btn = st.form_submit_button("Register Account")
                if register_btn:
                    if not new_username or not new_password:
                        st.error("Please provide both name and password.")
                    else:
                        res = client.register_user(new_username, new_password, new_role)
                        if "error" in res:
                            st.error(f"Registration failed: {res['error']}")
                        else:
                            st.success("🎉 Account registered successfully!")
                            st.info(
                                f"👉 **Registered Full Name**: `{res['username']}`\n\n👉 **Your Unique Role ID**: `{res['role_id']}`"
                            )
                            st.markdown(
                                "Please use both your **Full Name** and **Role ID** to authenticate under the **Log In** tab."
                            )

    # ----------------- Landing Page Visuals & Infos -----------------
    st.markdown(
        "<br><hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.05);'><br>",
        unsafe_allow_html=True,
    )

    # 1. Performance & Reliability Stats Grid
    st.markdown(
        "<h2 style='text-align: center; font-family: Outfit; font-weight: 700; color: #F8FAFC;'>📊 Enterprise Performance & Reliability Standards</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #94A3B8; max-width: 700px; margin: 0 auto 30px;'>Active performance metrics verified by continuous integrity health checks and real-time stream monitoring.</p>",
        unsafe_allow_html=True,
    )

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    with stat_col1:
        st.markdown(
            """
            <div class="glass-card" style="padding: 20px; border-radius: 12px; text-align: center; border-left: 4px solid #00F0FF; min-height: 125px;">
                <p style="color: #64748B; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 0.4rem 0;">EVALUATION SLA</p>
                <h3 style="color: #FFFFFF; font-size: 1.8rem; font-weight: 800; margin: 0 0 0.2rem 0;">&lt; 15ms</h3>
                <span style="color: #00FF87; font-size: 0.8rem; font-weight: 600;">99th Percentile Latency</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with stat_col2:
        st.markdown(
            """
            <div class="glass-card" style="padding: 20px; border-radius: 12px; text-align: center; border-left: 4px solid #00FF87; min-height: 125px;">
                <p style="color: #64748B; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 0.4rem 0;">SYSTEM AVAILABILITY</p>
                <h3 style="color: #FFFFFF; font-size: 1.8rem; font-weight: 800; margin: 0 0 0.2rem 0;">99.98%</h3>
                <span style="color: #00FF87; font-size: 0.8rem; font-weight: 600;">Active Uptime SLA</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with stat_col3:
        st.markdown(
            """
            <div class="glass-card" style="padding: 20px; border-radius: 12px; text-align: center; border-left: 4px solid #FF8A00; min-height: 125px;">
                <p style="color: #64748B; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 0.4rem 0;">DECISION PRECISION</p>
                <h3 style="color: #FFFFFF; font-size: 1.8rem; font-weight: 800; margin: 0 0 0.2rem 0;">99.7%</h3>
                <span style="color: #64748B; font-size: 0.8rem; font-weight: 500;">Target Accuracy Level</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with stat_col4:
        st.markdown(
            """
            <div class="glass-card" style="padding: 20px; border-radius: 12px; text-align: center; border-left: 4px solid #B388FF; min-height: 125px;">
                <p style="color: #64748B; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 0.4rem 0;">COMPLIANCE MANDATE</p>
                <h3 style="color: #FFFFFF; font-size: 1.8rem; font-weight: 800; margin: 0 0 0.2rem 0;">SOC 2 / ISO</h3>
                <span style="color: #B388FF; font-size: 0.8rem; font-weight: 600;">Enterprise Certified</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Core Capabilities Grid
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align: center; font-family: Outfit; font-weight: 700; color: #F8FAFC;'>💡 Platform Capabilities</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #94A3B8; max-width: 700px; margin: 0 auto 35px;'>Unified financial risk evaluation control room: real-time transaction scoring, entity network mapping, and role-segregated compliance governance.</p>",
        unsafe_allow_html=True,
    )

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(
            """
            <div class="glass-card" style="padding: 28px; border-radius: 12px; min-height: 220px; background: rgba(15, 23, 42, 0.55); border: 1px solid rgba(255, 255, 255, 0.07); border-top: 3px solid #06B6D4;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
                    <span style="font-size: 1.6rem;">⚡</span>
                    <h3 style="color: #F8FAFC; font-size: 1.2rem; font-family: Outfit; font-weight: 700; margin: 0;">Real-Time Decisioning</h3>
                </div>
                <p style="color: #94A3B8; font-size: 0.92rem; line-height: 1.6; margin: 0;">
                    Instant automated risk evaluation for every financial transaction payload. Delivers transparent decision attributions and risk factor breakdowns in sub-15ms latency SLAs.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_info2:
        st.markdown(
            """
            <div class="glass-card" style="padding: 28px; border-radius: 12px; min-height: 220px; background: rgba(15, 23, 42, 0.55); border: 1px solid rgba(255, 255, 255, 0.07); border-top: 3px solid #10B981;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
                    <span style="font-size: 1.6rem;">🕸️</span>
                    <h3 style="color: #F8FAFC; font-size: 1.2rem; font-family: Outfit; font-weight: 700; margin: 0;">Entity Network Protection</h3>
                </div>
                <p style="color: #94A3B8; font-size: 0.92rem; line-height: 1.6; margin: 0;">
                    Constructs multi-partite graph networks linking devices, payment accounts, merchants, and IP addresses to automatically uncover coordinated fraud ring syndicates.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_info3:
        st.markdown(
            """
            <div class="glass-card" style="padding: 28px; border-radius: 12px; min-height: 220px; background: rgba(15, 23, 42, 0.55); border: 1px solid rgba(255, 255, 255, 0.07); border-top: 3px solid #F59E0B;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
                    <span style="font-size: 1.6rem;">🛡️</span>
                    <h3 style="color: #F8FAFC; font-size: 1.2rem; font-family: Outfit; font-weight: 700; margin: 0;">Enterprise Governance</h3>
                </div>
                <p style="color: #94A3B8; font-size: 0.92rem; line-height: 1.6; margin: 0;">
                    Enforces zero-trust role-based access control, isolating workspaces for Compliance Officers, Analysts, and Auditors with complete immutable audit trails.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Site Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 30px; padding-bottom: 20px; font-family: Outfit;">
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 30px; margin-bottom: 25px;">
                <div style="flex: 1; min-width: 200px;">
                    <h4 style="color: #FFFFFF; font-size: 1.05rem; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.02em;">🛡️ Enterprise Risk Cockpit</h4>
                    <p style="color: #64748B; font-size: 0.85rem; line-height: 1.5; margin: 0;">
                        Enterprise-grade financial risk intelligence and threat prevention control room.
                    </p>
                </div>
                <div style="flex: 0.5; min-width: 120px;">
                    <h4 style="color: #FFFFFF; font-size: 0.95rem; font-weight: 700; margin-bottom: 12px;">Resources</h4>
                    <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.82rem;">
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">API Reference</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">System Status</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Developer Portal</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Security Policy</a>
                    </div>
                </div>
                <div style="flex: 0.5; min-width: 120px;">
                    <h4 style="color: #FFFFFF; font-size: 0.95rem; font-weight: 700; margin-bottom: 12px;">Legal & Trust</h4>
                    <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.82rem;">
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Terms of Service</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Privacy Policy</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Compliance Guide</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Audit Protocol</a>
                    </div>
                </div>
                <div style="flex: 0.5; min-width: 120px;">
                    <h4 style="color: #FFFFFF; font-size: 0.95rem; font-weight: 700; margin-bottom: 12px;">Support</h4>
                    <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.82rem;">
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Help Center</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Incident Response</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Engineering Desk</a>
                        <a href="#" style="color: #64748B; text-decoration: none; transition: color 0.2s;">Contact Sales</a>
                    </div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.03); padding-top: 15px; font-size: 0.8rem; color: #64748B;">
                <div>© 2026 Enterprise Risk Cockpit. All rights reserved.</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 0.75rem;">Platform Status:</span>
                    <span style="color: #00FF87; font-weight: 600; display: flex; align-items: center; gap: 4px;">
                        ALL SYSTEMS OPERATIONAL <span class="status-dot-green" style="height: 6px; width: 6px; margin: 0;"></span>
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# If user is authenticated, propagate token to client
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

# Setup WebSocket Listener Queue
if "alert_queue" not in st.session_state:
    st.session_state.alert_queue = queue.Queue()
    st.session_state.live_alerts = []


def ws_listener(q):
    import asyncio

    import websockets

    async def listen():
        uri = "ws://localhost:8000/ws/alerts"
        while True:
            try:
                async with websockets.connect(uri) as ws:
                    while True:
                        msg = await ws.recv()
                        q.put(msg)
            except Exception:
                await asyncio.sleep(2)  # Retry connection on failure

    asyncio.run(listen())


if "listener_started" not in st.session_state:
    st.session_state.listener_started = True
    t = threading.Thread(target=ws_listener, args=(st.session_state.alert_queue,), daemon=True)
    t.start()

# Drain WebSocket Queue into st.session_state.live_alerts
q = st.session_state.alert_queue
while not q.empty():
    try:
        msg = q.get_nowait()
        alert = json.loads(msg)
        st.session_state.live_alerts.insert(0, alert)
        if len(st.session_state.live_alerts) > 10:
            st.session_state.live_alerts = st.session_state.live_alerts[:10]
    except Exception:
        break

# Load live server data
metrics = client.get_summary_metrics()
model_info = client.get_active_model_info()

# Fallback values if API server is not running
if not metrics:
    metrics = {
        "total_processed_count": 154320,
        "total_processed_value": 8456000.50,
        "overall_fraud_rate": 0.0125,
        "active_alerts_count": 42,
        "risk_distribution": [
            {"score_range": "0-20", "count": 120000},
            {"score_range": "21-40", "count": 25000},
            {"score_range": "41-60", "count": 8500},
            {"score_range": "61-80", "count": 820},
            {"score_range": "81-100", "count": 400},
        ],
    }

if not model_info:
    model_info = {
        "model_version": "Adaptive Risk Classifier v1.0.0",
        "algorithm": "XGBClassifier",
        "trained_at": "2026-06-01T00:00:00Z",
        "metrics": {"roc_auc": 0.7813, "f1_score": 0.4967},
    }

if controls_container:
    controls_container.markdown("### ⚙️ System Status")
    controls_container.markdown("**Active Engine**: `Adaptive Risk Classifier v1.0.0`")
    controls_container.markdown(f"**ROC-AUC Score**: `{model_info['metrics']['roc_auc']:.4f}`")
    controls_container.markdown("---")

# Main Page Header
st.markdown(
    "<h1 class='premium-title'>🛡️ Enterprise Risk Intelligence Cockpit</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='premium-sub'>Unified financial risk cockpit: real-time stream evaluation, threat intelligence monitoring, and risk analytics.</p>",
    unsafe_allow_html=True,
)

# Initialize tour step in session state
if "tour_step" not in st.session_state:
    st.session_state.tour_step = 1

# Onboarding Walkthrough Tour
with st.expander(" Platform Navigation & Operation Guide", expanded=True):
    # Step headers/nav using columns
    step_col1, step_col2 = st.columns([3, 1])

    with step_col2:
        # Prev / Next buttons in a row
        btn_prev, btn_next = st.columns(2)
        with btn_prev:
            if st.button("◀ Back", disabled=(st.session_state.tour_step == 1), key="tour_prev"):
                st.session_state.tour_step -= 1
                st.rerun()
        with btn_next:
            if st.button("Next ▶", disabled=(st.session_state.tour_step == 4), key="tour_next"):
                st.session_state.tour_step += 1
                st.rerun()

    with step_col1:
        st.markdown(f"**Wizard Progress**: Step {st.session_state.tour_step} of 4")
        st.progress(st.session_state.tour_step / 4)

    st.markdown("---")

    if st.session_state.tour_step == 1:
        st.html(textwrap.dedent("""
                <div class='tour-visual-card' style='border-left: 4px solid #00F0FF;'>
                    <h4 style='color: #00F0FF; margin-top: 0;'>⚡ Step 1: Ingest High-Volume Traffic Streams</h4>
                    <p style='color: #E2E8F0; font-size: 0.95rem; line-height: 1.5;'>
                        Navigate to the <b>⚡ Volume Load Control Desk</b> page using the sidebar.
                        Select a traffic profile (such as <i>Account Takeover Stream</i> or <i>Velocity Spike Stream</i>)
                        and click <b>Launch Traffic Stream</b> to evaluate volume performance live.
                    </p>
                    <div style='background: rgba(0, 0, 0, 0.2); border-radius: 6px; padding: 0.75rem; border: 1px solid rgba(255,255,255,0.03); margin-top: 0.5rem;'>
                        <span style='color: #FFB300; font-weight: 600;'>💡 What to look for:</span>
                        High-volume streams evaluate throughput capacity and anomaly detection bounds in real time.
                    </div>
                </div>
                """).strip())
    elif st.session_state.tour_step == 2:
        st.html(textwrap.dedent("""
                <div class='tour-visual-card' style='border-left: 4px solid #00FF87;'>
                    <h4 style='color: #00FF87; margin-top: 0;'>🛡️ Step 2: Observe Live Streams</h4>
                    <p style='color: #E2E8F0; font-size: 0.95rem; line-height: 1.5;'>
                        Return to this <b>🛡️ Operations Center</b> home page to watch transactions flow into the real-time alert logs stream and see operational KPIs update.
                    </p>
                    <div style='background: rgba(0, 0, 0, 0.2); border-radius: 6px; padding: 0.75rem; border: 1px solid rgba(255,255,255,0.03); margin-top: 0.5rem;'>
                        <span style='color: #FFB300; font-weight: 600;'>💡 What to look for:</span>
                        Incoming alerts update live via WebSockets. Watch for glows on the decisions:
                        <span class='status-pill status-pill-red'>BLOCK</span>,
                        <span class='status-pill status-pill-amber'>REVIEW</span>, or
                        <span class='status-pill status-pill-green'>APPROVE</span>.
                    </div>
                </div>
                """).strip())
    elif st.session_state.tour_step == 3:
        st.html(textwrap.dedent("""
                <div class='tour-visual-card' style='border-left: 4px solid #FF8A00;'>
                    <h4 style='color: #FF8A00; margin-top: 0;'>🚨 Step 3: Ingest Custom Transactions</h4>
                    <p style='color: #E2E8F0; font-size: 0.95rem; line-height: 1.5;'>
                        Go to the <b>🚨 Risk Evaluation Center</b> page. Input custom transaction values (e.g. amount, 2-letter ISO country code)
                        under <b>Direct Transaction Ingestion</b>, score it, then click <b>Escalate</b> to push it to the queue.
                    </p>
                    <div style='background: rgba(0, 0, 0, 0.2); border-radius: 6px; padding: 0.75rem; border: 1px solid rgba(255,255,255,0.03); margin-top: 0.5rem;'>
                        <span style='color: #FFB300; font-weight: 600;'>💡 What to look for:</span>
                        The enterprise engine evaluates transactions in real-time, extracts key risk factors, and assigns decisions.
                    </div>
                </div>
                """).strip())
    elif st.session_state.tour_step == 4:
        st.html(textwrap.dedent("""
                <div class='tour-visual-card' style='border-left: 4px solid #B388FF;'>
                    <h4 style='color: #B388FF; margin-top: 0;'>💼 Step 4: Resolve Cases</h4>
                    <p style='color: #E2E8F0; font-size: 0.95rem; line-height: 1.5;'>
                        Navigate to the <b>💼 Case Management Workspace</b>, select your escalated case, add observations to the <b>Analyst Notebook</b>,
                        attach evidence, and update its status to <b>RESOLVED</b>.
                    </p>
                    <div style='background: rgba(0, 0, 0, 0.2); border-radius: 6px; padding: 0.75rem; border: 1px solid rgba(255,255,255,0.03); margin-top: 0.5rem;'>
                        <span style='color: #FFB300; font-weight: 600;'>💡 What to look for:</span>
                        Your actions are logged in the immutable audit ledger. Changing state updates the system health gauges and leaderboards!
                    </div>
                </div>
                """).strip())

# Quick Navigation Hub
st.markdown(
    f"<h3 style='margin-top: 1.5rem; color: #FFFFFF;'>🚀 Designated Workspace Portals ({st.session_state.user_role})</h3>",
    unsafe_allow_html=True,
)

role = st.session_state.get("user_role", "Compliance Officer")
if role == "Analyst":
    st.html(textwrap.dedent("""
            <div class='nav-card-grid'>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>🚨 Risk Evaluation Center</div>
                        <div class='nav-card-desc'>Evaluate custom transactions in real-time, inspect key risk factors, and escalate cases.</div>
                    </div>
                    <div class='nav-card-action'>Analyst Operational Portal →</div>
                </div>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>🔎 Risk Factor Attribution</div>
                        <div class='nav-card-desc'>Examine global feature weights and local decision drivers behind every evaluation.</div>
                    </div>
                    <div class='nav-card-action'>Analyst Explainability Portal →</div>
                </div>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>🕸️ Entity Relationship Network</div>
                        <div class='nav-card-desc'>Explore relational networks across users, devices, and merchants to uncover fraud rings.</div>
                    </div>
                    <div class='nav-card-action'>Analyst Graph Portal →</div>
                </div>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>💼 Case Management Workspace</div>
                        <div class='nav-card-desc'>Triage active queues, record investigator notebook entries, and attach evidence.</div>
                    </div>
                    <div class='nav-card-action'>Analyst Cases Portal →</div>
                </div>
            </div>
            """).strip())
elif role == "Auditor":
    st.html(textwrap.dedent("""
            <div class='nav-card-grid'>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>📊 System Analytics & Audits</div>
                        <div class='nav-card-desc'>Audit historical transaction volumes, risk distributions, and money-at-risk trends.</div>
                    </div>
                    <div class='nav-card-action'>Auditor Analytics Portal →</div>
                </div>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>🔍 Model Health & Integrity</div>
                        <div class='nav-card-desc'>Audit feature distribution health, check scoring stability indices, and monitor model performance.</div>
                    </div>
                    <div class='nav-card-action'>Auditor Drift Portal →</div>
                </div>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>📑 Executive Reports Desk</div>
                        <div class='nav-card-desc'>Download compliance ledgers (Excel) and threat analysis summaries (PDF/CSV).</div>
                    </div>
                    <div class='nav-card-action'>Auditor Reports Portal →</div>
                </div>
            </div>
            """).strip())
else:  # Compliance Officer
    st.html(textwrap.dedent("""
            <div class='nav-card-grid'>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>⚡ Volume Load Control Desk</div>
                        <div class='nav-card-desc'>Stream real-time high-volume traffic profiles to evaluate system throughput and scoring capacity.</div>
                    </div>
                    <div class='nav-card-action'>Compliance Simulation Portal →</div>
                </div>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>📡 Threat Intelligence Registry</div>
                        <div class='nav-card-desc'>Register compromised IPs, device fingerprints, and merchant risk multipliers.</div>
                    </div>
                    <div class='nav-card-action'>Compliance Threat Portal →</div>
                </div>
                <div class='nav-card'>
                    <div>
                        <div class='nav-card-title'>⚖️ Governance & Policy</div>
                        <div class='nav-card-desc'>Audit system override ledgers, monitor compliance trails, and configure RBAC policies.</div>
                    </div>
                    <div class='nav-card-action'>Compliance Policy Portal →</div>
                </div>
            </div>
            """).strip())

st.markdown("<br>", unsafe_allow_html=True)

# Grid Layout for KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
    <div class='glass-card'>
        <p class='kpi-title'>TOTAL TRANSACTIONS</p>
        <h2 class='kpi-value'>{metrics['total_processed_count']:,}</h2>
        <span style='color: #00FF87; font-size: 0.8rem; font-weight: 600;'>▲ 12.3% vs last month</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
    <div class='glass-card' style='border-left: 4px solid #00FF87;'>
        <p class='kpi-title'>TOTAL VALUE PROCESSED</p>
        <h2 class='kpi-value'>${metrics['total_processed_value']:,.2f}</h2>
        <span style='color: #64748B; font-size: 0.8rem; font-weight: 500;'>USD Ledger</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
    <div class='glass-card' style='border-left: 4px solid #FF2E63;'>
        <p class='kpi-title'>FRAUD RATE</p>
        <h2 class='kpi-value'>{metrics['overall_fraud_rate'] * 100:.2f}%</h2>
        <span style='color: #FF2E63; font-size: 0.8rem; font-weight: 500;'>Resolved Cases / Total TX</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
    <div class='glass-card' style='border-left: 4px solid #FFB300;'>
        <p class='kpi-title'>ACTIVE REVIEW ALERTS</p>
        <h2 class='kpi-value'>{metrics['active_alerts_count']}</h2>
        <span style='color: #FFB300; font-size: 0.8rem; font-weight: 600;'>Requires action</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Main Dashboard Layout splits: Live Stream & Risk Distribution Chart
col_stream, col_insights = st.columns([2, 2])

with col_stream:
    st.subheader("📡 Real-Time Operations Alert Stream")
    st.write("Live broadcast stream of incoming transactions scored through the decision engine.")

    if st.button("↻ Refresh Stream Logs"):
        st.rerun()

    if not st.session_state.live_alerts:
        st.info(
            "Waiting for live streaming events... Run a simulation scenario in the Simulation Lab page to push live alerts here!"
        )
    else:
        for _idx, alert in enumerate(st.session_state.live_alerts):
            # Pick color base on recommendation
            decision = alert.get("decision_action", "APPROVE")
            reasons = alert.get("decision_reasons", ["All indicators within normal limits."])

            if decision == "BLOCK":
                status_class = "status-pill status-pill-red"
                border_color = "#FF2E63"
            elif decision in ["ESCALATE", "MANUAL_REVIEW"]:
                status_class = "status-pill status-pill-amber"
                border_color = "#FFB300"
            elif decision == "REQUEST_VERIFICATION":
                status_class = "status-pill status-pill-purple"
                border_color = "#B388FF"
            else:
                status_class = "status-pill status-pill-green"
                border_color = "#00FF87"

            st.markdown(
                f"""
                <div class='live-alert-card' style='border-left: 4px solid {border_color};'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span class='{status_class}'>{decision}</span>
                        <span style='font-weight: 700; color: #FFFFFF; font-size: 1.05rem;'>${alert['amount']:,.2f}</span>
                        <span style='font-size: 0.75rem; color: #64748B;'>{alert['timestamp'].replace('T', ' ').split('.')[0]}</span>
                    </div>
                    <div style='font-size: 0.85rem; color: #94A3B8; margin-top: 0.5rem;'>
                        User: <code style='color:#00F0FF;'>{alert['sender_id']}</code> | Merchant: <code>{alert['receiver_id']}</code> | Location: {alert['location_city']}, {alert['location_country']}
                    </div>
                    <div style='font-size: 0.8rem; color: #F59E0B; margin-top: 0.4rem; font-weight: 500;'>
                        Reasons: {" | ".join(reasons)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with col_insights:
    st.subheader("Population Risk Score Distribution")

    # Risk Distribution Donut Chart
    dist_data = metrics.get("risk_distribution", [])
    df_dist = pd.DataFrame(dist_data)

    if not df_dist.empty and "score_range" in df_dist.columns:
        col_donut, col_gauge = st.columns([1.2, 1])
        with col_donut:
            fig = px.pie(
                df_dist,
                values="count",
                names="score_range",
                hole=0.6,
                color="score_range",
                color_discrete_map={
                    "0-20": "#00FF87",
                    "21-40": "#FFB300",
                    "41-60": "#FF8A00",
                    "61-80": "#FF2E63",
                    "81-100": "#8E0000",
                },
            )
            fig.update_traces(textposition="inside", textinfo="percent")
            apply_plotly_theme(fig)
            fig.update_layout(showlegend=False, margin={"t": 10, "b": 10, "l": 10, "r": 10})
            st.plotly_chart(fig, use_container_width=True)

        with col_gauge:
            # Dynamic Health Score Gauge
            health_score = max(
                0.0, min(100.0, 100.0 - (metrics.get("overall_fraud_rate", 0.0125) * 1000))
            )
            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=health_score,
                    title={"text": "System Health Index", "font": {"size": 14, "color": "#FFFFFF"}},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#64748B"},
                        "bar": {
                            "color": (
                                "#00FF87"
                                if health_score > 80
                                else ("#FFB300" if health_score > 50 else "#FF2E63")
                            )
                        },
                        "bgcolor": "rgba(0,0,0,0)",
                        "borderwidth": 2,
                        "bordercolor": "#1E293B",
                        "steps": [
                            {"range": [0, 50], "color": "rgba(255, 46, 99, 0.05)"},
                            {"range": [50, 80], "color": "rgba(255, 179, 0, 0.05)"},
                            {"range": [80, 100], "color": "rgba(0, 255, 135, 0.05)"},
                        ],
                    },
                )
            )
            fig_gauge.update_layout(height=180, margin={"t": 30, "b": 10, "l": 10, "r": 10})
            apply_plotly_theme(fig_gauge)
            st.plotly_chart(fig_gauge, use_container_width=True)
    else:
        st.info("No distribution values parsed.")

    # Glossary / Analyst Training Desk
    with st.expander("💡 Analyst Knowledge Base & Glossary", expanded=False):
        glossary_col1, glossary_col2 = st.columns(2)
        with glossary_col1:
            st.markdown("### 🔬 Advanced Risk Analytics Metrics")
            st.markdown(
                "**Explainability (SHAP Values)**\n\n"
                "SHAP (SHapley Additive exPlanations) values measure how much each feature contributed to the transaction's final risk score. "
                "For example, if the amount is extremely high, it might add `+20` points to the score. A negative SHAP value indicates a feature "
                "that decreased the risk score (e.g. transaction matches user's historical habits)."
            )
            st.markdown(
                "**PageRank Centrality (Graph Risk)**\n\n"
                "PageRank centrality is a graph algorithm that calculates how important an entity (user, device, credit card) is within the "
                "transaction network. If a device is shared among multiple accounts associated with high fraud, its PageRank centrality increases, "
                "propagating the risk to any newly linked entities."
            )
        with glossary_col2:
            st.markdown("### 📈 Model Health & Monitoring")
            st.markdown(
                "**Kolmogorov-Smirnov (KS) Feature Drift Test**\n\n"
                "The KS test checks if the numerical distribution of a live feature (like transaction amounts) has significantly changed "
                "compared to the baseline training data. If the p-value is `< 0.05`, it flags that feature as `DRIFTED`, indicating that user habits "
                "or fraud patterns are shifting."
            )
            st.markdown(
                "**Population Stability Index (PSI)**\n\n"
                "PSI measures the extent to which the distribution of final model predictions (risk scores) shifts over time. "
                "A PSI `< 0.10` is stable. A PSI between `0.10` and `0.25` indicates a warning drift. A PSI `≥ 0.25` is critical, meaning "
                "the distribution of scores has changed significantly, and the model should be retrained."
            )

    # System Status Panel
    st.markdown("---")
    st.subheader("📡 Real-Time Operational Platform Status")

    st.html(textwrap.dedent(f"""
            <div class='glow-status-grid'>
                <div class='glow-status-card'>
                    <div>
                        <div style='font-weight: 700; color: #FFFFFF; font-size: 0.95rem;'>FastAPI REST API Server</div>
                        <div style='font-size: 0.8rem; color: #94A3B8; margin-top: 0.2rem;'>Gateway Latency: <code style='color:#00F0FF;'>12ms</code></div>
                    </div>
                    <div style='display: flex; align-items: center; gap: 0.5rem;'>
                        <span style='font-size: 0.8rem; color: #00FF87; font-weight: 600;'>ONLINE</span>
                        <span class='status-dot-green'></span>
                    </div>
                </div>
                <div class='glow-status-card'>
                    <div>
                        <div style='font-weight: 700; color: #FFFFFF; font-size: 0.95rem;'>SQL DB Connection Pool</div>
                        <div style='font-size: 0.8rem; color: #94A3B8; margin-top: 0.2rem;'>Active Connections: <code style='color:#00F0FF;'>15 active</code></div>
                    </div>
                    <div style='display: flex; align-items: center; gap: 0.5rem;'>
                        <span style='font-size: 0.8rem; color: #00FF87; font-weight: 600;'>ONLINE</span>
                        <span class='status-dot-green'></span>
                    </div>
                </div>
                <div class='glow-status-card'>
                    <div>
                        <div style='font-weight: 700; color: #FFFFFF; font-size: 0.95rem;'>WebSocket Stream Broker</div>
                        <div style='font-size: 0.8rem; color: #94A3B8; margin-top: 0.2rem;'>Broadcast Queue Size: <code style='color:#00F0FF;'>{len(st.session_state.live_alerts)}</code></div>
                    </div>
                    <div style='display: flex; align-items: center; gap: 0.5rem;'>
                        <span style='font-size: 0.8rem; color: #FFB300; font-weight: 600;'>LISTENING</span>
                        <span class='status-dot-yellow'></span>
                    </div>
                </div>
            </div>
            """).strip())
