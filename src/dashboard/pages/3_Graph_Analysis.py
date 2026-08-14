import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.styles import apply_custom_theme, apply_plotly_theme
from src.features.knowledge_graph import KnowledgeGraphAnalyzer

st.set_page_config(page_title="Fraud Knowledge Graph", page_icon="🕸️", layout="wide")

apply_custom_theme("#1E0A2A")

if "user_token" not in st.session_state:
    st.switch_page("App.py")
    st.stop()

from src.dashboard.styles import render_custom_sidebar
controls_container = render_custom_sidebar()

st.markdown(
    "<h1 class='premium-title'>🕸️ Entity Relationship Network Desk</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p class='premium-sub'>Explore network connections across users, devices, and merchants to identify coordinated rings and risk propagation.</p>",
    unsafe_allow_html=True,
)

analyzer = KnowledgeGraphAnalyzer()

if not analyzer.G or analyzer.G.number_of_nodes() == 0:
    st.warning(
        "The Fraud Knowledge Graph is currently empty. Run the scoring pipeline to ingest transactions."
    )
else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class='glass-card'>
                <p class='kpi-title'>TOTAL NODES</p>
                <h2 class='kpi-value'>{analyzer.G.number_of_nodes()}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class='glass-card'>
                <p class='kpi-title'>TOTAL RELATIONS (EDGES)</p>
                <h2 class='kpi-value'>{analyzer.G.number_of_edges()}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        rings = analyzer.detect_fraud_rings()
        st.markdown(
            f"""
            <div class='glass-card' style='border-left: 4px solid #FF2E63;'>
                <p class='kpi-title'>FRAUD RINGS DETECTED</p>
                <h2 class='kpi-value'>{len(rings)}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        sharing = analyzer.detect_hidden_sharing()
        st.markdown(
            f"""
            <div class='glass-card' style='border-left: 4px solid #B388FF;'>
                <p class='kpi-title'>SHARED VECTOR CLUSTERS</p>
                <h2 class='kpi-value'>{len(sharing)}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Main Tabs
    tab_inspect, tab_rings, tab_propagation, tab_sharing = st.tabs(
        [
            "Interactive Ego Network Explorer",
            "Coordinated Fraud Rings",
            "Risk Propagation Model",
            "Hidden Shared Clusters",
        ]
    )

    with tab_inspect:
        st.subheader("Interactive Ego Network Explorer")
        st.write(
            "Inspect a specific node and its immediate neighbors to visualize local relationships."
        )

        # Node selector
        all_nodes = sorted(analyzer.G.nodes())
        selected_node = st.selectbox("Select Node ID to Inspect", all_nodes, index=0)

        if selected_node:
            col_graph, col_centrality = st.columns([1.5, 1])

            with col_graph:
                # Build ego graph
                ego_G = nx.ego_graph(analyzer.G, selected_node, radius=1)

                # Draw network with Plotly
                pos = nx.spring_layout(ego_G, seed=42)

                edge_x = []
                edge_y = []
                for edge in ego_G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                edge_trace = go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    line={"width": 1, "color": "#CBD5E1"},
                    hoverinfo="none",
                    mode="lines",
                )

                node_x = []
                node_y = []
                node_text = []
                node_color = []
                node_size = []

                for node in ego_G.nodes():
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)

                    n_type = ego_G.nodes[node].get("type", "unknown")
                    node_text.append(f"ID: {node}<br>Type: {n_type.upper()}")

                    # Colors based on node type
                    if node == selected_node:
                        node_color.append("#FF2E63")  # Glowing Red for target node
                        node_size.append(25)
                    elif n_type == "user":
                        node_color.append("#3B82F6")  # Glowing Blue
                        node_size.append(18)
                    elif n_type == "device":
                        node_color.append("#00FF87")  # Glowing Green
                        node_size.append(16)
                    elif n_type == "card":
                        node_color.append("#FFB300")  # Glowing Yellow
                        node_size.append(16)
                    else:
                        node_color.append("#B388FF")  # Glowing Purple
                        node_size.append(16)

                node_trace = go.Scatter(
                    x=node_x,
                    y=node_y,
                    mode="markers+text",
                    hoverinfo="text",
                    text=[n.split("_")[-1] for n in ego_G.nodes()],  # short names
                    textposition="bottom center",
                    marker={
                        "showscale": False,
                        "color": node_color,
                        "size": node_size,
                        "line": {"width": 2, "color": "#060814"},
                    },
                )

                node_trace.hovertext = node_text

                fig = go.Figure(
                    data=[edge_trace, node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode="closest",
                        margin={"b": 0, "l": 0, "r": 0, "t": 0},
                        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
                        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                    ),
                )
                apply_plotly_theme(fig)
                st.plotly_chart(fig, use_container_width=True)

            with col_centrality:
                st.markdown("#### Graph Network Risk Propagation Index")
                st.write("Top 5 central entities calculated live from the network topology.")
                try:
                    pr = nx.pagerank(analyzer.G)
                    df_pr = (
                        pd.DataFrame(list(pr.items()), columns=["Node ID", "Centrality"])
                        .sort_values(by="Centrality", ascending=False)
                        .head(5)
                    )
                    # Map node type
                    df_pr["Type"] = df_pr["Node ID"].map(
                        lambda x: analyzer.G.nodes[x].get("type", "unknown").upper()
                    )

                    fig_pr = px.bar(
                        df_pr,
                        x="Centrality",
                        y="Node ID",
                        color="Type",
                        orientation="h",
                        color_discrete_map={
                            "USER": "#3B82F6",
                            "DEVICE": "#00FF87",
                            "CARD": "#FFB300",
                            "MERCHANT": "#B388FF",
                        },
                    )
                    apply_plotly_theme(fig_pr)
                    fig_pr.update_layout(
                        height=280,
                        margin={"t": 10, "b": 10, "l": 10, "r": 10},
                        yaxis={"categoryorder": "total ascending"},
                    )
                    st.plotly_chart(fig_pr, use_container_width=True)
                except Exception:
                    st.info("Centrality calculation is loading...")

            # Node Details Table
            st.write("#### Neighbor Connections Details")
            details = []
            for nbr in analyzer.G.neighbors(selected_node):
                edge_data = analyzer.G.get_edge_data(selected_node, nbr)
                details.append(
                    {
                        "Neighbor ID": nbr,
                        "Entity Type": analyzer.G.nodes[nbr].get("type", "unknown").upper(),
                        "Transaction ID": edge_data.get("transaction_id", "N/A"),
                        "Amount": f"${edge_data.get('amount', 0.0):,.2f}",
                        "Is Fraud": "🚨 YES" if edge_data.get("is_fraud") == 1 else "✅ NO",
                        "Timestamp": edge_data.get("timestamp", "N/A"),
                    }
                )
            if details:
                st.dataframe(pd.DataFrame(details), use_container_width=True)

    with tab_rings:
        st.subheader("Coordinated Fraud Rings")
        st.write("Identifies sub-networks with high fraud transaction ratios or cycles.")

        if not rings:
            st.info("No suspicious fraud rings detected in the current network topology.")
        else:
            df_rings = pd.DataFrame(rings)
            # Reorder & rename columns for display
            df_rings_display = df_rings[
                ["ring_id", "node_count", "fraud_rate", "cycle_count", "severity"]
            ].copy()
            df_rings_display["fraud_rate"] = df_rings_display["fraud_rate"].map(
                lambda x: f"{x * 100:.1f}%"
            )
            st.dataframe(df_rings_display, use_container_width=True)

            # Detail view
            selected_ring = st.selectbox("Inspect Fraud Ring Details", df_rings["ring_id"].tolist())
            ring_data = df_rings[df_rings["ring_id"] == selected_ring].iloc[0]
            st.markdown(f"**Ring Severity**: `{ring_data['severity']}`")
            st.markdown(
                f"**Associated Users in Ring**: `{', '.join(ring_data['connected_users'])}`"
            )
            st.markdown(f"**All Ring Node Components**: `{', '.join(ring_data['nodes'])}`")

    with tab_propagation:
        st.subheader("Risk Propagation Model")
        st.write(
            "Propagates risk levels from known fraudulent nodes to neighboring accounts via random walk averages."
        )

        # Calculate propagated risks
        risks = analyzer.propagate_risk()
        df_risks = pd.DataFrame(list(risks.items()), columns=["Node ID", "Propagated Risk Score"])
        df_risks["Node Type"] = df_risks["Node ID"].map(
            lambda x: analyzer.G.nodes[x].get("type", "unknown").upper()
        )
        df_risks = df_risks.sort_values(by="Propagated Risk Score", ascending=False)

        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.dataframe(df_risks, use_container_width=True)
        with col_right:
            fig_hist = go.Figure(
                data=[
                    go.Histogram(
                        x=df_risks["Propagated Risk Score"], nbinsx=10, marker_color="#00F0FF"
                    )
                ]
            )
            apply_plotly_theme(fig_hist)
            fig_hist.update_layout(
                xaxis_title="Risk Score",
                yaxis_title="Count",
            )
            st.plotly_chart(fig_hist, use_container_width=True)

    with tab_sharing:
        st.subheader("Hidden Shared Clusters")
        st.write(
            "Detects user accounts sharing hardware or payment vectors without direct transaction interactions."
        )

        if not sharing:
            st.info("No suspicious shared vector clusters detected.")
        else:
            sharing_details = []
            for item in sharing:
                sharing_details.append(
                    {
                        "Shared Entity ID": item["entity_id"],
                        "Entity Type": item["entity_type"].upper(),
                        "Shared By Users": ", ".join(item["shared_by_users"]),
                        "User Count": item["user_count"],
                        "Description": item["description"],
                    }
                )
            st.dataframe(pd.DataFrame(sharing_details), use_container_width=True)
