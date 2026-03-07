import streamlit as st


def inject_global_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #0d1117;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        /* PERFECT SIDEBAR BUTTONS */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #050814 0%, #0d1117 100%);
            border-right: 1px solid #21262d;
            padding-top: 1rem;
        }

        /* Sidebar buttons */
        .stButton > button {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            padding: 14px 16px !important;
            margin: 6px 0 !important;
            height: auto !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            color: #e6edf3 !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
        }

        .stButton > button:hover {
            background: rgba(0, 255, 200, 0.12) !important;
            border-color: rgba(0, 255, 200, 0.4) !important;
            color: #00ffc8 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 8px 25px rgba(0, 255, 200, 0.2) !important;
        }

        .stButton > button:active {
            transform: translateY(0px) !important;
        }

        /* Push button */
        button[kind="primary"] {
            background: linear-gradient(135deg, #00ffc8 0%, #00e6b3 100%) !important;
            border-color: rgba(0, 255, 200, 0.3) !important;
            color: #050814 !important;
            box-shadow: 0 6px 20px rgba(0, 255, 200, 0.3) !important;
        }

        button[kind="primary"]:hover {
            background: linear-gradient(135deg, #00e6b3 0%, #00d4a8 100%) !important;
            box-shadow: 0 10px 30px rgba(0, 255, 200, 0.4) !important;
            transform: translateY(-2px) !important;
        }

        /* Secondary buttons (delete, etc.) */
        button[kind="secondary"] {
            color: #ff6b6b !important;
            border-color: rgba(255, 107, 107, 0.4) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
