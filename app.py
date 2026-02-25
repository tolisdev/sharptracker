import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
from datetime import date

# --- 1. CONFIG & AUTHENTICATION ---
st.set_page_config(page_title="SharpTracker Pro", layout="wide", page_icon="📈")

# Password logic: Checks Streamlit Cloud secrets first, then defaults to "admin"
PASSWORD_SECRET = st.secrets.get("APP_PASSWORD", "admin")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 SharpTracker Login")
    pwd_input = st.text_input("Enter Password", type="password")
    if st.button("Unlock System"):
        if pwd_input == PASSWORD_SECRET:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid Password")
    st.stop()

# --- 2. DATA ENGINES ---
DB_FILE = "bet_data.csv"
CASH_FILE = "cash_log.csv"
META_FILE = "meta_config.csv"

def load_data(file, columns):
    if os.path.exists(file):
        df = pd.read_csv(file)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    return pd.DataFrame(columns=columns)

def load_meta():
    if os.path.exists(META_FILE):
        return pd.read_csv(META_FILE).to_dict('list')
    return {
        "Sports": ["Football", "Basketball", "Tennis"],
        "Leagues": ["NFL", "NBA", "ATP"],
        "Bookies": ["Pinnacle", "Bet365"],
        "Types": ["Moneyline", "Spread", "Total"]
    }

def save_meta(m_dict):
    cleaned = {k: [str(x).strip() for x in v if str(x).strip() and str(x) != 'nan'] for k, v in m_dict.items()}
    pd.DataFrame.from_dict(cleaned, orient='index').transpose().to_csv(META_FILE, index=False)

# Load State
df_bets = load_data(DB_FILE, ["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L"])
df_cash = load_data(CASH_FILE, ["Date", "Bookie", "Type", "Amount"])
meta = load_meta()

# --- 3. SIDEBAR (PORTABILITY & METRICS) ---
with st.sidebar:
    st.title("🎯 SharpTracker")

    st.subheader("💾 Data Portability")
    # Export
    if not df_bets.empty:
        csv_data = df_bets.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV Backup", data=csv_data, file_name=f"bets_{date.today()}.csv", mime="text/csv")

    # Import
    uploaded = st.file_uploader("📤 Import/Merge CSV", type="csv")
    if uploaded:
        if st.button("Confirm Merge"):
            imp_df = pd.read_csv(uploaded)
            if 'Date' in imp_df.columns: imp_df['Date'] = pd.to_datetime(imp_df['Date']).dt.date
            df_bets = pd.concat([df_bets, imp_df]).drop_duplicates(subset=['Date', 'Event', 'Stake', 'Odds'])
            df_bets.to_csv(DB_FILE, index=False)
            st.success("Merged!")
            st.rerun()

    st.divider()
    nav = st.radio("Navigation", ["📊 Dashboard", "📝 Manage Bets", "💰 Bankroll", "⚙️ Settings"])

    st.divider()
    if not df_bets.empty:
        risk = df_bets[df_bets['Status'] == "Pending"]['Stake'].sum()
        st.metric("Money at Risk", f"${risk:,.2f}")
        st.metric("Net Betting P/L", f"${df_bets['P/L'].sum():,.2f}")

