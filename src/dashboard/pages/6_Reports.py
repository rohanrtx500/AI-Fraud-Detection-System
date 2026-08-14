import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.client import FraudAPIClient
from src.dashboard.styles import apply_custom_theme, apply_plotly_theme

# Page configuration
st.set_page_config(page_title="Executive Fraud Reporting", page_icon="📊", layout="wide")

apply_custom_theme("#0A1E2A")

if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

client = FraudAPIClient()
client.set_token(st.session_state.user_token)

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

# Header
st.markdown(
    "<h1 class='premium-title'>📑 Executive Compliance & Audit Reports</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p class='premium-sub'>Compile operational summaries, analyze top threat categories, and export official PDF/Excel report ledgers.</p>",
    unsafe_allow_html=True,
)

# Select Reporting Window
window = st.selectbox(
    "Select Reporting Window",
    ["daily", "weekly", "monthly"],
    format_func=lambda x: {
        "daily": "Daily Summary (Last 24 Hours)",
        "weekly": "Weekly Summary (Last 7 Days)",
        "monthly": "Monthly Summary (Last 30 Days)",
    }[x],
)

# Fetch Summary data
with st.spinner("Compiling database summaries..."):
    data = client.get_reports_summary(window)

if not data:
    st.error("Could not fetch reports data from the API server. Ensure the backend is active.")
    st.stop()

summary = data.get("summary", {})

# Grid Layout for KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #00FF87;'>
            <div class='kpi-title'>Confirmed Fraud Rate</div>
            <div class='kpi-value'>{summary.get('fraud_rate', 0.0) * 100:.3f}%</div>
            <div class='status-pill status-pill-green' style='margin-top: 0.5rem;'>Resolved Cases / Total TX</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #FF2E63;'>
            <div class='kpi-title'>Money At Risk</div>
            <div class='kpi-value'>${summary.get('money_at_risk', 0.0):,.2f}</div>
            <div class='status-pill status-pill-red' style='margin-top: 0.5rem;'>Flagged/Blocked Amount</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #00F0FF;'>
            <div class='kpi-title'>Scored Transactions Volume</div>
            <div class='kpi-value'>{summary.get('total_transactions', 0):,}</div>
            <div class='status-pill status-pill-amber' style='margin-top: 0.5rem; color: #00F0FF !important; background: rgba(0, 240, 255, 0.08) !important; border-color: rgba(0, 240, 255, 0.15) !important;'>Scoring Stream</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class='glass-card' style='border-left: 4px solid #B388FF;'>
            <div class='kpi-title'>Total Value Scored</div>
            <div class='kpi-value'>${summary.get('total_amount', 0.0):,.2f}</div>
            <div class='status-pill status-pill-purple' style='margin-top: 0.5rem;'>USD Ledger</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Export Desk Sidebar
