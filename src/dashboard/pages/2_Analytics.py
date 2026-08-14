import numpy as np  # noqa: F401 (kept for potential future use)
import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

# Page configuration
st.set_page_config(page_title="Platform Analytics", page_icon="📈", layout="wide")

apply_custom_theme("#0A252E")

st.markdown(
    "<h1 class='premium-title'>📊 Executive Risk & Value Analytics</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='premium-sub'>Aggregated risk metrics, time-series volume trends, and geographical threat distributions.</p>",
    unsafe_allow_html=True,
)

# Initialize client
if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

client = FraudAPIClient()

if st.session_state.user_role != "Auditor":
    st.error("⚠️ Access Denied: This workspace is designated exclusively for Auditor users.")
    if st.button("⚡ Switch to Risk Auditor Role (1-Click)", type="primary"):
        res = client.login_user("AU-5265", "Password123!")
        if "access_token" in res:
            st.session_state.user_token = res["access_token"]
            st.session_state.user_role = res["role"]
            st.session_state.username = res["username"]
            st.session_state.user_role_id = res.get("role_id") or "AU-5265"
            st.session_state.user_display_name = f"{res['username']} ({st.session_state.user_role_id})"
            st.query_params["session_token"] = res["access_token"]
            st.query_params["role"] = res["role"]
            st.query_params["username"] = res["username"]
            st.query_params["role_id"] = st.session_state.user_role_id
            st.rerun()
    st.stop()
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

# Date filter
col_filt1, col_filt2 = st.columns(2)
with col_filt1:
    days_to_plot = st.slider("Select Timeframe (Days)", min_value=5, max_value=30, value=15)

# Load daily trends from API
trends = client.get_daily_trends(days=days_to_plot)

# Show empty state if no real data is available yet
if not trends:
    st.info("📭 No transaction data recorded yet. Analytics will populate automatically as transactions are processed through the platform.")
    st.stop()

df_trends = pd.DataFrame(trends)

# Row 1: Graphs
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Daily Transaction Volume & Detections")

    # Draw double axis or dual lines for volume vs alerts
    fig1 = px.line(
        df_trends,
        x="date",
        y=["total_transactions", "flagged_fraud_transactions"],
        markers=True,
        labels={"value": "Count", "date": "Date", "variable": "Metric Category"},
        color_discrete_map={
            "total_transactions": "#00F0FF",  # Cyan
            "flagged_fraud_transactions": "#FF2E63",  # Crimson Red
        },
    )
    apply_plotly_theme(fig1)
    fig1.update_layout(legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01})
    st.plotly_chart(fig1, use_container_width=True)

with col_g2:
    st.subheader("Risk Score Distribution Profile")

    # Build from real assessed transactions
    scores_raw = [t.get("risk_score") for t in trends if t.get("risk_score") is not None]
    if scores_raw:
        scores_df = pd.DataFrame({"Risk Score": scores_raw})
        fig2 = px.histogram(
            scores_df,
            x="Risk Score",
            nbins=50,
            color_discrete_sequence=["#00F0FF"],
        )
        apply_plotly_theme(fig2)
        fig2.update_layout(bargap=0.05)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📭 Risk score distribution will appear once transactions have been evaluated by the platform.")

# Row 2: Location heat map & MCC Treemap
st.markdown("---")
col_map, col_mcc = st.columns([1.2, 1])

with col_map:
    st.subheader("Geographical High-Risk Ingestion Heatmap")
    st.write(
        "Detections distribution mapping where IP address location mismatches credit card billing records."
    )

    # Build from real flagged transaction geo data
    geo_rows = [
        t for t in trends
        if t.get("lat") is not None and t.get("lon") is not None
    ]
    if geo_rows:
        geo_df = pd.DataFrame(geo_rows)[["lat", "lon", "Risk Level", "Flagged Alerts Count"]]
        st.map(geo_df, size="Flagged Alerts Count", color=[239, 68, 68, 160])
        st.dataframe(geo_df, use_container_width=True)
    else:
        st.info("📭 Geographic heatmap will populate as flagged transactions with location data are processed.")

with col_mcc:
    st.subheader("Top Merchant Categories (MCC) Distribution")
    st.write(
        "Treemap of transaction category groupings scaled by volume and color-coded by average risk."
    )

    # Build MCC distribution from live transaction data
    mcc_rows = [t for t in trends if t.get("merchant_category") is not None]
    if mcc_rows:
        df_mcc = pd.DataFrame(mcc_rows)
        df_mcc_agg = df_mcc.groupby("merchant_category").agg(
            Count=("merchant_category", "count")
        ).reset_index().rename(columns={"merchant_category": "Category"})
        fig_tree = px.treemap(
            df_mcc_agg,
            path=["Category"],
            values="Count",
            color_discrete_sequence=["#00F0FF"],
        )
        apply_plotly_theme(fig_tree)
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("📭 Merchant category distribution will appear once transactions are processed.")
