import streamlit as st

from auth import ensure_auth, logout_button
from data.analytics import basic_counters  # we'll use this
from data.data_layer import init_user_data, push_to_cloud
from styling import inject_global_css
from views.bankroll import render_bankroll
from views.dashboard import render_dashboard
from views.settings import render_settings
from views.wagers import render_wagers

st.set_page_config(page_title="SharpTracker Elite", layout="wide", page_icon="🎯")
inject_global_css()

user = ensure_auth()
if user is None:
    st.stop()

init_user_data(user)

# Initialize page state
if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Dashboard"

# ========== CLEAN SIDEBAR ==========
with st.sidebar:
    # Header
    st.markdown("### 🎯 SharpTracker")
    st.caption(f"*{user.upper()}*")

    st.caption(f"Last sync: {st.session_state.last_sync}")

    # PROFIT & RTP COUNTERS
    df_bets = st.session_state.bets_df
    if not df_bets.empty:
        counters = basic_counters(df_bets)
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.metric("Profit", f"${counters['net_pl']:,.0f}")
        with col_p2:
            st.metric("ROI", f"{counters['roi_pct']:.1f}%")
    else:
        st.caption("📊 Log bets to see stats")

    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} unsaved**")
        if st.button("💾 Sync", use_container_width=True):
            push_to_cloud()

    st.markdown("---")

    # Navigation (matches your screenshot exactly)
    if st.button("📊 Dashboard", use_container_width=True):
        st.session_state.selected_page = "Dashboard"
        st.rerun()

    if st.button("🎯 Wagers", use_container_width=True):
        st.session_state.selected_page = "Wagers"
        st.rerun()

    if st.button("💰 Bankroll", use_container_width=True):
        st.session_state.selected_page = "Bankroll"
        st.rerun()

    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.selected_page = "Settings"
        st.rerun()

    st.markdown("---")
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
