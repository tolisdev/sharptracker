import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date

# --- 1. SETTINGS & AUTH ---
st.set_page_config(page_title="SharpTracker Pro", layout="wide", page_icon="🎯")

# Password logic: Checks Streamlit Cloud secrets first, then defaults to "admin"
# To set on Cloud: Add APP_PASSWORD = "yourpass" to the Secrets tab.
PASSWORD_SECRET = st.secrets.get("APP_PASSWORD", "admin")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login():
    st.title("🔐 SharpTracker Login")
    pwd_input = st.text_input("Enter Password", type="password")
    if st.button("Unlock System"):
        if pwd_input == PASSWORD_SECRET:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid Password")

if not st.session_state["authenticated"]:
    login()
    st.stop()

# --- 2. DATA FILES ---
DB_FILE = "bet_data.csv"
META_FILE = "meta_config.csv"

def load_bets():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    return pd.DataFrame(columns=["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L"])

def load_meta():
    if os.path.exists(META_FILE):
        return pd.read_csv(META_FILE).to_dict('list')
    return {
        "Sports": ["Football", "Basketball", "Tennis"],
        "Leagues": ["NFL", "NBA", "ATP", "UFC"],
        "Bookies": ["Pinnacle", "Bet365", "DraftKings"],
        "Types": ["Moneyline", "Spread", "Total", "Parlay"]
    }

def save_meta(m_dict):
    # Clean empty strings
    cleaned = {k: [str(x).strip() for x in v if str(x).strip() and str(x) != 'nan'] for k, v in m_dict.items()}
    pd.DataFrame.from_dict(cleaned, orient='index').transpose().to_csv(META_FILE, index=False)

# Initial Load
df_bets = load_bets()
meta = load_meta()

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.title("🎯 SharpTracker")
nav = st.sidebar.radio("Navigation", ["Dashboard", "Manage Bets", "Settings", "Tools"])

st.sidebar.divider()
if not df_bets.empty:
    net_profit = df_bets['P/L'].sum()
    st.sidebar.metric("Lifetime P/L", f"${net_profit:,.2f}", delta=f"{net_profit:,.2f}")

# --- 4. PAGE: SETTINGS (Configurable Lists) ---
if nav == "Settings":
    st.header("⚙️ System Configuration")
    st.write("Customize your dropdown menus here. Enter one item per line.")

    col1, col2 = st.columns(2)
    updated_meta = {}

    categories = list(meta.keys())
    for i, cat in enumerate(categories):
        with (col1 if i % 2 == 0 else col2):
            current_vals = [str(x) for x in meta[cat] if str(x) != 'nan']
            user_input = st.text_area(f"Edit {cat}", value="\n".join(current_vals), height=150)
            updated_meta[cat] = user_input.split("\n")

    if st.button("💾 Save All Configurations"):
        save_meta(updated_meta)
        st.success("Settings saved! Dropdowns in 'Manage Bets' are now updated.")
        st.rerun()

