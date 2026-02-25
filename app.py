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

# --- 2. CLOUD CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(worksheet=name, ttl="0s")

def save_sheet(df, name):
    conn.update(worksheet=name, data=df)
    st.cache_data.clear()

# Initial Load
df_bets = load_sheet("Bets")
df_cash = load_sheet("Cash")
df_meta = load_sheet("Meta")

# Formatting
for df in [df_bets, df_cash]:
    if not df.empty and 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.date

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🎯 SharpTracker")
    nav = st.radio("Navigation", ["📊 Dashboard", "📝 Manage Bets", "💰 Bankroll", "⚙️ Settings"])
    st.divider()
    if not df_bets.empty:
        risk = df_bets[df_bets['Status'] == "Pending"]['Stake'].sum()
        profit = df_bets['P/L'].sum()
        st.metric("Money at Risk", f"${risk:,.2f}")
        st.metric("Total P/L", f"${profit:,.2f}", delta=f"{profit:,.2f}")

# --- 4. DASHBOARD PAGE ---
if nav == "📊 Dashboard":
    st.header("📈 Cloud Performance Analytics")
    if df_bets.empty:
        st.info("No data found. Log a bet to start!")
    else:
        with st.expander("🔍 Filters", expanded=True):
            c1, c2, c3 = st.columns(3)
            f_l = c1.multiselect("League", df_bets['League'].unique())
            f_b = c2.multiselect("Bookie", df_bets['Bookie'].unique())
            f_s = c3.multiselect("Sport", df_bets['Sport'].unique())

        dff = df_bets.copy()
        if f_l: dff = dff[dff['League'].isin(f_l)]
        if f_b: dff = dff[dff['Bookie'].isin(f_b)]
        if f_s: dff = dff[dff['Sport'].isin(f_s)]

        st.divider()
        dff_s = dff.sort_values("Date")
        dff_s['Cum'] = dff_s['P/L'].cumsum()
        st.plotly_chart(px.area(dff_s, x="Date", y="Cum", title="Equity Curve"), use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(px.bar(dff.groupby("Sport")['P/L'].sum().reset_index(), x='Sport', y='P/L', title="Profit by Sport"))
        with col_b:
            co_df = dff[dff['Status'] == "Cashed Out"]
            if not co_df.empty:
                st.plotly_chart(px.histogram(co_df, x="P/L", title="Cashout Profit Distribution"))

# --- 5. MANAGE BETS (WITH CASHOUT) ---
elif nav == "📝 Manage Bets":
    st.header("📝 Wager Management")

    with st.expander("➕ Log New Bet"):
        with st.form("new_bet_form"):
            c1, c2, c3 = st.columns(3)
            d_i = c1.date_input("Date", date.today())
            s_i = c1.selectbox("Sport", df_meta["Sports"].dropna().tolist())
            l_i = c1.selectbox("League", df_meta["Leagues"].dropna().tolist())
            b_i = c2.selectbox("Bookie", df_meta["Bookies"].dropna().tolist())
            t_i = c2.selectbox("Type", df_meta["Types"].dropna().tolist())
            e_i = c2.text_input("Selection")
            o_i = c3.number_input("Odds", 1.01, 100.0, 1.91)
            st_i = c3.number_input("Stake", 0.0, 50000.0, 10.0)
            res_i = c3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("Sync Wager"):
                pl = (st_i * o_i - st_i) if res_i == "Won" else (-st_i if res_i == "Lost" else 0.0)
                new_id = int(df_bets['id'].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame([[new_id, d_i, s_i, l_i, b_i, t_i, e_i, o_i, st_i, res_i, pl, 0.0]], columns=df_bets.columns)
                save_sheet(pd.concat([df_bets, new_row]), "Bets")
                st.rerun()

    pending = df_bets[df_bets['Status'] == "Pending"]
    if not pending.empty:
        st.subheader("🔔 Open Wagers")
        for idx, row in pending.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{row['Event']}** | {row['Bookie']} | ${row['Stake']}")
                res = col2.selectbox("Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"r_{row['id']}")
                co_val = 0.0
                if res == "Cashed Out":
                    co_val = col3.number_input("Payout", min_value=0.0, key=f"c_{row['id']}")
                if res != "Pending":
                    if st.button("Update Cloud", key=f"b_{row['id']}"):
                        df_bets.at[idx, 'Status'] = res
                        if res == "Won": df_bets.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake'])
                        elif res == "Lost": df_bets.at[idx, 'P/L'] = -row['Stake']
                        elif res == "Cashed Out":
                            df_bets.at[idx, 'P/L'] = co_val - row['Stake']
                            df_bets.at[idx, 'Cashout_Amt'] = co_val
                        save_sheet(df_bets, "Bets")
                        st.rerun()

# --- 6. BANKROLL PAGE ---
elif nav == "💰 Bankroll":
    st.header("💰 Bankroll Management")
    with st.form("cash_form"):
        c1, c2, c3 = st.columns(3)
        ct = c2.selectbox("Type", ["Deposit", "Withdrawal", "Bonus"])
        ca = c3.number_input("Amount", 0.0)
        if st.form_submit_button("Log Transaction"):
            final = -ca if ct == "Withdrawal" else ca
            new_c = pd.DataFrame([[date.today(), c1.selectbox("Bookie", df_meta["Bookies"].dropna().tolist()), ct, final]], columns=df_cash.columns)
            save_sheet(pd.concat([df_cash, new_c]), "Cash")
            st.rerun()

    summary = []
    for b in [x for x in df_meta["Bookies"].dropna().tolist()]:
        c_flow = df_cash[df_cash['Bookie'] == b]['Amount'].sum()
        p_flow = df_bets[df_bets['Bookie'] == b]['P/L'].sum()
        risk_flow = df_bets[(df_bets['Bookie'] == b) & (df_bets['Status'] == "Pending")]['Stake'].sum()
        summary.append({"Bookie": b, "Balance": c_flow + p_flow - risk_flow})
    st.table(pd.DataFrame(summary))

# --- 7. SETTINGS PAGE ---
elif nav == "⚙️ Settings":
    st.header("⚙️ Global Config")
    new_m = {}
    for cat in df_meta.columns:
        cur = [str(x) for x in df_meta[cat].dropna().tolist()]
        new_m[cat] = st.text_area(f"Edit {cat}", value="\n".join(cur)).split("\n")
    if st.button("Save Settings"):
        save_sheet(pd.DataFrame.from_dict(new_m, orient='index').transpose(), "Meta")
        st.success("Synced to Google Sheets!")
