import streamlit as st

def inject_global_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: #0a0e17;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        margin: 2px 0;
        height: 44px;
    }

    .stButton > button:hover {
        background-color: #00d4ff !important;
        color: #000 !important;
    }

    button[kind="primary"] {
        background-color: #00ffc8 !important;
        color: #000 !important;
    }
    </style>
    """, unsafe_allow_html=True)
