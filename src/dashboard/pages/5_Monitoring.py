import textwrap
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

# Page Configuration
st.set_page_config(page_title="Model Monitoring & Drift Detection", page_icon="🔍", layout="wide")

apply_custom_theme("#0A2A1E")

if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

if st.session_state.user_role != "Auditor":
    st.error("⚠️ Access Denied: This workspace is designated exclusively for Auditor users.")
    st.stop()
client = FraudAPIClient()
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

# Load Model Monitoring Report
with st.spinner("Fetching monitoring analytics report..."):
    report = client.get_monitoring_report()

# Fallback UI if report isn't returned from API
if not report:
    st.error("Could not fetch the active monitoring report from the API server.")
    st.info("Ensure the FastAPI backend is running and correct environment keys are configured.")
    st.stop()


# Helper to format ISO datetimes
def format_datetime(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return dt_str


# Sidebar Configuration
run_drift_check = False
if controls_container:
    controls_container.markdown("### 🔍 Monitoring Desk")
    controls_container.markdown(f"**Last Checked**:\n`{format_datetime(report['last_run'])}`")
    run_drift_check = controls_container.button("🔄 Run Distribution Check Now", use_container_width=True)
    controls_container.info(
        "This system compares current live inference distributions (last 30 days) against "
        "training distribution baselines to identify feature and label shifts."
    )

if run_drift_check:
    with st.spinner("Executing statistical distribution checks on backend database..."):
        new_report = client.run_monitoring_check()
        if new_report:
            st.toast("Monitoring analysis completed successfully!", icon="✅")
            st.rerun()
        else:
            st.error("Failed to run manual monitoring cycle.")

# Header
st.markdown(
    "<h1 class='premium-title'>🔍 Data Distribution & Model Integrity</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p class='premium-sub'>Continuous performance tracking, statistical distribution health checks, and prediction stability analytics.</p>",
    unsafe_allow_html=True,
)

# Alerts banner
if report.get("alerts"):
    st.subheader("⚠️ Active Operational Alerts")
    for alert in report["alerts"]:
        st.warning(alert, icon="⚠️")
else:
    st.success(
        "All features, predictions, and model performance metrics are within healthy limits.",
        icon="✅",
    )

st.markdown("<br>", unsafe_allow_html=True)

# Tabs
tab_performance, tab_features, tab_predictions = st.tabs(
    [
        "📈 Model Performance Metrics",
        "📊 Feature Drift Audits (KS Test)",
        "🎯 Prediction Drift & Class Distributions (PSI)",
    ]
)

# ----------------- Tab 1: Performance Metrics -----------------
with tab_performance:
    st.subheader("Model Performance Audit Logs")
    st.write(
        "Accuracy, precision, recall, and F1 metrics computed by cross-referencing "
        "model risk decisions against analyst-resolved ground-truth cases."
    )

    perf = report.get("performance", {})

    # Grid Layout for KPIs
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)

    with p_col1:
        st.markdown(
            f"""
            <div class='glass-card' style='border-left: 4px solid #3B82F6;'>
                <p class='kpi-title'>Accuracy</p>
                <h2 class='kpi-value'>{perf.get('accuracy', 0.0) * 100:.2f}%</h2>
                <span style='color: #94A3B8; font-size: 0.75rem; font-weight: 500; margin-top: 0.25rem; display: inline-block;'>Sample Size: {perf.get('sample_size', 0)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p_col2:
        st.markdown(
            f"""
            <div class='glass-card' style='border-left: 4px solid #00FF87;'>
                <p class='kpi-title'>Precision</p>
                <h2 class='kpi-value'>{perf.get('precision', 0.0) * 100:.2f}%</h2>
                <span style='color: #00FF87; font-size: 0.75rem; font-weight: 500; margin-top: 0.25rem; display: inline-block;'>TP / (TP + FP)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p_col3:
        st.markdown(
            f"""
            <div class='glass-card' style='border-left: 4px solid #FFB300;'>
                <p class='kpi-title'>Recall</p>
                <h2 class='kpi-value'>{perf.get('recall', 0.0) * 100:.2f}%</h2>
                <span style='color: #FFB300; font-size: 0.75rem; font-weight: 500; margin-top: 0.25rem; display: inline-block;'>TP / (TP + FN)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with p_col4:
        st.markdown(
            f"""
            <div class='glass-card' style='border-left: 4px solid #FF2E63;'>
                <p class='kpi-title'>F1 Score</p>
                <h2 class='kpi-value'>{perf.get('f1_score', 0.0):.4f}</h2>
                <span style='color: #FF2E63; font-size: 0.75rem; font-weight: 500; margin-top: 0.25rem; display: inline-block;'>Harmonic Mean</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Explanation banner about source of data
    if perf.get("is_baseline_estimate"):
        st.info(
            "ℹ️ **Baseline Estimate Mode**: The system database currently contains fewer than 5 resolved ground-truth "
            "cases (open cases or pending investigations do not count). Showing pre-calculated validation baseline values "
            "to ensure dashboard continuity. Real-time evaluations will kick in as soon as more alerts are resolved."
        )
    else:
        st.success(
            f"🎯 **Live Engine Tracking Mode**: Metrics are computed dynamically based on {perf.get('sample_size', 0)} "
            "cases resolved by compliance team analysts."
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        f1_val = float(perf.get("f1_score", 0.0))
        fig_f1 = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=f1_val,
                title={"text": "F1 Performance Metric", "font": {"size": 14, "color": "#FFFFFF"}},
                gauge={
                    "axis": {"range": [0, 1.0], "tickwidth": 1, "tickcolor": "#64748B"},
                    "bar": {"color": "#00FF87" if f1_val > 0.45 else "#FF2E63"},
                    "bgcolor": "rgba(0,0,0,0)",
                    "borderwidth": 2,
                    "bordercolor": "#1E293B",
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 0.45,
                    },
                },
            )
        )
        fig_f1.update_layout(height=180, margin={"t": 30, "b": 10, "l": 10, "r": 10})
        apply_plotly_theme(fig_f1)
        st.plotly_chart(fig_f1, use_container_width=True)

    with col_g2:
        roc_auc_val = float(perf.get("roc_auc", perf.get("accuracy", 0.0)))
        fig_auc = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=roc_auc_val,
                title={
                    "text": "Accuracy / ROC-AUC Index",
                    "font": {"size": 14, "color": "#FFFFFF"},
                },
                gauge={
                    "axis": {"range": [0, 1.0], "tickwidth": 1, "tickcolor": "#64748B"},
                    "bar": {"color": "#3B82F6" if roc_auc_val > 0.75 else "#FFB300"},
                    "bgcolor": "rgba(0,0,0,0)",
                    "borderwidth": 2,
                    "bordercolor": "#1E293B",
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 0.75,
                    },
                },
            )
        )
        fig_auc.update_layout(height=180, margin={"t": 30, "b": 10, "l": 10, "r": 10})
        apply_plotly_theme(fig_auc)
        st.plotly_chart(fig_auc, use_container_width=True)

