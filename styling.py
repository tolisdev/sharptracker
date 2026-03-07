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

        /* CLEAN SIDEBAR BUTTONS */
        [data-testid="stSidebar"] {
            background: #0a0f1a !important;
            border-right: 1px solid #1a2332 !important;
        }

        .stButton > button {
            background: rgba(20, 25, 40, 0.8) !important;
            border: 1px solid rgba(60, 70, 90, 0.5) !important;
            border-radius: 8px !important;
            padding: 12px 16px !important;
            margin: 3px 0 !important;
            height: 48px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #e2e8f0 !important;
            box-shadow: none !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            background: rgba(0, 255, 200, 0.08) !important;
            border-color: rgba(0, 255, 200, 0.3) !important;
            color: #00ffc8 !important;
            box-shadow: 0 2px 12px rgba(0, 255, 200, 0.15) !important;
            transform: none !important;
        }

        /* Sync button */
        button[kind="primary"] {
            background: linear-gradient(135deg, #00ffc8 0%, #00e0b5 100%) !important;
            border: none !important;
            color: #0a0f1a !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 16px rgba(0, 255, 200, 0.3) !important;
        }

        button[kind="primary"]:hover {
            box-shadow: 0 6px 20px rgba(0, 255, 200, 0.4) !important;
        }

        /* Logout */
        button:has(span:contains("Logout")) {
            color: #ff6b6b !important;
            border-color: rgba(255, 107, 107, 0.4) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
