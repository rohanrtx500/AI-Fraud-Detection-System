import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

st.set_page_config(page_title="Threat Intel Blacklist", page_icon="📡", layout="wide", initial_sidebar_state="expanded")

apply_custom_theme("#320A0A")

st.markdown(
    "<h1 class='premium-title'>📡 Threat Intelligence & Risk Multipliers</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='premium-sub'>Register compromised threat vectors (IPs, devices, cards, merchant locations) to calculate real-time risk multipliers.</p>",
    unsafe_allow_html=True,
)

if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

client = FraudAPIClient()
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

role = st.session_state.get("user_role", "Compliance Officer")

# Grid layout: left column for adding new vector, right column for active list
col_add, col_list = st.columns([1, 2])

with col_add:
    st.markdown("### ➕ Add Blacklist Vector")

    if role != "Compliance Officer":
        st.warning(
            "⚠️ Access Denied: Managing blacklisted threat intelligence vectors is restricted to Compliance Officers."
        )
    else:
        with st.form("add_threat_form"):
            st.write("Register a new compromised indicator vector:")
            t_type = st.selectbox("Indicator Type", ["IP", "DEVICE", "ACCOUNT", "MERCHANT"])
            t_val = st.text_input(
                "Indicator Value", placeholder="e.g. 198.51.100.4, dev_fingerprint_abc"
            )
            t_mult = st.number_input(
                "Risk Multiplier (e.g. 2.0x, 3.5x)", min_value=1.0, value=2.0, step=0.5
            )
            t_src = st.text_input("Source/Reference Feed", "manual_entry")

            submit_btn = st.form_submit_button("Add to Blacklist")

            if submit_btn:
                if not t_val.strip():
                    st.error("Indicator Value cannot be empty.")
                else:
                    res = client.add_threat(t_type, t_val.strip(), t_mult, t_src)
                    if res:
                        st.success(f"Successfully blacklisted {t_type} value '{t_val}'!")
                        st.rerun()

with col_list:
    st.markdown("### 📋 Active Blacklist Registry")

    # Load from API
    threats = client.get_threats()

    if not threats:
        st.info("📭 No indicators have been registered yet. Use the form above to add IP addresses, devices, or entity IDs to the blacklist registry.")
        st.stop()

    df_threats = pd.DataFrame(threats)

    # Threat Analytics Charts
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        df_type = df_threats.groupby("indicator_type").size().reset_index(name="Count")
        fig_donut = px.pie(
            df_type,
            values="Count",
            names="indicator_type",
            hole=0.6,
            title="Threat Indicators by Type",
            color="indicator_type",
            color_discrete_map={
                "IP": "#FF2E63",
                "DEVICE": "#FFB300",
                "ACCOUNT": "#00F0FF",
                "MERCHANT": "#B388FF",
            },
        )
        fig_donut.update_traces(textposition="inside", textinfo="percent+value")
        apply_plotly_theme(fig_donut)
        fig_donut.update_layout(
            showlegend=False, margin={"t": 40, "b": 10, "l": 10, "r": 10}, height=200
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_chart2:
        df_sorted = df_threats.sort_values(by="risk_multiplier", ascending=False).head(5)
        fig_bar = px.bar(
            df_sorted,
            x="risk_multiplier",
            y="value",
            orientation="h",
            color="indicator_type",
            color_discrete_map={
                "IP": "#FF2E63",
                "DEVICE": "#FFB300",
                "ACCOUNT": "#00F0FF",
                "MERCHANT": "#B388FF",
            },
            title="Top Threat Risk Multipliers",
            labels={"risk_multiplier": "Multiplier", "value": "Indicator"},
        )
        apply_plotly_theme(fig_bar)
        fig_bar.update_layout(
            showlegend=False,
            margin={"t": 40, "b": 10, "l": 10, "r": 10},
            height=200,
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Display table
    df_show = df_threats[
        ["indicator_type", "value", "risk_multiplier", "source", "added_at", "indicator_id"]
    ].copy()
    df_show.columns = [
        "Type",
        "Value",
        "Multiplier (Risk)",
        "Source Feed",
        "Added At",
        "Indicator ID",
    ]
    df_show["Added At"] = df_show["Added At"].map(lambda x: x.replace("T", " ").split(".")[0])

    st.dataframe(df_show, use_container_width=True)

    # Delete option
    st.markdown("---")
    st.markdown("### 🗑️ Remove Blacklist Vector")

    if role != "Compliance Officer":
        st.warning(
            "⚠️ Access Denied: Removing blacklisted threat intelligence vectors is restricted to Compliance Officers."
        )
    else:
        # Select list from dataframe
        selected_id = st.selectbox("Select ID to Remove", df_threats["indicator_id"].tolist())
        if st.button("Delete Blacklist Entry", type="primary"):
            if client.delete_threat(selected_id):
                st.success("Successfully removed indicator from blacklist.")
                st.rerun()
            else:
                st.error("Failed to delete indicator.")
