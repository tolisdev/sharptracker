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

# ========== MINIMAL SIDEBAR ==========
with st.sidebar:
    # Compact header
    st.markdown(f"""
        <div style='padding: 1rem 1rem 0 1rem;'>
            <h3 style='color: #00ffc8; margin: 0; font-size: 22px; font-weight: 800;'>🎯</h3>
            <div style='color: #8b949e; font-size: 13px; font-weight: 600; margin-top: 4px;'>
                {user.upper()}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.caption(f"Last sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} unsaved**")
        if st.button("💾 Sync", use_container_width=True, key="sync_btn"):
            push_to_cloud()

    st.markdown("---")

    # CLEAN NAV BUTTONS (compact + elegant)
    col1, col2 = st.columns([1, 0.1])

    with col1:
        if st.button("📊 Dashboard", use_container_width=True, key="nav_dash"):
            st.session_state.selected_page = "Dashboard"
            st.rerun()

    with col2:
        st.markdown("")

    with col1:
        if st.button("🎯 Wagers", use_container_width=True, key="nav_wagers"):
            st.session_state.selected_page = "Wagers"
            st.rerun()

    with col2:
        st.markdown("")

    with col1:
        if st.button("💰 Bankroll", use_container_width=True, key="nav_bank"):
            st.session_state.selected_page = "Bankroll"
            st.rerun()

    with col2:
        st.markdown("")

    with col1:
        if st.button("⚙️ Settings", use_container_width=True, key="nav_set"):
            st.session_state.selected_page = "Settings"
            st.rerun()

    # Active indicator
    st.markdown("---")
    st.markdown(f"""
        <div style='padding: 12px; text-align: center;
                    background: rgba(0, 255, 200, 0.08);
                    border: 1px solid rgba(0, 255, 200, 0.2);
                    border-radius: 8px;'>
            <span style='color: #00ffc8; font-weight: 700; font-size: 13px;'>
                {st.session_state.get('selected_page', 'Dashboard')}
            </span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    logout_button()
