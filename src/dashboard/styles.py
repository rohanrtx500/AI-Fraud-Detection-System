import streamlit as st


def apply_custom_theme(glow_color="#0D1532"):
    """
    Injects a unified premium dark design system into the Streamlit app.
    Combines Outfit & JetBrains Mono typography with deep slate/navy glassmorphism.
    """
    css = r"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

        /* Dynamic Entrance Animations */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(15px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes revealChart {
            from {
                clip-path: inset(100% 0 0 0);
                transform: scale(0.97) translateY(15px);
                opacity: 0;
            }
            to {
                clip-path: inset(0 0 0 0);
                transform: scale(1) translateY(0);
                opacity: 1;
            }
        }

        @keyframes fadeInLeft {
            from {
                opacity: 0;
                transform: translateX(-15px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        /* Global Theme Overrides & Entrance */
        .stApp, [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 50% 0%, #0D1532 0%, #060814 80%) !important;
            animation: fadeIn 0.6s ease-out both !important;
        }

        .main, [data-testid="stHeader"] {
            background: transparent !important;
            background-color: transparent !important;
        }

        /* Completely Nuke Top Gradient Line, Header Bar, and Three-Dots Toolbar */
        header,
        header *,
        [data-testid="stHeader"],
        [data-testid="stHeader"] *,
        [data-testid="stDecoration"],
        [data-testid="stDecoration"] *,
        div[data-testid="stDecoration"],
        div[class*="stDecoration"],
        .stDecoration,
        header::before,
        [data-testid="stHeader"]::before,
        [data-testid="stHeader"]::after {
            display: none !important;
            visibility: hidden !important;
            height: 0px !important;
            min-height: 0px !important;
            max-height: 0px !important;
            opacity: 0 !important;
            pointer-events: none !important;
            background: none !important;
            background-color: transparent !important;
            background-image: none !important;
            border: none !important;
            box-shadow: none !important;
        }

        #MainMenu,
        [data-testid="stMainMenu"],
        [data-testid="stToolbar"],
        [data-testid="stElementToolbar"],
        [data-testid="stStatusWidget"],
        footer,
        footer * {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0px !important;
            pointer-events: none !important;
        }

        [data-testid="stAppViewContainer"] {
            padding-top: 0px !important;
        }
    </style>
    <script>
        const hideHeaderAndLine = () => {
            const els = document.querySelectorAll('header, [data-testid="stHeader"], [data-testid="stDecoration"], #MainMenu, [data-testid="stToolbar"], [class*="stDecoration"]');
            els.forEach(el => {
                if (el) {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                    el.style.setProperty('height', '0px', 'important');
                    el.style.setProperty('background', 'none', 'important');
                }
            });
        };
        hideHeaderAndLine();
        setInterval(hideHeaderAndLine, 150);
    </script>

        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif !important;
            color: #F8FAFC !important;
        }

        code, pre {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #060814;
        }
        ::-webkit-scrollbar-thumb {
            background: #1E293B;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #334155;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #04060E !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        }

        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Interactive Widgets */
        div[data-baseweb="input"], div[data-baseweb="select"] {
            background-color: rgba(15, 23, 42, 0.4) !important;
            border: 1px solid rgba(255, 255, 255, 0.06) !important;
            border-radius: 8px !important;
            color: #F8FAFC !important;
        }

        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
            border-color: #00F0FF !important;
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.15) !important;
        }

        /* Button Styling - Stripe/Linear Design */
        button[kind="primary"], button[kind="secondary"], .stButton > button {
            background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            padding: 0.5rem 1.2rem !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25) !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;
        }

        button[kind="primary"]:hover, button[kind="secondary"]:hover, .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35) !important;
            background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%) !important;
        }

        button[kind="primary"]:active, button[kind="secondary"]:active, .stButton > button:active {
            transform: translateY(0px) !important;
        }

        /* Tabs Styling */
        div[data-baseweb="tab-list"] {
            background-color: transparent !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
            gap: 0.5rem !important;
        }

        button[data-baseweb="tab"] {
            background-color: transparent !important;
            color: #94A3B8 !important;
            font-weight: 600 !important;
            border: none !important;
            padding: 0.8rem 1.2rem !important;
            transition: all 0.2s ease !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: #00F0FF !important;
            border-bottom: 2px solid #00F0FF !important;
        }

        /* Glassmorphic Panel Cards */
        .glass-card {
            background: rgba(15, 23, 42, 0.45) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
            margin-bottom: 1rem;
        }

        .glass-card:hover {
            border-color: rgba(6, 182, 212, 0.35) !important;
            box-shadow: 0 15px 40px -10px rgba(0, 0, 0, 0.6), 0 0 15px rgba(6, 182, 212, 0.1) !important;
            transform: translateY(-2px) !important;
        }

        /* Premium Title Headers */
        .premium-title {
            font-size: 2.6rem;
            font-weight: 800;
            background: linear-gradient(90deg, #FFFFFF 0%, #E2E8F0 50%, #00F0FF 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
            margin-bottom: 0.3rem;
            text-transform: tracking-tight;
        }

        .premium-sub {
            color: #64748B;
            font-size: 1.05rem;
            font-weight: 400;
            margin-bottom: 1.8rem;
        }

        /* Live Activity Stream Cards */
        .live-alert-card {
            background: rgba(15, 23, 42, 0.3) !important;
            border: 1px solid rgba(255, 255, 255, 0.04) !important;
            border-radius: 10px !important;
            padding: 1rem !important;
            margin-bottom: 0.8rem !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
            transition: all 0.2s ease !important;
        }

        .live-alert-card:hover {
            background: rgba(15, 23, 42, 0.45) !important;
            border-color: rgba(255, 255, 255, 0.08) !important;
            transform: translateX(2px) !important;
        }

        /* Status Pills & Badges */
        .status-pill {
            padding: 0.25rem 0.6rem !important;
            border-radius: 6px !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
            display: inline-block;
        }

        .status-pill-green {
            color: #00FF87 !important;
            background: rgba(0, 255, 135, 0.08) !important;
            border: 1px solid rgba(0, 255, 135, 0.15) !important;
            text-shadow: 0 0 8px rgba(0, 255, 135, 0.3) !important;
        }

        .status-pill-amber {
            color: #FFB300 !important;
            background: rgba(255, 179, 0, 0.08) !important;
            border: 1px solid rgba(255, 179, 0, 0.15) !important;
            text-shadow: 0 0 8px rgba(255, 179, 0, 0.3) !important;
        }

        .status-pill-red {
            color: #FF2E63 !important;
            background: rgba(255, 46, 99, 0.08) !important;
            border: 1px solid rgba(255, 46, 99, 0.15) !important;
            text-shadow: 0 0 8px rgba(255, 46, 99, 0.3) !important;
        }

        .status-pill-purple {
            color: #B388FF !important;
            background: rgba(179, 136, 255, 0.08) !important;
            border: 1px solid rgba(179, 136, 255, 0.15) !important;
            text-shadow: 0 0 8px rgba(179, 136, 255, 0.3) !important;
        }

        /* KPI Titles and Metrics */
        .kpi-title {
            color: #64748B;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin: 0 0 0.4rem 0;
        }

        .kpi-value {
            color: #FFFFFF;
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0;
        }

        /* Streamlit Dataframe styles override */
        div[data-testid="stTable"] table {
            background-color: rgba(15, 23, 42, 0.3) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 8px !important;
        }

        /* Universal entrance transitions for every written or visual element */
        h1, h2, h3, h4, h5, h6, p, span, li, table, tr, td, th, form, img, button,
        .stMarkdown, [data-testid="metric-container"], .glass-card, .live-alert-card,
        div[data-testid="stDataFrame"], div[data-testid="stTable"],
        .stSlider, .stSelectbox, .stTextInput, .stNumberInput, div[data-baseweb="input"],
        div[data-baseweb="select"], .stAlert, .stDataFrame, .stTable {
            animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both !important;
        }

        /* Sidebar items animate with fadeInLeft */
        [data-testid="stSidebarNav"] li, [data-testid="stSidebar"] [class*="stMarkdown"], [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
            animation: fadeInLeft 0.5s cubic-bezier(0.16, 1, 0.3, 1) both !important;
        }

        /* Staggered load delays for sequential animation cascade */
        h1, .premium-title { animation-delay: 0.02s !important; }
        p, .premium-sub { animation-delay: 0.05s !important; }

        /* Sidebar navigation list items cascade */
        [data-testid="stSidebarNav"] li:nth-child(1) { animation-delay: 0.02s !important; }
        [data-testid="stSidebarNav"] li:nth-child(2) { animation-delay: 0.04s !important; }
        [data-testid="stSidebarNav"] li:nth-child(3) { animation-delay: 0.06s !important; }
        [data-testid="stSidebarNav"] li:nth-child(4) { animation-delay: 0.08s !important; }
        [data-testid="stSidebarNav"] li:nth-child(5) { animation-delay: 0.10s !important; }
        [data-testid="stSidebarNav"] li:nth-child(6) { animation-delay: 0.12s !important; }
        [data-testid="stSidebarNav"] li:nth-child(7) { animation-delay: 0.14s !important; }
        [data-testid="stSidebarNav"] li:nth-child(8) { animation-delay: 0.16s !important; }
        [data-testid="stSidebarNav"] li:nth-child(9) { animation-delay: 0.18s !important; }
        [data-testid="stSidebarNav"] li:nth-child(10) { animation-delay: 0.20s !important; }
        [data-testid="stSidebarNav"] li:nth-child(11) { animation-delay: 0.22s !important; }

        /* KPI cards and input blocks cascade */
        .glass-card, [data-testid="metric-container"], div[data-baseweb="input"], div[data-baseweb="select"] {
            animation-delay: 0.08s !important;
        }

        /* Charts grow-reveal and stagger */
        [data-testid="stPlotlyChart"] .main-svg, [data-testid="stPlotlyChart"] .plot-container, [data-testid="stPlotlyChart"] .js-plotly-plot, [data-testid="stPlotlyChart"] iframe {
            animation: revealChart 1.0s cubic-bezier(0.16, 1, 0.3, 1) both !important;
            animation-delay: 0.12s !important;
        }

        /* Dataframes, tables and logs stagger */
        div[data-testid="stDataFrame"], div[data-testid="stTable"], table, .live-alert-card {
            animation-delay: 0.16s !important;
        }

        form, .stButton, button {
            animation-delay: 0.1s !important;
        }

        /* Pulsing Status indicators */
        .status-dot-green {
            height: 10px;
            width: 10px;
            background-color: #00FF87;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #00FF87;
            animation: pulse-green 1.5s infinite;
        }

        .status-dot-yellow {
            height: 10px;
            width: 10px;
            background-color: #FFB300;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #FFB300;
            animation: pulse-yellow 1.5s infinite;
        }

        @keyframes pulse-green {
            0% {
                transform: scale(0.9);
                box-shadow: 0 0 0 0 rgba(0, 255, 135, 0.7);
            }
            70% {
                transform: scale(1);
                box-shadow: 0 0 0 8px rgba(0, 255, 135, 0);
            }
            100% {
                transform: scale(0.9);
                box-shadow: 0 0 0 0 rgba(0, 255, 135, 0);
            }
        }

        @keyframes pulse-yellow {
            0% {
                transform: scale(0.9);
                box-shadow: 0 0 0 0 rgba(255, 179, 0, 0.7);
            }
            70% {
                transform: scale(1);
                box-shadow: 0 0 0 8px rgba(255, 179, 0, 0);
            }
            100% {
                transform: scale(0.9);
                box-shadow: 0 0 0 0 rgba(255, 179, 0, 0);
            }
        }

        /* Nav Cards styling */
        .nav-card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }

        .nav-card {
            background: rgba(15, 23, 42, 0.45) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none !important;
            color: inherit !important;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
        }

        .nav-card:hover {
            border-color: rgba(0, 240, 255, 0.3) !important;
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.15) !important;
            transform: translateY(-4px);
        }

        .nav-card-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #FFFFFF;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .nav-card-desc {
            font-size: 0.85rem;
            color: #94A3B8;
            line-height: 1.4;
            margin-bottom: 1rem;
        }

        .nav-card-action {
            font-size: 0.8rem;
            color: #00F0FF;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            margin-top: auto;
        }

        /* Glow Status Cards for System Status Panel */
        .glow-status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }

        .glow-status-card {
            background: rgba(15, 23, 42, 0.35) !important;
            border: 1px solid rgba(255, 255, 255, 0.04) !important;
            border-radius: 8px;
            padding: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.25s ease;
        }

        .glow-status-card:hover {
            border-color: rgba(255, 255, 255, 0.08) !important;
            background: rgba(15, 23, 42, 0.55) !important;
        }

        /* Tour Step Visual Container */
        .tour-visual-card {
            background: rgba(0, 240, 255, 0.02) !important;
            border: 1px dashed rgba(0, 240, 255, 0.2) !important;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
        }

        /* Top Gradient Accent Bar */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #00F0FF 0%, #00FF87 50%, #FFB300 100%) !important;
            z-index: 999999 !important;
            box-shadow: 0 1px 10px rgba(0, 240, 255, 0.5) !important;
        }

        /* Sidebar Brand Header Injection */
        [data-testid="stSidebarNav"]::before {
            content: "🛡️ AI RISK COCKPIT";
            display: block;
            padding: 1.5rem 1rem 1rem 1rem !important;
            font-family: 'Outfit', sans-serif !important;
            font-size: 1.15rem !important;
            font-weight: 800 !important;
            color: #FFFFFF !important;
            letter-spacing: 0.05em !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
            margin-bottom: 1rem !important;
            text-align: center !important;
            background: linear-gradient(90deg, #FFFFFF 0%, #00F0FF 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 15px rgba(0, 240, 255, 0.1) !important;
        }

        /* Sidebar Navigation Item Overrides */
        [data-testid="stSidebarNav"] li {
            padding: 0.15rem 0.6rem !important;
        }

        [data-testid="stSidebarNavLink"] {
            background-color: transparent !important;
            border-radius: 8px !important;
            padding: 0.75rem 1.0rem !important;
            margin: 0.25rem 0 !important;
            border: 1px solid transparent !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
            color: #E2E8F0 !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            display: flex !important;
            align-items: center !important;
            gap: 0.75rem !important;
        }

        [data-testid="stSidebarNavLink"] span,
        [data-testid="stSidebarNavLink"] * {
            color: #E2E8F0 !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            font-family: 'Outfit', sans-serif !important;
            transition: color 0.25s ease !important;
        }

        /* Hover state */
        [data-testid="stSidebarNavLink"]:hover {
            background-color: rgba(255, 255, 255, 0.04) !important;
            border-color: rgba(255, 255, 255, 0.02) !important;
            color: #FFFFFF !important;
            transform: translateX(3px) !important;
        }

        [data-testid="stSidebarNavLink"]:hover span,
        [data-testid="stSidebarNavLink"]:hover * {
            color: #FFFFFF !important;
        }

        /* Active/Current page state */
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background: linear-gradient(90deg, rgba(0, 240, 255, 0.08) 0%, rgba(0, 240, 255, 0) 100%) !important;
            border-left: 3px solid #00F0FF !important;
            border-radius: 0 8px 8px 0 !important;
            color: #00F0FF !important;
            font-weight: 800 !important;
            box-shadow: inset 1px 0 0 rgba(0, 240, 255, 0.2) !important;
        }

        [data-testid="stSidebarNavLink"][aria-current="page"] span,
        [data-testid="stSidebarNavLink"][aria-current="page"] * {
            color: #00F0FF !important;
            font-weight: 800 !important;
            font-size: 1.2rem !important;
            text-shadow: 0 0 10px rgba(0, 240, 255, 0.2) !important;
        }

        /* Custom st.page_link element override inside the sidebar */
        [data-testid="stSidebar"] [data-testid="stPageLink"] {
            background-color: transparent !important;
            border-radius: 8px !important;
            margin: 0.15rem 0 !important;
            border: 1px solid transparent !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }

        [data-testid="stSidebar"] [data-testid="stPageLink"] a,
        [data-testid="stSidebar"] [data-testid="stPageLink"] button,
        [data-testid="stSidebar"] [data-testid="stPageLink"] p,
        [data-testid="stSidebar"] [data-testid="stPageLink"] span,
        [data-testid="stSidebar"] [data-testid="stPageLink"] div,
        [data-testid="stSidebar"] [data-testid="stPageLink"] * {
            color: #E2E8F0 !important;
            font-size: 1.25rem !important;
            font-weight: 700 !important;
            font-family: 'Outfit', sans-serif !important;
            text-decoration: none !important;
        }

        /* Hover states */
        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover {
            background-color: rgba(255, 255, 255, 0.05) !important;
            transform: translateX(3px) !important;
        }

        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover a,
        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover button,
        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover p,
        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover span,
        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover div,
        [data-testid="stSidebar"] [data-testid="stPageLink"]:hover * {
            color: #FFFFFF !important;
        }

        /* Active page state styling (disabled component state for current page) */
        [data-testid="stSidebar"] [data-testid="stPageLink"] button[disabled],
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[disabled],
        [data-testid="stSidebar"] [data-testid="stPageLink"] [disabled],
        [data-testid="stSidebar"] [data-testid="stPageLink"] [data-aria-disabled="true"] {
            background: linear-gradient(90deg, rgba(0, 240, 255, 0.08) 0%, rgba(0, 240, 255, 0) 100%) !important;
            border-left: 3px solid #00F0FF !important;
            border-radius: 0 8px 8px 0 !important;
            opacity: 1 !important;
            pointer-events: none !important;
        }

        [data-testid="stSidebar"] [data-testid="stPageLink"] [disabled] p,
        [data-testid="stSidebar"] [data-testid="stPageLink"] [disabled] span,
        [data-testid="stSidebar"] [data-testid="stPageLink"] [disabled] *,
        [data-testid="stSidebar"] [data-testid="stPageLink"] [data-aria-disabled="true"] p,
        [data-testid="stSidebar"] [data-testid="stPageLink"] [data-aria-disabled="true"] span,
        [data-testid="stSidebar"] [data-testid="stPageLink"] [data-aria-disabled="true"] * {
            color: #00F0FF !important;
            font-weight: 800 !important;
            font-size: 1.25rem !important;
            text-shadow: 0 0 10px rgba(0, 240, 255, 0.2) !important;
        }

        /* Sidebar Headers Styling */
        [data-testid="stSidebar"] [data-testid="stMarkdown"] h2,
        [data-testid="stSidebar"] [data-testid="stMarkdown"] h1,
        [data-testid="stSidebar"] [data-testid="stMarkdown"] h3 {
            color: #FFFFFF !important;
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
            padding-bottom: 0.4rem !important;
            margin-top: 1.25rem !important;
            margin-bottom: 0.6rem !important;
            letter-spacing: -0.01em !important;
        }

        /* Sidebar Selectbox Customizer */
        [data-testid="stSidebar"] div[data-baseweb="select"] {
            background-color: rgba(15, 23, 42, 0.7) !important;
            border: 1px solid rgba(0, 240, 255, 0.15) !important;
        }

        /* Slider Customizer Overrides */
        div[data-testid="stSlider"] [role="slider"] {
            background-color: #00F0FF !important;
            border: 2px solid #FFFFFF !important;
            box-shadow: 0 0 8px rgba(0, 240, 255, 0.6) !important;
        }

        div[data-testid="stSlider"] [aria-valuemax] {
            background-color: rgba(255, 255, 255, 0.08) !important;
        }

        /* Progress bars styling override */
        div[data-testid="stProgress"] > div > div > div > div {
            background-image: linear-gradient(90deg, #00F0FF 0%, #00FF87 100%) !important;
            box-shadow: 0 0 8px rgba(0, 240, 255, 0.4) !important;
        }

        /* Scroll-triggered reveal animations */
        .scroll-reveal {
            opacity: 0 !important;
            transform: translateY(30px) !important;
            animation: none !important;
            transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1), transform 0.8s cubic-bezier(0.16, 1, 0.3, 1) !important;
            will-change: opacity, transform;
        }

        .scroll-reveal.visible {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    </style>
    """
    css = css.replace(
        "radial-gradient(circle at 50% 0%, #0D1532 0%, #060814 80%)",
        f"radial-gradient(circle at 50% 0%, {glow_color} 0%, #060814 80%)",
    )
    st.markdown(css, unsafe_allow_html=True)

    # Inject JS scripts via components.html to bypass Streamlit script stripping
    import streamlit.components.v1 as components

    js_code = """
    <script>
        (function() {
            function animateKPIs() {
                try {
                    const parentDoc = window.parent.document;
                    if (!parentDoc) return;
                    const kpis = parentDoc.querySelectorAll('.kpi-value');
                    kpis.forEach(el => {
                        const originalText = el.textContent.trim();
                        if (el.dataset.lastVal === originalText) return;

                        const match = originalText.match(/([\\d,.]+)/);
                        if (!match) return;

                        const numStr = match[1].replace(/,/g, '');
                        const targetVal = parseFloat(numStr);
                        if (isNaN(targetVal)) return;

                        el.dataset.lastVal = originalText;

                        const prefix = originalText.substring(0, match.index);
                        const suffix = originalText.substring(match.index + match[1].length);
                        const decimals = numStr.includes('.') ? numStr.split('.')[1].length : 0;

                        const duration = 1000; // ms
                        let startTime = null;

                        function updateNumber(timestamp) {
                            if (!startTime) startTime = timestamp;
                            const progress = Math.min((timestamp - startTime) / duration, 1);
                            const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);

                            const currentVal = easeProgress * targetVal;

                            let formattedVal = currentVal.toFixed(decimals);
                            if (decimals === 0) {
                                formattedVal = Math.floor(currentVal).toLocaleString('en-US');
                            } else {
                                const parts = formattedVal.split('.');
                                parts[0] = Math.floor(parts[0]).toLocaleString('en-US');
                                formattedVal = parts.join('.');
                            }

                            el.textContent = prefix + formattedVal + suffix;

                            if (progress < 1) {
                                requestAnimationFrame(updateNumber);
                            } else {
                                el.textContent = originalText;
                            }
                        }

                        requestAnimationFrame(updateNumber);
                    });
                } catch (e) {
                    console.error("animateKPIs error:", e);
                }
            }

            function setupScrollReveal() {
                try {
                    const parentDoc = window.parent.document;
                    if (!parentDoc) return;

                    let parentStyle = parentDoc.getElementById('scroll-reveal-styles');
                    if (!parentStyle) {
                        parentStyle = parentDoc.createElement('style');
                        parentStyle.id = 'scroll-reveal-styles';
                        parentStyle.textContent = `
                            .scroll-reveal {
                                opacity: 0 !important;
                                transform: translateY(30px) !important;
                                animation: none !important;
                                transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1), transform 0.8s cubic-bezier(0.16, 1, 0.3, 1) !important;
                                will-change: opacity, transform;
                            }
                            .scroll-reveal.visible {
                                opacity: 1 !important;
                                transform: translateY(0) !important;
                            }
                        `;
                        parentDoc.head.appendChild(parentStyle);
                    }

                    const observer = new IntersectionObserver((entries, obs) => {
                        entries.forEach(entry => {
                            if (entry.isIntersecting) {
                                entry.target.classList.add('visible');
                                obs.unobserve(entry.target);
                            }
                        });
                    }, {
                        threshold: 0.05,
                        rootMargin: '0px 0px -40px 0px'
                    });

                    const targets = parentDoc.querySelectorAll(
                        '.glass-card, [data-testid="stImage"], .banner-container, [data-testid="metric-container"], table, .live-alert-card, .nav-card, h2, h3, hr, footer'
                    );

                    targets.forEach(el => {
                        if (el.closest('form')) return;
                        if (!el.classList.contains('scroll-reveal')) {
                            el.classList.add('scroll-reveal');
                            observer.observe(el);
                        }
                    });
                } catch (e) {
                    console.error("ScrollReveal error:", e);
                }
            }

            setTimeout(animateKPIs, 100);
            setTimeout(setupScrollReveal, 150);

            try {
                const parentDoc = window.parent.document;
                if (parentDoc) {
                    let debounceTimeout;
                    const observer = new MutationObserver(function() {
                        clearTimeout(debounceTimeout);
                        debounceTimeout = setTimeout(function() {
                            animateKPIs();
                            setupScrollReveal();
                        }, 100);
                    });
                    observer.observe(parentDoc.body, { childList: true, subtree: true });
                }
            } catch (e) {
                console.error("MutationObserver error:", e);
            }
        })();
    </script>
    """
    components.html(js_code, height=0, width=0)


def apply_plotly_theme(fig):
    """
    Reformats a Plotly figure to fit the premium dark dashboard layout.
    Adds smooth transition animations on redraws/load.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="Outfit, sans-serif",
        font_color="#94A3B8",
        title_font_color="#FFFFFF",
        title_font_family="Outfit, sans-serif",
        title_font_size=16,
        legend_font_color="#94A3B8",
        margin={"t": 40, "b": 40, "l": 40, "r": 40},
        xaxis={
            "gridcolor": "rgba(255,255,255,0.04)",
            "linecolor": "rgba(255,255,255,0.08)",
            "zerolinecolor": "rgba(255,255,255,0.04)",
            "tickfont": {"color": "#64748B"},
        },
        yaxis={
            "gridcolor": "rgba(255,255,255,0.04)",
            "linecolor": "rgba(255,255,255,0.08)",
            "zerolinecolor": "rgba(255,255,255,0.04)",
            "tickfont": {"color": "#64748B"},
        },
        transition={"duration": 500, "easing": "cubic-in-out"},
    )
    return fig


