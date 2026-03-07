import streamlit as st

def _reset_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def ensure_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None

    if st.session_state.authenticated:
        return st.session_state.username

    st.title("🎯 SharpTracker Elite")
    st.markdown("#### Secure System Access")

    with st.container(border=True):
        u_in = st.text_input("Username", placeholder="Your ID")
        p_in = st.text_input("Password", type="password", placeholder="••••••••")
        login = st.button("Unlock Environment", use_container_width=True)

        if login:
            user_db = st.secrets.get("users", {})
            if u_in in user_db and p_in == user_db[u_in]:
                st.session_state.authenticated = True
                st.session_state.username = u_in
                st.success("Access granted. Loading your environment…")
                st.rerun()
            else:
                st.error("Invalid credentials. Please verify your username/password.")

    return None

def logout_button():
    if st.button("🚪 Logout", use_container_width=True):
        _reset_session()
        st.rerun()