if controls_container:
    controls_container.markdown("### 📥 Export Reports")

    # Check RBAC
    role = st.session_state.get("user_role", "Auditor")
    if role != "Auditor":
        controls_container.warning(
            "⚠️ Access Denied: Executive Report downloads are restricted to Auditors."
        )
    else:
        controls_container.write("Download styled documents compiled directly from the live database ledger.")

        # PDF Download
        pdf_data = client.get_reports_export_raw(window, "pdf")
        if pdf_data:
            controls_container.download_button(
                label="📄 Download PDF Executive Report",
                data=pdf_data,
                file_name=f"executive_fraud_report_{window}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            controls_container.warning("Failed to load PDF report.")

        # Excel Download
        excel_data = client.get_reports_export_raw(window, "excel")
        if excel_data:
            controls_container.download_button(
                label=" Excel Spreadsheet Export",
                data=excel_data,
                file_name=f"executive_fraud_report_{window}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            controls_container.warning("Failed to load Excel report.")

        # CSV Download
        csv_data = client.get_reports_export_raw(window, "csv")
        if csv_data:
            controls_container.download_button(
                label="📝 Download CSV Trends Log",
                data=csv_data,
                file_name=f"executive_fraud_trends_{window}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            controls_container.warning("Failed to load CSV report.")

# Main Body Tabs
tab_trends, tab_threats, tab_analysts = st.tabs(
    ["📈 Risk & Value Trends", "🎯 Threat Matrix Breakdowns", "👥 Compliance Team Performance"]
)

# ----------------- Tab 1: Risk & Value Trends -----------------
with tab_trends:
    st.subheader("Time-Series Risk Trends")
    st.write(
        "Visualizes day-by-day aggregates of transaction volumes and corresponding money at risk."
    )

    trends = data.get("risk_trends", [])
    if trends:
        df_trends = pd.DataFrame(trends)

        # 3-column layout for Volume, Risk, and Financial Impact Donut
        col_t1, col_t2, col_t3 = st.columns(3)

        with col_t1:
            fig_vol = px.line(
                df_trends,
                x="date",
                y="total_transactions",
                markers=True,
                color_discrete_sequence=["#00F0FF"],
                title="Daily Scored Transaction Volume",
                labels={"total_transactions": "Transaction Count", "date": "Date"},
            )
            apply_plotly_theme(fig_vol)
            st.plotly_chart(fig_vol, use_container_width=True)

        with col_t2:
            fig_risk = px.bar(
                df_trends,
                x="date",
                y="money_at_risk",
                color_discrete_sequence=["#FF2E63"],
                title="Daily Money At Risk ($)",
                labels={"money_at_risk": "Amount ($)", "date": "Date"},
            )
            apply_plotly_theme(fig_risk)
            st.plotly_chart(fig_risk, use_container_width=True)

        with col_t3:
            total_amt = summary.get("total_amount", 0.0)
            money_at_risk = summary.get("money_at_risk", 0.0)
            fraud_rate = summary.get("fraud_rate", 0.0)
            fraud_lost = summary.get(
                "fraud_amount",
                (
                    df_trends["fraud_amount"].sum()
                    if "fraud_amount" in df_trends.columns
                    else total_amt * fraud_rate
                ),
            )
            clean_amt = max(0.0, total_amt - money_at_risk - fraud_lost)

            df_impact = pd.DataFrame(
                [
                    {"Category": "Clean Transactions", "Amount": clean_amt},
                    {"Category": "Blocked (Protected)", "Amount": money_at_risk},
                    {"Category": "Lost (Confirmed)", "Amount": fraud_lost},
                ]
            )

            fig_impact = px.pie(
                df_impact,
                values="Amount",
                names="Category",
                hole=0.6,
                title="Financial Ledger Breakdown",
                color="Category",
                color_discrete_map={
                    "Clean Transactions": "#00FF87",
                    "Blocked (Protected)": "#FFB300",
                    "Lost (Confirmed)": "#FF2E63",
                },
            )
            fig_impact.update_traces(textposition="inside", textinfo="percent")
            apply_plotly_theme(fig_impact)
            fig_impact.update_layout(showlegend=False, margin={"t": 40, "b": 10, "l": 10, "r": 10})
            st.plotly_chart(fig_impact, use_container_width=True)

        st.dataframe(
            df_trends,
            column_config={
                "total_amount": st.column_config.NumberColumn(format="$%,.2f"),
                "fraud_amount": st.column_config.NumberColumn(format="$%,.2f"),
                "money_at_risk": st.column_config.NumberColumn(format="$%,.2f"),
                "fraud_rate": st.column_config.NumberColumn(format="%.4f"),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No trend data found.")

# ----------------- Tab 2: Threat Matrix Breakdowns -----------------
with tab_threats:
    st.subheader("Top Fraud Risk Vectors")
    st.write(
        "Identifies high-risk regions, suspicious merchant codes, and fraudulent device hardware fingerprints."
    )

    threats = data.get("top_threats", {})

    col_th1, col_th2 = st.columns(2)

    with col_th1:
        st.subheader("Country Risk Levels")
        countries = threats.get("country", [])
        if countries:
            df_country = pd.DataFrame(countries)
            fig_country = px.bar(
                df_country,
                x="country",
                y="total_amount",
                color="average_risk_score",
                color_continuous_scale="Reds",
                title="Top Scored Volume by Country",
                labels={
                    "total_amount": "Total Amount ($)",
                    "country": "Country Code",
                    "average_risk_score": "Avg Risk Score",
                },
            )
            apply_plotly_theme(fig_country)
            st.plotly_chart(fig_country, use_container_width=True)
            st.dataframe(df_country, use_container_width=True, hide_index=True)
        else:
            st.info("No country threat vectors parsed.")

    with col_th2:
        st.subheader("Merchant Categories (MCC)")
        mccs = threats.get("mcc", [])
        if mccs:
            df_mcc = pd.DataFrame(mccs)
            fig_mcc = px.bar(
                df_mcc,
                x="mcc",
                y="total_amount",
                color="average_risk_score",
                color_continuous_scale="Oranges",
                title="Top Scored Volume by Merchant Category",
                labels={
                    "total_amount": "Total Amount ($)",
                    "mcc": "MCC Category",
                    "average_risk_score": "Avg Risk Score",
                },
            )
            apply_plotly_theme(fig_mcc)
            st.plotly_chart(fig_mcc, use_container_width=True)
            st.dataframe(df_mcc, use_container_width=True, hide_index=True)
        else:
            st.info("No MCC threats parsed.")

    st.markdown("---")
    st.subheader("Top Spoofed Devices Activity")
    devices = threats.get("device", [])
    if devices:
        df_device = pd.DataFrame(devices)
        st.dataframe(
            df_device,
            column_config={
                "total_amount": st.column_config.NumberColumn(format="$%,.2f"),
                "average_risk_score": st.column_config.NumberColumn(format="%.1f"),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No device threat vectors found.")

# ----------------- Tab 3: Analyst Performance -----------------
with tab_analysts:
    st.subheader("Compliance Resolution Metrics")
    st.write(
        "Tracks cases assigned, case completion volumes, resolution speeds, and true-positive confirmation rates."
    )

    perf = data.get("analyst_performance", [])
    if perf:
        df_perf = pd.DataFrame(perf)

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            fig_perf = px.bar(
                df_perf,
                x="analyst",
                y=["assigned_cases", "resolved_cases"],
                barmode="group",
                color_discrete_map={"assigned_cases": "#00F0FF", "resolved_cases": "#00FF87"},
                title="Assigned vs Resolved Workload Shares",
                labels={"value": "Cases", "analyst": "Analyst Name"},
            )
            apply_plotly_theme(fig_perf)
            st.plotly_chart(fig_perf, use_container_width=True)

        with col_p2:
            fig_time = px.bar(
                df_perf,
                x="analyst",
                y="average_resolution_time_hours",
                color_discrete_sequence=["#FFB300"],
                title="Average Case Resolution Speed (Hours)",
                labels={
                    "average_resolution_time_hours": "Resolution Time (hrs)",
                    "analyst": "Analyst Name",
                },
            )
            apply_plotly_theme(fig_time)
            st.plotly_chart(fig_time, use_container_width=True)

        st.dataframe(
            df_perf,
            column_config={
                "accuracy_rate": st.column_config.NumberColumn(format="%.1%"),
                "average_resolution_time_hours": st.column_config.NumberColumn(format="%.2f hrs"),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No analyst performance metrics compiled.")