# --- 4. DASHBOARD PAGE ---
if nav == "📊 Dashboard":
    st.header("📈 Performance Dashboard")
    if df_bets.empty:
        st.info("No data yet. Log some bets to see the magic.")
    else:
        with st.expander("🔍 Global Filters", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            f_sport = c1.multiselect("Sport", df_bets['Sport'].unique())
            f_league = c2.multiselect("League", df_bets['League'].unique())
            f_bookie = c3.multiselect("Bookie", df_bets['Bookie'].unique())
            f_type = c4.multiselect("Bet Type", df_bets['Type'].unique())

        dff = df_bets.copy()
        if f_sport: dff = dff[dff['Sport'].isin(f_sport)]
        if f_league: dff = dff[dff['League'].isin(f_league)]
        if f_bookie: dff = dff[dff['Bookie'].isin(f_bookie)]
        if f_type: dff = dff[dff['Type'].isin(f_type)]

        # KPIs
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        prof = dff['P/L'].sum()
        stk = dff['Stake'].sum()
        m1.metric("Filtered Profit", f"${prof:,.2f}")
        m2.metric("ROI", f"{(prof/stk*100 if stk>0 else 0):.2f}%")
        m3.metric("Win Rate", f"{(len(dff[dff['Status']=='Won'])/len(dff[dff['Status'].isin(['Won','Lost'])])*100 if len(dff[dff['Status'].isin(['Won','Lost'])])>0 else 0):.1f}%")
        m4.metric("Total Bets", len(dff))

        # Visuals
        dff_s = dff.sort_values("Date")
        dff_s['Cum'] = dff_s['P/L'].cumsum()
        st.plotly_chart(px.area(dff_s, x="Date", y="Cum", title="Equity Curve", template="plotly_dark"), use_container_width=True)

        g1, g2 = st.columns(2)
        g1.plotly_chart(px.bar(dff.groupby("Sport")['P/L'].sum().reset_index(), x='Sport', y='P/L', title="Profit by Sport"), use_container_width=True)
        g2.plotly_chart(px.pie(dff, values='Stake', names='Bookie', title="Stake by Bookie"), use_container_width=True)

# --- 5. MANAGE BETS PAGE ---
elif nav == "📝 Manage Bets":
    st.header("📝 Wager Management")

    with st.expander("➕ Log New Bet"):
        with st.form("new_bet"):
            c1, c2, c3 = st.columns(3)
            d_in = c1.date_input("Date", date.today())
            s_in = c1.selectbox("Sport", meta["Sports"])
            l_in = c1.selectbox("League", meta["Leagues"])
            b_in = c2.selectbox("Bookie", meta["Bookies"])
            t_in = c2.selectbox("Type", meta["Types"])
            e_in = c2.text_input("Selection")
            o_in = c3.number_input("Odds", 1.01, 100.0, 1.91)
            st_in = c3.number_input("Stake", 0.0, 100000.0, 10.0)
            res_in = c3.selectbox("Status", ["Pending", "Won", "Lost", "Push"])

            if st.form_submit_button("Record Bet"):
                pl = (st_in*o_in-st_in) if res_in=="Won" else (-st_in if res_in=="Lost" else 0.0)
                new_id = df_bets['id'].max() + 1 if not df_bets.empty else 1
                new_row = pd.DataFrame([[new_id, d_in, s_in, l_in, b_in, t_in, e_in, o_in, st_in, res_in, pl]], columns=df_bets.columns)
                pd.concat([df_bets, new_row]).to_csv(DB_FILE, index=False)
                st.rerun()

    # Bulk Settle
    pending = df_bets[df_bets['Status'] == "Pending"]
    if not pending.empty:
        st.subheader("🔔 Settle Pending")
        for idx, row in pending.iterrows():
            with st.container(border=True):
                col_i, col_s = st.columns([4, 1])
                col_i.write(f"**{row['Event']}** ({row['Bookie']}) | ${row['Stake']}")
                res = col_s.selectbox("Result", ["Pending", "Won", "Lost", "Push"], key=f"s_{row['id']}")
                if res != "Pending":
                    df_bets.at[idx, 'Status'] = res
                    df_bets.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake']) if res=="Won" else (-row['Stake'] if res=="Lost" else 0.0)
                    df_bets.to_csv(DB_FILE, index=False)
                    st.rerun()

    st.divider()
    for idx, row in df_bets.sort_values("Date", ascending=False).iterrows():
        with st.expander(f"{row['Date']} | {row['Event']} | {row['Status']}"):
            if st.button("Delete Bet", key=f"d_{row['id']}"):
                df_bets.drop(idx).to_csv(DB_FILE, index=False)
                st.rerun()

# --- 6. BANKROLL PAGE ---
elif nav == "💰 Bankroll":
    st.header("💰 Bankroll Control")
    with st.form("cash"):
        c1, c2, c3 = st.columns(3)
        cd = c1.date_input("Date")
        cb = c1.selectbox("Bookie", meta["Bookies"])
        ct = c2.selectbox("Type", ["Deposit", "Withdrawal", "Bonus"])
        ca = c3.number_input("Amount", 0.0)
        if st.form_submit_button("Log Transaction"):
            final = -ca if ct=="Withdrawal" else ca
            pd.concat([df_cash, pd.DataFrame([[cd, cb, ct, final]], columns=df_cash.columns)]).to_csv(CASH_FILE, index=False)
            st.rerun()

    st.subheader("Live Balances")
    summary = []
    for b in meta["Bookies"]:
        if str(b) == 'nan': continue
        cash = df_cash[df_cash['Bookie'] == b]['Amount'].sum()
        profit = df_bets[df_bets['Bookie'] == b]['P/L'].sum()
        staked = df_bets[(df_bets['Bookie'] == b) & (df_bets['Status'] == "Pending")]['Stake'].sum()
        summary.append({"Bookie": b, "Net Deposits/Bonus": cash, "Profit": profit, "In Play": staked, "Current Balance": cash + profit - staked})
    st.table(pd.DataFrame(summary))

# --- 7. SETTINGS PAGE ---
elif nav == "⚙️ Settings":
    st.header("⚙️ Configuration")
    col1, col2 = st.columns(2)
    new_meta = {}
    for i, cat in enumerate(meta.keys()):
        with (col1 if i % 2 == 0 else col2):
            cur = [str(x) for x in meta[cat] if str(x) != 'nan']
            inp = st.text_area(f"Manage {cat}", value="\n".join(cur), height=150)
            new_meta[cat] = inp.split("\n")
    if st.button("Save Settings"):
        save_meta(new_meta)
        st.success("Updated!")
