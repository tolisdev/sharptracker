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

        /* Enhanced sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #050814 0%, #0d1117 100%);
            border-right: 1px solid #21262d;
            padding-top: 1rem;
        }

        /* Option menu enhancements */
        .css-1v0mbdj .nav-link {
            border-radius: 8px !important;
            margin: 4px 0 !important;
            padding: 12px 16px !important;
            transition: all 0.2s ease !important;
        }

        .css-1v0mbdj .nav-link:hover {
            background: rgba(0, 255, 200, 0.1) !important;
            box-shadow: 0 4px 12px rgba(0, 255, 200, 0.15) !important;
        }

        .css-1v0mbdj .nav-link-selected {
            background: rgba(0, 255, 200, 0.15) !important;
            box-shadow: 0 4px 16px rgba(0, 255, 200, 0.25) !important;
        }

        /* Icons */
        .css-1v0mbdj .icon {
            margin-right: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