# ----------------- Tab 2: Feature Drift Audits -----------------
with tab_features:
    st.subheader("Kolmogorov-Smirnov (KS) Two-Sample Distribution Audits")
    st.write(
        "Calculates drift indicators on numerical features. A low p-value (< 0.05) "
        "indicates that recent live inference distributions have statistically shifted from the training baseline."
    )

    feat_drift = report.get("feature_drift", {})

    if feat_drift:
        # Create table data
        rows = []
        for feature, details in feat_drift.items():
            status_style = "status-stable" if details["status"] == "STABLE" else "status-drifted"
            badge_text = "STABLE" if details["status"] == "STABLE" else "DRIFTED 🚨"

            rows.append(
                {
                    "Feature Name": feature,
                    "Statistical Test": "Two-Sample Kolmogorov-Smirnov",
                    "Distance Statistic": details["statistic"],
                    "p-value": details["p_value"],
                    "Status": badge_text,
                }
            )

        df_feat = pd.DataFrame(rows)

        # Display styled table
        st.dataframe(
            df_feat,
            column_config={
                "p-value": st.column_config.NumberColumn(format="%.5f"),
                "Distance Statistic": st.column_config.NumberColumn(format="%.4f"),
                "Status": st.column_config.TextColumn(
                    help="DRIFTED if p-value < 0.05, meaning distributions differ significantly."
                ),
            },
            use_container_width=True,
            hide_index=True,
        )

        # Visualization
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Statistical Distance Matrix")

        # Bar chart showing distances
        fig_dist = px.bar(
            df_feat,
            x="Distance Statistic",
            y="Feature Name",
            orientation="h",
            color="Status",
            color_discrete_map={"STABLE": "#00FF87", "DRIFTED 🚨": "#FF2E63"},
            labels={"Distance Statistic": "KS Statistic (Higher = More Divergent)"},
        )
        apply_plotly_theme(fig_dist)
        fig_dist.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_dist, use_container_width=True)

    else:
        st.info("No feature drift data compiled.")

