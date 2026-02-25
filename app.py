import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date

# --- CONFIG ---
st.set_page_config(page_title="SharpTracker Solo", layout="wide", page_icon="🎯")
DB_FILE = "bets.csv"
APP_PASSWORD = "admin"  # Change this for deployment!

# --- DATA HELPERS ---
def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Ensure proper types
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        df['Odds'] = df['Odds'].astype(float)
        df['Stake'] = df['Stake'].astype(float)
        df['P/L'] = df['P/L'].astype(float)
        return df
    return pd.DataFrame(columns=["Date", "Sport", "Event", "Odds", "Stake", "Status", "P/L"])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

def calculate_pl(row):
    if row['Status'] == "Won": return (row['Stake'] * row['Odds']) - row['Stake']
    if row['Status'] == "Lost": return -row['Stake']
    return 0.0

# --- AUTH ---
if "auth" not in st.session_state: st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.title("🔒 SharpTracker Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Enter"):
        if pwd == APP_PASSWORD:
            st.session_state["auth"] = True
            st.rerun()
        else: st.error("Wrong password")
    st.stop()

# --- MAIN APP ---
df = load_data()
st.sidebar.title("🎯 SharpTracker")
page = st.sidebar.radio("Menu", ["Dashboard", "Log Bet", "Kelly Calc"])

if page == "Dashboard":
    st.header("📊 Performance Dashboard")

    # 1. Metrics
    if not df.empty:
        total_pl = df['P/L'].sum()
        roi = (total_pl / df['Stake'].sum() * 100) if df['Stake'].sum() > 0 else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Net Profit", f"${total_pl:,.2f}")
        c2.metric("ROI", f"{roi:.2f}%")
        c3.metric("Pending Bets", len(df[df['Status'] == "Pending"]))

        # 2. Bulk Settle Feature
        pending = df[df['Status'] == "Pending"]
        if not pending.empty:
            with st.expander("🔔 Settle Pending Bets", expanded=True):
                st.write("Update the result for your open wagers:")
                for idx, row in pending.iterrows():
                    col_info, col_res = st.columns([3, 1])
                    col_info.write(f"**{row['Date']}** | {row['Sport']}: {row['Event']} (${row['Stake']} @ {row['Odds']})")
                    new_stat = col_res.selectbox("Result", ["Pending", "Won", "Lost", "Push"], key=f"settle_{idx}")

                    if new_stat != "Pending":
                        df.at[idx, 'Status'] = new_stat
                        df.at[idx, 'P/L'] = calculate_pl(df.iloc[idx])
                        save_data(df)
                        st.rerun()

        # 3. Chart
        df_sorted = df.sort_values("Date")
        df_sorted['Cumulative'] = df_sorted['P/L'].cumsum()
        st.plotly_chart(px.line(df_sorted, x="Date", y="Cumulative", title="Bankroll Growth"), use_container_width=True)

        # 4. History
        st.subheader("History")
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)

elif page == "Log Bet":
    st.header("📝 New Wager")
    with st.form("add_bet"):
        c1, c2 = st.columns(2)
        d = c1.date_input("Date", date.today())
        s = c1.selectbox("Sport", ["NFL", "NBA", "MLB", "Soccer", "UFC", "Other"])
        e = c1.text_input("Event")
        o = c2.number_input("Odds", 1.01, 100.0, 1.91)
        stk = c2.number_input("Stake", 0.0, 10000.0, 10.0)
        stat = c2.selectbox("Status", ["Pending", "Won", "Lost", "Push"])

        if st.form_submit_button("Log"):
            pl = (stk * o - stk) if stat == "Won" else (-stk if stat == "Lost" else 0)
            new_row = pd.DataFrame([[d, s, e, o, stk, stat, pl]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("Bet logged!")

elif page == "Kelly Calc":
    st.header("🧮 Kelly Criterion")
    br = st.number_input("Bankroll", value=1000.0)
    p = st.slider("Win Prob %", 0, 100, 55) / 100
    b = st.number_input("Odds", value=2.0) - 1
    k = (p * b - (1 - p)) / b if b > 0 else 0
    st.metric("Suggested Bet", f"${max(0, br * k):,.2f}", f"{k*100:.1f}% of Bankroll")