# --- 5. PAGE: MANAGE BETS (Add/Delete/Settle) ---
elif nav == "Manage Bets":
    st.header("📝 Manage Your Wagers")

    # --- SUB-SECTION: ADD NEW ---
    with st.expander("➕ Log a New Bet", expanded=False):
        with st.form("bet_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                f_date = st.date_input("Date", date.today())
                f_sport = st.selectbox("Sport", meta["Sports"])
                f_league = st.selectbox("League", meta["Leagues"])
            with c2:
                f_bookie = st.selectbox("Bookie", meta["Bookies"])
                f_type = st.selectbox("Type", meta["Types"])
                f_event = st.text_input("Event/Selection")
            with c3:
                f_odds = st.number_input("Odds", 1.01, 100.0, 1.91)
                f_stake = st.number_input("Stake ($)", 0.0, 50000.0, 10.0)
                f_stat = st.selectbox("Status", ["Pending", "Won", "Lost", "Push"])

            if st.form_submit_button("Record Bet"):
                # Calc P/L
                pl = 0.0
                if f_stat == "Won": pl = (f_stake * f_odds) - f_stake
                elif f_stat == "Lost": pl = -f_stake

                new_id = df_bets['id'].max() + 1 if not df_bets.empty else 1
                new_row = pd.DataFrame([[new_id, f_date, f_sport, f_league, f_bookie, f_type, f_event, f_odds, f_stake, f_stat, pl]], columns=df_bets.columns)
                df_bets = pd.concat([df_bets, new_row], ignore_index=True)
                df_bets.to_csv(DB_FILE, index=False)
                st.success("Bet Logged!")
                st.rerun()

    # --- SUB-SECTION: BULK SETTLE ---
    st.divider()
    pending = df_bets[df_bets['Status'] == "Pending"]
    if not pending.empty:
        st.subheader(f"🔔 Pending Settlements ({len(pending)})")
        for idx, row in pending.iterrows():
            with st.container(border=True):
                col_info, col_act = st.columns([4, 1])
                col_info.write(f"**{row['Event']}** | {row['Sport']} | ${row['Stake']} @ {row['Odds']}")
                new_res = col_act.selectbox("Result", ["Pending", "Won", "Lost", "Push"], key=f"set_{row['id']}")
                if new_res != "Pending":
                    # Update Logic
                    df_bets.at[idx, 'Status'] = new_res
                    if new_res == "Won": df_bets.at[idx, 'P/L'] = (row['Stake'] * row['Odds']) - row['Stake']
                    elif new_res == "Lost": df_bets.at[idx, 'P/L'] = -row['Stake']
                    else: df_bets.at[idx, 'P/L'] = 0.0
                    df_bets.to_csv(DB_FILE, index=False)
                    st.rerun()
    else:
        st.info("No pending bets to settle.")

    # --- SUB-SECTION: DELETE ---
    st.divider()
    st.subheader("🗑️ History & Deletion")
    if not df_bets.empty:
        for idx, row in df_bets.sort_values("Date", ascending=False).iterrows():
            with st.expander(f"{row['Date']} - {row['Event']} ({row['Status']})"):
                st.write(f"Bookie: {row['Bookie']} | P/L: ${row['P/L']:.2f}")
                if st.button("Delete This Bet", key=f"del_{row['id']}"):
                    df_bets = df_bets.drop(idx)
                    df_bets.to_csv(DB_FILE, index=False)
                    st.rerun()

# --- 6. PAGE: DASHBOARD (Analytics) ---
elif nav == "Dashboard":
    st.header("📊 Performance Dashboard")
    if df_bets.empty:
        st.warning("No data found. Log bets in 'Manage Bets' to see analytics.")
    else:
        # Filters
        c1, c2 = st.columns(2)
        f_sport = c1.multiselect("Filter by Sport", df_bets['Sport'].unique())
        f_bookie = c2.multiselect("Filter by Bookie", df_bets['Bookie'].unique())

        filtered = df_bets.copy()
        if f_sport: filtered = filtered[filtered['Sport'].isin(f_sport)]
        if f_bookie: filtered = filtered[filtered['Bookie'].isin(f_bookie)]

        # Stats
        st.divider()
        m1, m2, m3 = st.columns(3)
        total_p = filtered['P/L'].sum()
        roi = (total_p / filtered['Stake'].sum() * 100) if filtered['Stake'].sum() > 0 else 0
        m1.metric("Net Profit", f"${total_p:,.2f}")
        m2.metric("ROI", f"{roi:.2f}%")
        m3.metric("Win Rate", f"{(len(filtered[filtered['Status']=='Won'])/len(filtered[filtered['Status']!='Pending'])*100):.1f}%" if len(filtered[filtered['Status']!='Pending']) > 0 else "0%")

        # Charts
        st.plotly_chart(px.area(filtered.sort_values("Date"), x="Date", y="P/L", title="Profit Timeline").update_traces(line_color="green"), use_container_width=True)

        ca, cb = st.columns(2)
        ca.plotly_chart(px.bar(filtered.groupby("Sport")['P/L'].sum().reset_index(), x='Sport', y='P/L', color='Sport', title="Profit by Sport"))
        cb.plotly_chart(px.bar(filtered.groupby("Type")['P/L'].sum().reset_index(), x='Type', y='P/L', color='Type', title="Profit by Bet Type"))

# --- 7. PAGE: TOOLS (Kelly) ---
elif nav == "Tools":
    st.header("🧮 Betting Tools")
    st.subheader("Kelly Criterion Calculator")
    br = st.number_input("Current Bankroll", 0.0, 1000000.0, 1000.0)
    odds = st.number_input("Decimal Odds", 1.01, 50.0, 2.0)
    win_p = st.slider("Estimated Win Probability (%)", 0, 100, 50) / 100

    b = odds - 1
    k = (win_p * b - (1 - win_p)) / b if b > 0 else 0
    st.success(f"Recommended Stake: {max(0, k*100):.2f}%")
    st.info(f"Bet Amount: ${max(0, br * k):.2f}")
