import streamlit as st

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

with st.sidebar:
    st.subheader(f"🎯 SharpTracker: {user.upper()}")
    st.caption(f"Status: Synchronized  •  Last sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        if st.button("💾 Push to Cloud", type="primary", use_container_width=True):
            push_to_cloud()

    logout_button()

    st.markdown("---")

    # prettier menu placeholder: we’ll improve this in next step
    nav = st.radio(
        "Navigation",
        ["Dashboard", "Wagers", "Bankroll", "Settings"],
        label_visibility="collapsed",
    )

if nav == "Dashboard":
    render_dashboard()
elif nav == "Wagers":
    render_wagers(user)
elif nav == "Bankroll":
    render_bankroll()
elif nav == "Settings":
    render_settings()