def render_custom_sidebar():
    """
    Renders user session and custom navigation in the sidebar based on user role.
    Organized with Navigation at the top, Page-Specific settings in the middle,
    and a styled User Profile Card + Logout button at the bottom.
    """
    if "user_token" not in st.session_state:
        return None

    # Pre-allocate containers to enforce layout hierarchy
    nav_container = st.sidebar.container()
    controls_container = st.sidebar.container()
    profile_container = st.sidebar.container()

    # Render Navigation links
    nav_container.markdown("### 🧭 Navigation")
    
    # Base link that everyone gets
    nav_container.page_link("App.py", label="Home Cockpit", icon="🛡️")
    
    role = st.session_state.get("user_role", "Compliance Officer")
    if role == "Compliance Officer":
        # Compliance Officer: Traffic Load Desk, Threat Intelligence, and GRC Governance
        nav_container.page_link("pages/7_Simulation.py", label="Volume Load Control Desk", icon="⚡")
        nav_container.page_link("pages/8_Threat_Intel.py", label="Threat Intelligence Registry", icon="📡")
        nav_container.page_link("pages/9_Governance.py", label="Governance & Audit Ledgers", icon="⚖️")
    elif role == "Analyst":
        # Analyst: Risk Evaluation, Factor Attribution, Entity Relationship Networks, and Case Management
        nav_container.page_link("pages/1_Realtime_Alerts.py", label="Risk Evaluation Center", icon="🚨")
        nav_container.page_link("pages/3_Explainability.py", label="Risk Factor Attribution", icon="🔎")
        nav_container.page_link("pages/3_Graph_Analysis.py", label="Entity Relationship Network", icon="🕸️")
        nav_container.page_link("pages/4_Cases.py", label="Case Management Workspace", icon="💼")
    elif role == "Auditor":
        # Auditor: Risk & Value Analytics, Model Integrity Checks, and Executive Compliance Reports
        nav_container.page_link("pages/2_Analytics.py", label="Risk & Value Analytics", icon="📊")
        nav_container.page_link("pages/5_Monitoring.py", label="Model Health & Integrity", icon="🔍")
        nav_container.page_link("pages/6_Reports.py", label="Executive Compliance Reports", icon="📑")

    nav_container.markdown("---")

    # Render User Profile Card & Logout in profile_container (Bottom)
    profile_container.markdown("---")
    
    # Styled HTML container for the user profile card
    profile_html = f"""
    <div style="
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 14px;
        margin-top: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    ">
        <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; display: flex; align-items: center; gap: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            <span>👤</span> {st.session_state.username}
        </div>
        <div style="font-size: 0.78rem; color: #00F0FF; font-weight: 600; margin-top: 4px; letter-spacing: 0.03em; text-transform: uppercase;">
            {st.session_state.user_role}
        </div>
        <div style="font-size: 0.75rem; color: #64748B; margin-top: 2px;">
            ID: <code style="color: #94A3B8; font-family: monospace;">{st.session_state.get('user_role_id', 'N/A')}</code>
        </div>
    </div>
    """
    profile_container.html(profile_html)
    
    if profile_container.button("Logout", key="logout_btn", use_container_width=True):
        if "user_token" in st.session_state:
            del st.session_state.user_token
        if "user_role" in st.session_state:
            del st.session_state.user_role
        if "username" in st.session_state:
            del st.session_state.username
        if "user_role_id" in st.session_state:
            del st.session_state.user_role_id
        if "user_display_name" in st.session_state:
            del st.session_state.user_display_name
        if "active_scoring_result" in st.session_state:
            del st.session_state.active_scoring_result
        st.rerun()

    return controls_container