# ----------------- Tab 3: Prediction Drift & Distributions -----------------
with tab_predictions:
    st.subheader("Population Stability Index (PSI) & Score Shares")
    st.write(
        "Analyzes prediction distribution alignment. High PSI indicates that the risk profile "
        "of live transactions is shifting, possibly indicating model bias, change in fraud patterns, or feature drift."
    )

    pred_drift = report.get("prediction_drift", {})
    psi = pred_drift.get("psi", 0.0)
    psi_status = pred_drift.get("status", "STABLE")

    # Metric highlight
    psi_col1, psi_col2 = st.columns([1, 3])
    with psi_col1:
        if psi_status == "STABLE":
            border_color = "#10B981"
            badge_lbl = "Healthy Prediction Stream"
        elif psi_status == "WARNING_DRIFT":
            border_color = "#F59E0B"
            badge_lbl = "Warning: Moderate Drift"
        else:
            border_color = "#EF4444"
            badge_lbl = "Critical: Extreme Shift"

        st.markdown(
            f"""
            <div class='glass-card' style='border-left: 4px solid {border_color};'>
                <p class='kpi-title'>PSI Value</p>
                <h2 class='kpi-value'>{psi:.4f}</h2>
                <span style='color: {border_color}; font-weight: 700; font-size: 0.8rem;'>{psi_status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with psi_col2:
        # Mini guide
        st.markdown(textwrap.dedent("""
                * **PSI < 0.10**: Stable distribution. No action required.
                * **0.10 ≤ PSI < 0.25**: Moderate shift. Monitor features for early degradation signs.
                * **PSI ≥ 0.25**: Significant shift. Model retraining recommended to prevent performance decline.
                """))

    st.markdown("<br>", unsafe_allow_html=True)

    # Class Distribution Comparison
    st.subheader("Risk Bucket Distribution Shares")
    class_dist = report.get("class_distribution", {})

    if class_dist:
        base_shares = class_dist.get("baseline", {})
        live_shares = class_dist.get("target", {})

        # Reshape data for plotly bar chart
        shares_data = []
        for bucket in ["Low", "Medium", "High", "Critical"]:
            shares_data.append(
                {
                    "Risk Category": bucket,
                    "Distribution Share": base_shares.get(bucket, 0.0),
                    "Population Group": "Training Baseline",
                }
            )
            shares_data.append(
                {
                    "Risk Category": bucket,
                    "Distribution Share": live_shares.get(bucket, 0.0),
                    "Population Group": "Live Stream (30 Days)",
                }
            )

        df_shares = pd.DataFrame(shares_data)

        fig_shares = px.bar(
            df_shares,
            x="Risk Category",
            y="Distribution Share",
            color="Population Group",
            barmode="group",
            color_discrete_map={"Training Baseline": "#3B82F6", "Live Stream (30 Days)": "#00F0FF"},
            labels={"Distribution Share": "Percentage Share"},
        )
        apply_plotly_theme(fig_shares)
        fig_shares.update_layout(yaxis={"tickformat": ".1%"})
        st.plotly_chart(fig_shares, use_container_width=True)

        # Risk score histograms based on actual live monitoring data
        st.subheader("Risk Score Density Analysis")

        live_scores = monitoring_data.get("prediction_drift", {}).get("live_scores", [])
        if live_scores:
            fig_hist = go.Figure()
            fig_hist.add_trace(
                go.Histogram(
                    x=live_scores,
                    name="Actual Live Stream",
                    marker_color="#00F0FF",
                    opacity=0.7,
                    nbinsx=40,
                )
            )
            fig_hist.update_layout(
                barmode="overlay",
                xaxis_title="Risk Score (0 - 100)",
                yaxis_title="Volume / Density Count",
                bargap=0.05,
            )
            apply_plotly_theme(fig_hist)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("📭 Density profile will render as transactions are evaluated.")

    else:
        st.info("No prediction drift data compiled.")
