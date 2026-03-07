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
        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }

        [data-testid="stSidebar"] {
            background-color: #050814;
            border-right: 1px solid #21262d;
        }

        /* We’ll upgrade nav styling in the next step */
        </style>
        """,
        unsafe_allow_html=True,
    )
py
