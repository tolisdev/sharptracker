import streamlit as st
from datetime import datetime
from typing import List

import pandas as pd
from streamlit_gsheets import GSheetsConnection


def _get_conn() -> GSheetsConnection:
    return st.connection("gsheets", type=GSheetsConnection)


def _safe_load(tab_name: str, columns: List[str]) -> pd.DataFrame:
    conn = _get_conn()
    try:
        df = conn.read(worksheet=tab_name, ttl="0s")
        for col in columns:
            if col not in df.columns:
                df[col] = 0.0 if col in ["id", "Odds", "Stake", "P/L", "Cashout_Amt"] else ""
        return df
    except Exception:
        df = pd.DataFrame(columns=columns)
        conn.update(worksheet=tab_name, data=df)
        return df


def init_user_data(user: str):
    if "unsaved_count" not in st.session_state:
        st.session_state.unsaved_count = 0
    if "last_sync" not in st.session_state:
        st.session_state.last_sync = "Never"

    if "bets_df" in st.session_state:
        return

    bets_tab = f"bets_{user}"
    cash_tab = f"cash_{user}"
    meta_tab = f"meta_{user}"

    try:
        b_df = _safe_load(
            bets_tab,
            [
                "id", "Date", "Sport", "League", "Bookie", "Type",
                "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt",
                "Legs", "Tipster",
            ],
        )
        c_df = _safe_load(
            cash_tab,
            ["Date", "Bookie", "Type", "Amount"],
        )
        m_df = _safe_load(
            meta_tab,
            ["Sports", "Leagues", "Bookies", "Types", "Tipsters"],
        )

        if not b_df.empty:
            b_df["Date"] = pd.to_datetime(b_df["Date"]).dt.date
        if not c_df.empty:
            c_df["Date"] = pd.to_datetime(c_df["Date"]).dt.date

        st.session_state.bets_df = b_df
        st.session_state.cash_df = c_df
        st.session_state.meta_df = m_df
        st.session_state.bets_tab = bets_tab
        st.session_state.cash_tab = cash_tab
        st.session_state.meta_tab = meta_tab
        st.session_state.last_sync = datetime.now().strftime("%H:%M")

    except Exception as e:
        st.error(f"Data loading error: {e}")
        st.stop()


def push_to_cloud():
    conn = _get_conn()
    conn.update(worksheet=st.session_state.bets_tab, data=st.session_state.bets_df)
    conn.update(worksheet=st.session_state.cash_tab, data=st.session_state.cash_df)
    conn.update(worksheet=st.session_state.meta_tab, data=st.session_state.meta_df)
    st.session_state.unsaved_count = 0
    st.session_state.last_sync = datetime.now().strftime("%H:%M")
    st.success("All changes saved to cloud.")
    st.rerun()
