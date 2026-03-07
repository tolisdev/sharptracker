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

# ========== BULLETPROOF SIDEBAR ==========
with st.sidebar:
    st.markdown(f"## 🎯 **{user.upper()}**")
    st.caption(f"Status: Synchronized  •  Last sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} Unsaved Changes**")
        if st.button("💾 Push to Cloud", type="primary", use_container_width=True):
            push_to_cloud()

    st.markdown("---")

    # PURE CSS BUTTON NAVIGATION (NO LAG!)
    if "selected_page" not in st.session_state:
        st.session_state.selected_page = "Dashboard"

    # Button definitions
    pages = [
        ("Dashboard", "📊", "#00ffc8"),
        ("Wagers", "🎯", "#00d4ff"),
        ("Bankroll", "💰", "#00ff88"),
        ("Settings", "⚙️", "#ffaa00"),
    ]

    for page_name, icon, color in pages:
        if st.button(f"{icon} {page_name}",
                    key=f"nav_{page_name}",
                    use_container_width=True,
                    help=f"Go to {page_name}"):
            st.session_state.selected_page = page_name
            st.rerun()

    # Visual indicator for current page
    st.markdown("---")
    st.markdown(
        f"""
        <div style='text-align: center; padding: 12px;
                    background: rgba(0, 255, 200, 0.1);
                    border-radius: 10px; border: 1px solid rgba(0, 255, 200, 0.3);'>
            <span style='color: #00ffc8; font-weight: 700; font-size: 14px;'>
                {st.session_state.selected_page}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    logout_button()

# ========== PAGE ROUTING ==========
selected = st.session_state.selected_page

if selected == "Dashboard":
    render_dashboard()
elif selected == "Wagers":
    render_wagers(user)
elif selected == "Bankroll":
    render_bankroll()
elif selected == "Settings":
    render_settings()
