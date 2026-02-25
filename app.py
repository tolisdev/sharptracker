import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import date

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="SharpTracker Cloud", layout="wide", page_icon="📈")
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

# --- 2. THE SYNC ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch_all():
    """Fetches fresh data from Google Sheets"""
    try:
        bets = conn.read(worksheet="Bets", ttl="0s")
        cash = conn.read(worksheet="Cash", ttl="0s")
        meta = conn.read(worksheet="Meta", ttl="0s")
        return bets, cash, meta
    except Exception as e:
        st.error(f"Cloud Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def push_and_refresh(df, sheet_name):
    """Saves to Cloud and clears cache to force a fresh fetch"""
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
        st.toast(f"✅ {sheet_name} Synced to Cloud!")
    except Exception as e:
        st.error(f"Save Error: {e}")

# INITIAL FETCH (Run on every start/refresh)
df_bets, df_cash, df_meta = fetch_all()

# Clean dates for the UI
for df in [df_bets, df_cash]:
    if not df.empty and 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.date

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🎯 SharpTracker")
    if st.button("🔄 Force Cloud Sync"):
        st.rerun()

    nav = st.radio("Navigation", ["📊 Dashboard", "📝 Manage Bets", "💰 Bankroll", "⚙️ Settings"])

    st.divider()
    if not df_bets.empty:
        risk = df_bets[df_bets['Status'] == "Pending"]['Stake'].sum()
        profit = pd.to_numeric(df_bets['P/L']).sum()
        st.metric("Money at Risk", f"${risk:,.2f}")
        st.metric("Total P/L", f"${profit:,.2f}")

# --- 4. DASHBOARD ---
if nav == "📊 Dashboard":
    st.header("📊 Performance Analytics")
    if df_bets.empty:
        st.info("Cloud is empty. Add your first wager in 'Manage Bets'.")
    else:
        # Filters
        c1, c2, c3 = st.columns(3)
        f_l = c1.multiselect("League", df_bets['League'].unique())
        f_b = c2.multiselect("Bookie", df_bets['Bookie'].unique())
        f_s = c3.multiselect("Sport", df_bets['Sport'].unique())

        dff = df_bets.copy()
        if f_l: dff = dff[dff['League'].isin(f_l)]
        if f_b: dff = dff[dff['Bookie'].isin(f_b)]
        if f_s: dff = dff[dff['Sport'].isin(f_s)]

        # Growth Chart
        dff_s = dff.sort_values("Date")
        dff_s['Cum'] = dff_s['P/L'].cumsum()
        st.plotly_chart(px.area(dff_s, x="Date", y="Cum", title="Cloud Equity Curve"), use_container_width=True)

        # Cashout Analysis
        co_df = dff[dff['Status'] == "Cashed Out"]
        if not co_df.empty:
            st.plotly_chart(px.histogram(co_df, x="P/L", title="Cashout ROI Analysis", color_discrete_sequence=['gold']))

# --- 5. MANAGE BETS (Edit & Save) ---
elif nav == "📝 Manage Bets":
    st.header("📝 Wager Management")

    with st.expander("➕ Log New Bet"):
        with st.form("add_bet_form"):
            c1, c2, c3 = st.columns(3)
            # Safe meta fetching
            s_list = df_meta["Sports"].dropna().tolist() if not df_meta.empty else ["Default"]
            l_list = df_meta["Leagues"].dropna().tolist() if not df_meta.empty else ["Default"]
            b_list = df_meta["Bookies"].dropna().tolist() if not df_meta.empty else ["Default"]

            d_i = c1.date_input("Date", date.today())
            s_i = c1.selectbox("Sport", s_list)
            l_i = c1.selectbox("League", l_list)
            b_i = c2.selectbox("Bookie", b_list)
            e_i = c2.text_input("Selection")
            o_i = c3.number_input("Odds", 1.01, 100.0, 1.91)
            st_i = c3.number_input("Stake", 0.0, 10000.0, 10.0)
            res_i = c3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("Sync Wager to Google"):
                pl = (st_i * o_i - st_i) if res_i == "Won" else (-st_i if res_i == "Lost" else 0.0)
                new_id = int(df_bets['id'].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame([[new_id, d_i, s_i, l_i, b_i, "ML", e_i, o_i, st_i, res_i, pl, 0.0]],
                                       columns=["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"])
                push_and_refresh(pd.concat([df_bets, new_row]), "Bets")
                st.rerun()

    # Settlement Logic
    pending = df_bets[df_bets['Status'] == "Pending"]
    if not pending.empty:
        st.subheader("🔔 Open Wagers")
        for idx, row in pending.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{row['Event']}** | ${row['Stake']}")
                res = col2.selectbox("Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"r_{row['id']}")
                co_val = col3.number_input("Payout", 0.0, key=f"c_{row['id']}") if res == "Cashed Out" else 0.0

                if res != "Pending":
                    if st.button("Update Cloud", key=f"b_{row['id']}"):
                        df_bets.at[idx, 'Status'] = res
                        if res == "Won": df_bets.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake'])
                        elif res == "Lost": df_bets.at[idx, 'P/L'] = -row['Stake']
                        elif res == "Cashed Out":
                            df_bets.at[idx, 'P/L'] = co_val - row['Stake']
                            df_bets.at[idx, 'Cashout_Amt'] = co_val
                        push_and_refresh(df_bets, "Bets")
                        st.rerun()

# --- 6. BANKROLL ---
elif nav == "💰 Bankroll":
    st.header("💰 Bankroll & Bonuses")
    with st.form("cash_form"):
        c1, c2, c3 = st.columns(3)
        cb = c1.selectbox("Bookie", df_meta["Bookies"].dropna().tolist() if not df_meta.empty else ["Default"])
        ct = c2.selectbox("Type", ["Deposit", "Withdrawal", "Bonus"])
        ca = c3.number_input("Amount", 0.0)
        if st.form_submit_button("Log Transaction"):
            final = -ca if ct == "Withdrawal" else ca
            new_c = pd.DataFrame([[date.today(), cb, ct, final]], columns=["Date", "Bookie", "Type", "Amount"])
            push_and_refresh(pd.concat([df_cash, new_c]), "Cash")
            st.rerun()

# --- 7. SETTINGS ---
elif nav == "⚙️ Settings":
    st.header("⚙️ Global Settings")
    new_m = {}
    cols = st.columns(len(df_meta.columns))
    for i, cat in enumerate(df_meta.columns):
        with cols[i]:
            cur = [str(x) for x in df_meta[cat].dropna().tolist()]
            new_m[cat] = st.text_area(f"Edit {cat}", value="\n".join(cur), height=300).split("\n")

    if st.button("Overwrite Cloud Config"):
        push_and_refresh(pd.DataFrame.from_dict(new_m, orient='index').transpose(), "Meta")
        st.rerun()
