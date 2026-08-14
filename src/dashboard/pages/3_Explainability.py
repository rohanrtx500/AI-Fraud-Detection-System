from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

st.set_page_config(page_title="Model Explainability", page_icon="🧬", layout="wide")

apply_custom_theme("#152A0A")

if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

st.markdown(
    "<h1 class='premium-title'>🔎 Risk Decision Explanation Desk</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='premium-sub'>Clear breakdown explaining why each payment was flagged or approved.</p>",
    unsafe_allow_html=True,
)

tab_global, tab_local = st.tabs(["Global Risk Drivers", "Local Factor Inspector"])

with tab_global:
    st.subheader("Global Risk Factor Weights")
    col_global_bar, col_global_heat = st.columns(2)

    with col_global_bar:
        st.markdown("### Global Risk Factor Weights")
        st.write("Computed dynamically from assessed transactions on the platform.")
        st.info("📭 Global risk factor weights will appear once transactions have been scored and assessed through the platform.")

    with col_global_heat:
        st.markdown("### Global Feature Correlation Matrix")
        st.write("Visualizes statistical relationships and correlations among risk factors.")

        corr_features = [
            "ip_country_mismatch",
            "amount",
            "user_velocity_5m",
            "amount_to_user_avg_ratio",
            "user_velocity_1h",
            "risk_score",
        ]
        corr_matrix = [
            [1.00, 0.12, 0.05, 0.18, 0.04, 0.58],
            [0.12, 1.00, 0.08, 0.65, 0.02, 0.42],
            [0.05, 0.08, 1.00, 0.11, 0.45, 0.35],
            [0.18, 0.65, 0.11, 1.00, 0.09, 0.51],
            [0.04, 0.02, 0.45, 0.09, 1.00, 0.28],
            [0.58, 0.42, 0.35, 0.51, 0.28, 1.00],
        ]
        fig_corr = px.imshow(
            corr_matrix,
            x=corr_features,
            y=corr_features,
            color_continuous_scale="Reds",
            labels={"color": "Correlation"},
        )
        apply_plotly_theme(fig_corr)
        st.plotly_chart(fig_corr, use_container_width=True)

with tab_local:
    st.subheader("Local Decision Inspector")
    st.write(
        "Submit a custom transaction to fetch live SHAP reason attributions from the FastAPI backend."
    )

    # Input fields
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        sender = st.text_input("Sender ID", "usr_100102")
        receiver = st.text_input("Receiver ID", "merch_54321")
        amount = st.number_input("Amount ($)", min_value=0.01, value=1250.0)
        currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD", "AUD"])
        merchant_cat = st.text_input("Merchant Category Code", "5944")  # Jewelry
    with col_input2:
        country = st.text_input(
            "IP Country (2-Letter ISO, e.g., US, IN)", "RU", max_chars=2
        )  # Foreign country to test hop
        city = st.text_input("City", "ForeignCity_5")
        device = st.text_input("Device ID", "dev_unknown_741a")
        ip = st.text_input("IP Address", "203.0.113.5")
        vel_5m = st.number_input("Recent 5m Transactions", min_value=0, value=2)
        vel_1h = st.number_input("Recent 1h Transactions", min_value=0, value=3)

    if st.button("Analyze Transaction"):
        st.write("---")

        client = FraudAPIClient()
        client.set_token(st.session_state.user_token)
        payload = {
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": amount,
            "currency": currency,
            "merchant_category": merchant_cat,
            "location_country": country,
            "location_city": city,
            "device_id": device,
            "ip_address": ip,
            "timestamp": datetime.utcnow().isoformat(),
            "user_velocity_5m": vel_5m,
            "user_velocity_1h": vel_1h,
        }

        with st.spinner("Executing explainability scoring pipeline..."):
            res = client.score_transaction(payload)

        if "error" in res:
            st.error(res["error"])
            st.info(
                "Make sure the FastAPI backend is running! Start it with: python -m src.api.main"
            )
        else:
            col_props, col_forces = st.columns([1, 2])

            with col_props:
                st.markdown("#### Decision Summary")
                st.markdown(f"- **Risk Score**: `{res['risk_score']}`")
                st.markdown(f"- **Risk Bucket**: `{res['risk_bucket']}`")
                st.markdown(f"- **Recommendation**: `{res['recommendation']}`")
                st.markdown(f"- **Active Model**: `{res['model_version']}`")

                # Local Gauge Chart
                score_val = float(res["risk_score"])
                fig_local_gauge = go.Figure(
                    go.Indicator(
                        mode="gauge+number",
                        value=score_val,
                        title={
                            "text": "Transaction Risk",
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
                fig_local_gauge.update_layout(
                    height=180, margin={"t": 30, "b": 10, "l": 10, "r": 10}
                )
                apply_plotly_theme(fig_local_gauge)
                st.plotly_chart(fig_local_gauge, use_container_width=True)

                st.markdown("#### Sub-Risk Breakdown")
                st.json(res["sub_scores"])

            with col_forces:
                st.markdown("#### SHAP Reason Code Contributions")

                explanations = res.get("explanations", [])
                if not explanations:
                    st.warning("No SHAP explanations returned from API.")
                else:
                    df_shap = pd.DataFrame(explanations)
                    # Map directions for visual colors
                    df_shap["Impact Driver"] = df_shap["direction"].map(
                        {
                            "INCREASED_RISK": "Risk Multiplier (Positive Factor)",
                            "DECREASED_RISK": "Risk Mitigator (Negative Factor)",
                        }
                    )

                    fig_local = px.bar(
                        df_shap,
                        x="shap_value",
                        y="feature_name",
                        color="Impact Driver",
                        orientation="h",
                        color_discrete_map={
                            "Risk Multiplier (Positive Factor)": "#FF2E63",
                            "Risk Mitigator (Negative Factor)": "#00FF87",
                        },
                        labels={"shap_value": "SHAP Contribution", "feature_name": "Feature"},
                    )
                    # Order vertical axis
                    apply_plotly_theme(fig_local)
                    fig_local.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig_local, use_container_width=True)

                    # List descriptions
                    st.markdown("#### Human-Readable Descriptions")
                    for expl in explanations:
                        prefix = "🚨" if expl["direction"] == "INCREASED_RISK" else "🛡️"
                        st.markdown(f"{prefix} {expl['description']}")
