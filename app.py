import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import date

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="SharpTracker Cloud", layout="wide", page_icon="🛡️")

PASSWORD_SECRET = st.secrets.get("APP_PASSWORD", "admin")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 SharpTracker Login")
    pwd_input = st.text_input("Enter Password", type="password")
    if pwd_input == PASSWORD_SECRET:
        st.session_state["authenticated"] = True
        st.rerun()
    st.stop()

# --- 2. SESSION STATE ENGINE (The Rate-Limit Shield) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Track if we have unsaved changes
if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0

# Initial Pull from Google (Only happens once per app load)
if "bets_df" not in st.session_state:
    try:
        st.session_state.bets_df = conn.read(worksheet="Bets", ttl="0s")
        st.session_state.cash_df = conn.read(worksheet="Cash", ttl="0s")
        st.session_state.meta_df = conn.read(worksheet="Meta", ttl="0s")

        # Format dates
        for key in ['bets_df', 'cash_df']:
            if not st.session_state[key].empty:
                st.session_state[key]['Date'] = pd.to_datetime(st.session_state[key]['Date']).dt.date
    except Exception as e:
        st.error(f"Initial Cloud Pull Failed: {e}")
        st.stop()

# --- 3. SIDEBAR SYNC & AUTO-SAVE REMINDER ---
with st.sidebar:
    st.title("🎯 SharpTracker")

    # Unsaved Changes Warning
    if st.session_state.unsaved_count > 0:
        st.warning(f"⚠️ {st.session_state.unsaved_count} Unsaved Changes")
        if st.button("💾 PUSH TO GOOGLE SHEETS", type="primary", use_container_width=True):
            with st.spinner("Syncing..."):
                try:
                    conn.update(worksheet="Bets", data=st.session_state.bets_df)
                    conn.update(worksheet="Cash", data=st.session_state.cash_df)
                    conn.update(worksheet="Meta", data=st.session_state.meta_df)
                    st.session_state.unsaved_count = 0
                    st.success("Cloud Updated!")
                    st.rerun()
    else:
        st.success("✅ Cloud is up to date")
        if st.button("📥 Refresh from Cloud", use_container_width=True):
            for key in ["bets_df", "cash_df", "meta_df", "unsaved_count"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    st.divider()
    nav = st.radio("Navigation", ["📊 Dashboard", "📝 Manage Bets", "💰 Bankroll", "⚙️ Settings"])

# Logic Variables
df_bets = st.session_state.bets_df
df_cash = st.session_state.cash_df
df_meta = st.session_state.meta_df

# --- 4. DASHBOARD PAGE ---
if nav == "📊 Dashboard":
    st.header("📊 Performance Analytics")
    if df_bets.empty:
        st.info("No data in current session.")
    else:
        # Simple Stats
        profit = pd.to_numeric(df_bets['P/L']).sum()
        risk = df_bets[df_bets['Status'] == "Pending"]['Stake'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Net P/L", f"${profit:,.2f}")
        m2.metric("Money at Risk", f"${risk:,.2f}")
        m3.metric("Total Bets", len(df_bets))

        # Charts
        dff_s = df_bets.sort_values("Date")
        dff_s['Cum'] = dff_s['P/L'].cumsum()
        st.plotly_chart(px.area(dff_s, x="Date", y="Cum", title="Equity Curve"), use_container_width=True)

# --- 5. MANAGE BETS (Saves to Session) ---
elif nav == "📝 Manage Bets":
    st.header("📝 Wager Management")

    with st.expander("➕ Log New Bet"):
        with st.form("add_bet"):
            c1, c2, c3 = st.columns(3)
            # Fetch lists from meta
            s_list = df_meta["Sports"].dropna().tolist() if not df_meta.empty else []
            l_list = df_meta["Leagues"].dropna().tolist() if not df_meta.empty else []
            b_list = df_meta["Bookies"].dropna().tolist() if not df_meta.empty else []

            d_i = c1.date_input("Date", date.today())
            s_i = c1.selectbox("Sport", s_list)
            l_i = c1.selectbox("League", l_list)
            b_i = c2.selectbox("Bookie", b_list)
            e_i = c2.text_input("Selection")
            o_i = c3.number_input("Odds", 1.01, 100.0, 1.91)
            st_i = c3.number_input("Stake", 0.0, 10000.0, 10.0)
            res_i = c3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("Add to Session"):
                pl = (st_i * o_i - st_i) if res_i == "Won" else (-st_i if res_i == "Lost" else 0.0)
                new_id = int(df_bets['id'].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame([[new_id, d_i, s_i, l_i, b_i, "ML", e_i, o_i, st_i, res_i, pl, 0.0]],
                                       columns=["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"])
                st.session_state.bets_df = pd.concat([df_bets, new_row], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.rerun()

    # Settle Pending
    pending = df_bets[df_bets['Status'] == "Pending"]
    if not pending.empty:
        st.subheader("🔔 Settle Wagers")
        for idx, row in pending.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{row['Event']}** | ${row['Stake']}")
                res = col2.selectbox("Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"r_{row['id']}")
                co_val = col3.number_input("Payout", 0.0, key=f"c_{row['id']}") if res == "Cashed Out" else 0.0

                if res != "Pending":
                    if st.button("Update Session", key=f"b_{row['id']}"):
                        st.session_state.bets_df.at[idx, 'Status'] = res
                        if res == "Won": st.session_state.bets_df.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake'])
                        elif res == "Lost": st.session_state.bets_df.at[idx, 'P/L'] = -row['Stake']
                        elif res == "Cashed Out":
                            st.session_state.bets_df.at[idx, 'P/L'] = co_val - row['Stake']
                            st.session_state.bets_df.at[idx, 'Cashout_Amt'] = co_val
                        st.session_state.unsaved_count += 1
                        st.rerun()

    # History/Delete
    st.divider()
    for idx, row in df_bets.sort_values("Date", ascending=False).iterrows():
        with st.expander(f"{row['Date']} | {row['Event']} ({row['Status']})"):
            if st.button("Remove Locally", key=f"del_{row['id']}"):
                st.session_state.bets_df = df_bets.drop(idx)
                st.session_state.unsaved_count += 1
                st.rerun()

# --- 6. BANKROLL PAGE ---
elif nav == "💰 Bankroll":
    st.header("💰 Bankroll Management")
    with st.form("cash_form"):
        c1, c2, c3 = st.columns(3)
        cb = c1.selectbox("Bookie", df_meta["Bookies"].dropna().tolist() if not df_meta.empty else [])
        ct = c2.selectbox("Type", ["Deposit", "Withdrawal", "Bonus"])
        ca = c3.number_input("Amount", 0.0)
        if st.form_submit_button("Log Transaction"):
            final = -ca if ct == "Withdrawal" else ca
            new_c = pd.DataFrame([[date.today(), cb, ct, final]], columns=["Date", "Bookie", "Type", "Amount"])
            st.session_state.cash_df = pd.concat([df_cash, new_c], ignore_index=True)
            st.session_state.unsaved_count += 1
            st.rerun()

# --- 7. SETTINGS PAGE ---
elif nav == "⚙️ Settings":
    st.header("⚙️ Configuration")
    new_m = {}
    cols = st.columns(len(df_meta.columns))
    for i, cat in enumerate(df_meta.columns):
        with cols[i]:
            cur = [str(x) for x in df_meta[cat].dropna().tolist()]
            inp = st.text_area(f"Edit {cat}", value="\n".join(cur), height=300)
            new_m[cat] = inp.split("\n")

    if st.button("Update Session Config"):
        st.session_state.meta_df = pd.DataFrame.from_dict(new_m, orient='index').transpose()
        st.session_state.unsaved_count += 1
        st.success("Session settings updated!")
