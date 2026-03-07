import streamlit as st

def inject_global_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0a0e17;
        padding-top: 1rem;
    }

    /* Sidebar buttons - exact match to screenshot */
    .stButton > button {
        background: #1a2332 !important;
        border: 1px solid #2a3444 !important;
        border-radius: 8px !important;
        padding: 14px 20px !important;
        margin: 2px 0 !important;
        height: 52px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #e6f0ff !important;
        box-shadow: none !important;
    }

    .stButton > button:hover {
        background: #00d4ff !important;
        border-color: #00b8e6 !important;
        color: #0a0e17 !important;
        box-shadow: 0 4px 16px rgba(0, 212, 255, 0.3) !important;
    }

    /* Sync button */
    button[kind="primary"] {
        background: linear-gradient(135deg, #00ffc8 0%, #00e6b3 100%) !important;
        border: none !important;
        color: #0a0e17 !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 16px rgba(0, 255, 200, 0.4) !important;
    }

    /* Metrics in sidebar */
    [data-testid="stMetricValue"] {
        font-size: 22px !important;
        color: #00ffc8 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #8b9ba5 !important;
        font-size: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)
