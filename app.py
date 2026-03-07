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

# Initialize page state if missing
if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Dashboard"

# ========== CLEAN SIDEBAR ==========
with st.sidebar:
    # Header
    col_h1, col_h2 = st.columns([1, 2])
    with col_h1:
        st.markdown("### 🎯 SharpTracker")
    with col_h2:
        st.caption(f"*{user.upper()}*")

    st.caption(f"Last sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} unsaved**")
        if st.button("💾 Sync", use_container_width=True):
            push_to_cloud()

    st.markdown("---")

    # Navigation buttons
    if st.button("📊 Dashboard", use_container_width=True, key="btn_dash"):
        st.session_state.selected_page = "Dashboard"
        st.rerun()

    if st.button("🎯 Wagers", use_container_width=True, key="btn_wagers"):
        st.session_state.selected_page = "Wagers"
        st.rerun()

    if st.button("💰 Bankroll", use_container_width=True, key="btn_bank"):
        st.session_state.selected_page = "Bankroll"
        st.rerun()

    if st.button("⚙️ Settings", use_container_width=True, key="btn_settings"):
        st.session_state.selected_page = "Settings"
        st.rerun()

    st.markdown("---")

    # Active page indicator
    st.success(f"→ {st.session_state.selected_page}", icon="✅")

    logout_button()

# ========== ROUTING ==========
selected = st.session_state.selected_page

if selected == "Dashboard":
    render_dashboard()
elif selected == "Wagers":
    render_wagers(user)
elif selected == "Bankroll":
    render_bankroll()
elif selected == "Settings":
    render_settings()
