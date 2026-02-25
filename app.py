import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="SharpTracker Pro", layout="wide", page_icon="🎯")
PASSWORD_SECRET = st.secrets.get("APP_PASSWORD", "admin")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 SharpTracker Login")
    if st.text_input("Password", type="password") == PASSWORD_SECRET:
        st.session_state["authenticated"] = True
        st.rerun()
    st.stop()

# --- 2. DATA FILES ---
DB_FILE = "bet_data.csv"
META_FILE = "meta_config.csv"
CASH_FILE = "cash_log.csv"  # New file for Deposits, Withdrawals, and Bonuses

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
    return {"Sports": ["Football"], "Leagues": ["NFL"], "Bookies": ["Pinnacle"], "Types": ["Spread"]}

# Initial Load
df_bets = load_data(DB_FILE, ["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L"])
df_cash = load_data(CASH_FILE, ["Date", "Bookie", "Type", "Amount"]) # Type: Deposit, Withdrawal, Bonus
meta = load_meta()

# --- 3. SIDEBAR ---
st.sidebar.title("🎯 SharpTracker")
nav = st.sidebar.radio("Navigation", ["Dashboard", "Manage Bets", "Bankroll", "Settings"])

if not df_bets.empty:
    risk = df_bets[df_bets['Status'] == "Pending"]['Stake'].sum()
    st.sidebar.metric("Money at Risk", f"${risk:,.2f}")
    st.sidebar.metric("Net Betting P/L", f"${df_bets['P/L'].sum():,.2f}")

# --- 4. PAGE: BANKROLL (NEW) ---
if nav == "Bankroll":
    st.header("💰 Bankroll Management")

    # --- TRANSACTION FORM ---
    with st.expander("💸 Add Transaction (Deposit, Withdrawal, Bonus)", expanded=True):
        with st.form("cash_form"):
            col1, col2, col3 = st.columns(3)
            t_date = col1.date_input("Date", date.today())
            t_bookie = col1.selectbox("Bookie", meta["Bookies"])
            t_type = col2.selectbox("Transaction Type", ["Deposit", "Withdrawal", "Bonus"])
            t_amt = col3.number_input("Amount ($)", min_value=0.0, step=10.0)

            if st.form_submit_button("Log Transaction"):
                # Withdrawals are stored as negative numbers for easy summing
                final_amt = -t_amt if t_type == "Withdrawal" else t_amt
                new_cash = pd.DataFrame([[t_date, t_bookie, t_type, final_amt]], columns=df_cash.columns)
                pd.concat([df_cash, new_cash]).to_csv(CASH_FILE, index=False)
                st.success("Transaction recorded!")
                st.rerun()

    # --- BOOKIE SUMMARY TABLE ---
    st.subheader("🏦 Current Balances per Bookie")
    bookie_stats = []
    for b in [x for x in meta["Bookies"] if str(x) != 'nan']:
        # Cash movements (Deposits + Bonuses - Withdrawals)
        cash_flow = df_cash[df_cash['Bookie'] == b]['Amount'].sum()
        # Betting P/L
        bet_pl = df_bets[df_bets['Bookie'] == b]['P/L'].sum()
        # Active Stakes (subtracting from available balance)
        active_stakes = df_bets[(df_bets['Bookie'] == b) & (df_bets['Status'] == "Pending")]['Stake'].sum()

        current_bal = cash_flow + bet_pl - active_stakes
        bookie_stats.append({"Bookie": b, "Cash In/Out": cash_flow, "Betting P/L": bet_pl, "Pending": active_stakes, "Available Balance": current_bal})

    if bookie_stats:
        st.table(pd.DataFrame(bookie_stats))

    st.subheader("📜 Cash History")
    st.dataframe(df_cash.sort_values("Date", ascending=False), use_container_width=True)

# --- 5. PAGE: DASHBOARD ---
elif nav == "Dashboard":
    st.header("📊 Analytics")
    # Adding League Filter as requested previously
    f_league = st.multiselect("Filter by League", df_bets['League'].unique())
    dff = df_bets.copy()
    if f_league: dff = dff[dff['League'].isin(f_league)]

    if not dff.empty:
        st.plotly_chart(px.line(dff.sort_values("Date"), x="Date", y="P/L", title="Profit Curve"), use_container_width=True)
        st.dataframe(dff, use_container_width=True)

# --- 6. PAGE: MANAGE BETS ---
elif nav == "Manage Bets":
    st.header("📝 Wagers")
    # (Same form/settle logic as before)
    with st.expander("Log New Bet"):
        with st.form("b_form"):
            c1, c2, c3 = st.columns(3)
            # Form fields...
            if st.form_submit_button("Add"):
                # Save logic...
                pass
    # ... Bulk settle logic ...

# --- 7. PAGE: SETTINGS ---
elif nav == "Settings":
    st.header("⚙️ Settings")
    # Simple list management for Sports, Leagues, Bookies, Types
    for cat in meta.keys():
        vals = [str(x) for x in meta[cat] if str(x) != 'nan']
        new_vals = st.text_area(f"Edit {cat}", value="\n".join(vals))
        meta[cat] = new_vals.split("\n")
    if st.button("Save Settings"):
        pd.DataFrame.from_dict(meta, orient='index').transpose().to_csv(META_FILE, index=False)
        st.rerun()
