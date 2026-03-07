import streamlit as st
from streamlit_option_menu import option_menu

from auth import ensure_auth, logout_button
from data_layer import init_user_data, push_to_cloud
from styling import inject_global_css
from views_dashboard import render_dashboard
from views_wagers import render_wagers
from views_bankroll import render_bankroll
from views_settings import render_settings

st.set_page_config(page_title="SharpTracker Elite", layout="wide", page_icon="🎯")
inject_global_css()

user = ensure_auth()
if user is None:
    st.stop()

init_user_data(user)

# ========== PRETTY SIDEBAR ==========
with st.sidebar:
    st.markdown(f"## 🎯 **{user.upper()}**")
    st.caption(f"Status: Synchronized  •  Last sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} Unsaved Changes**")
        if st.button("💾 Push to Cloud", type="primary", use_container_width=True):
            push_to_cloud()

    st.markdown("---")

    # BEAUTIFUL NAVIGATION MENU
    selected = option_menu(
        menu_title=None,  # title for this block
        options=["Dashboard", "Wagers", "Bankroll", "Settings"],
        icons=["graph-up", "receipt", "wallet2", "gear-fill"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {
                "padding": "5px 14px",
                "margin": "0",
                "background-color": "#050814",
            },
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "0px",
                "--hover-color": "#00ffc8",
            },
            "nav-link-selected": {
                "background-color": "transparent",
                "color": "#00ffc8",
            },
            "icon": {
                "font-size": "18px",
                "color": "#8b949e",
            },
            "icon-selected": {
                "color": "#00ffc8",
            },
        },
    )

    st.markdown("---")
    logout_button()

    # FOOTER
    st.markdown(
        """
        <div style='text-align: center; color: #8b949e; font-size: 11px;
                    font-weight: 700; margin-top: 2rem;'>
            Made by Akenza Web Studio
        </div>
        """,
        unsafe_allow_html=True,
    )

# ========== PAGE ROUTING ==========
if selected == "Dashboard":
    render_dashboard()
elif selected == "Wagers":
    render_wagers(user)
elif selected == "Bankroll":
    render_bankroll()
elif selected == "Settings":
    render_settings()
