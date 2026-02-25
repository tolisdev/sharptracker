import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="SharpTracker Elite", layout="wide", page_icon="📈")

# Custom CSS for a more "Dashboard" look
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; }
    .stButton>button { border-radius: 8px; height: 3em; width: 100%; transition: 0.3s; }
    .stExpander { border: 1px solid #30333d; border-radius: 10px; }
    .status-card { padding: 20px; border-radius: 10px; background-color: #1e2129; border-left: 5px solid #00ffc8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 SharpTracker Elite")
    with st.container(border=True):
        pwd_input = st.text_input("Enter Access Key", type="password")
        if st.button("Unlock System"):
            if pwd_input == st.secrets.get("APP_PASSWORD", "admin"):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid Access Key")
    st.stop()

# --- 3. CORE DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0
if "last_sync" not in st.session_state:
    st.session_state.last_sync = "Never"

# Initial Load
if "bets_df" not in st.session_state:
    try:
        st.session_state.bets_df = conn.read(worksheet="Bets", ttl="0s")
        st.session_state.cash_df = conn.read(worksheet="Cash", ttl="0s")
        st.session_state.meta_df = conn.read(worksheet="Meta", ttl="0s")
        st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
        for key in ['bets_df', 'cash_df']:
            if not st.session_state[key].empty and 'Date' in st.session_state[key].columns:
                st.session_state[key]['Date'] = pd.to_datetime(st.session_state[key]['Date']).dt.date
    except Exception as e:
        st.error(f"Cloud Connection Failed. Check Secrets. Error: {e}")
        st.stop()

df_bets = st.session_state.bets_df
df_cash = st.session_state.cash_df
df_meta = st.session_state.meta_df

# --- 4. SIDEBAR & NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2620/2620958.png", width=80)
    st.title("SharpTracker Elite")
    st.caption(f"Last Cloud Sync: {st.session_state.last_sync}")

    # Sync Status Card
    if st.session_state.unsaved_count > 0:
        with st.container(border=True):
            st.warning(f"**{st.session_state.unsaved_count} Unsaved Changes**")
            if st.button("💾 PUSH TO CLOUD", type="primary"):
                conn.update(worksheet="Bets", data=st.session_state.bets_df)
                conn.update(worksheet="Cash", data=st.session_state.cash_df)
                conn.update(worksheet="Meta", data=st.session_state.meta_df)
                st.session_state.unsaved_count = 0
                st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
                st.success("Cloud Updated!")
                st.rerun()
    else:
        st.success("✅ Cloud Synchronized")
        if st.button("🔄 Pull Fresh Data"):
            for key in ["bets_df", "cash_df", "meta_df", "unsaved_count"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    st.divider()
    nav = st.radio("MAIN MENU", ["📊 Analytics", "📝 Wagers", "💰 Bankroll", "⚙️ Config"], label_visibility="collapsed")

# --- 5. ANALYTICS PAGE ---
if nav == "📊 Analytics":
    st.title("📊 Performance Intelligence")

    if df_bets.empty:
        st.info("Start your session by logging bets in the Wagers tab.")
    else:
        # KPI Bar
        p_val = pd.to_numeric(df_bets['P/L']).sum()
        r_val = df_bets[df_bets['Status'] == "Pending"]['Stake'].sum()
        roi = (p_val / df_bets['Stake'].sum() * 100) if df_bets['Stake'].sum() > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net Profit", f"${p_val:,.2f}", delta=f"{roi:.1f}% ROI")
        m2.metric("Exposure", f"${r_val:,.2f}")
        m3.metric("Win Rate", f"{(len(df_bets[df_bets['Status']=='Won'])/len(df_bets[df_bets['Status'].isin(['Won','Lost'])])*100 if not df_bets[df_bets['Status'].isin(['Won','Lost'])].empty else 0):.1f}%")
        m4.metric("Avg Odds", f"{df_bets['Odds'].mean():.2f}")

        # Main Performance Graph
        st.divider()
        dff_s = df_bets.sort_values("Date")
        dff_s['Cum'] = dff_s['P/L'].cumsum()
        fig = px.area(dff_s, x="Date", y="Cum", title="Equity Curve (Session Data)",
                      template="plotly_dark", color_discrete_sequence=['#00ffc8'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # Insights Row
        c_left, c_right = st.columns(2)
        with c_left:
            st.plotly_chart(px.bar(df_bets.groupby("Sport")['P/L'].sum().reset_index(),
                                   x='Sport', y='P/L', title="Profit by Category", color='Sport'), use_container_width=True)
        with c_right:
            st.plotly_chart(px.pie(df_bets, values='Stake', names='Bookie', hole=.4, title="Bankroll Distribution"), use_container_width=True)

# --- 6. WAGERS PAGE ---
elif nav == "📝 Wagers":
    st.title("📝 Wager Management")

    tab_new, tab_open, tab_hist = st.tabs(["➕ Add Bet", "🔔 Pending", "📚 History"])

    with tab_new:
        with st.form("new_wager", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            # Safe lists
            s_list = df_meta["Sports"].dropna().tolist() if "Sports" in df_meta.columns else []
            l_list = df_meta["Leagues"].dropna().tolist() if "Leagues" in df_meta.columns else []
            b_list = df_meta["Bookies"].dropna().tolist() if "Bookies" in df_meta.columns else []

            d_i = col1.date_input("Date", date.today())
            s_i = col1.selectbox("Sport", s_list)
            l_i = col2.selectbox("League", l_list)
            b_i = col2.selectbox("Bookie", b_list)
            e_i = col1.text_input("Event Selection")
            o_i = col3.number_input("Odds", 1.01, 500.0, 1.91)
            st_i = col3.number_input("Stake", 1.0, 50000.0, 10.0)
            res_i = col3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("Log To Local Session"):
                pl = (st_i * o_i - st_i) if res_i == "Won" else (-st_i if res_i == "Lost" else 0.0)
                new_id = int(df_bets['id'].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame([[new_id, d_i, s_i, l_i, b_i, "ML", e_i, o_i, st_i, res_i, pl, 0.0]],
                                       columns=["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"])
                st.session_state.bets_df = pd.concat([df_bets, new_row], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.toast("Bet Added to Session")
                st.rerun()

    with tab_open:
        pending = df_bets[df_bets['Status'] == "Pending"]
        if pending.empty:
            st.success("All bets settled! No open risk.")
        else:
            for idx, row in pending.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    c1.write(f"**{row['Event']}** ({row['League']})")
                    c2.write(f"Stake: ${row['Stake']} @ {row['Odds']}")
                    res_choice = c3.selectbox("Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"p_{row['id']}")

                    if res_choice != "Pending":
                        co_val = 0.0
                        if res_choice == "Cashed Out":
                            co_val = st.number_input("Payout", key=f"co_{row['id']}")

                        if st.button("Set Result", key=f"btn_{row['id']}"):
                            st.session_state.bets_df.at[idx, 'Status'] = res_choice
                            if res_choice == "Won": st.session_state.bets_df.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake'])
                            elif res_choice == "Lost": st.session_state.bets_df.at[idx, 'P/L'] = -row['Stake']
                            elif res_choice == "Cashed Out":
                                st.session_state.bets_df.at[idx, 'P/L'] = co_val - row['Stake']
                                st.session_state.bets_df.at[idx, 'Cashout_Amt'] = co_val
                            st.session_state.unsaved_count += 1
                            st.rerun()

    with tab_hist:
        st.dataframe(df_bets.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)

# --- 7. BANKROLL PAGE ---
elif nav == "💰 Bankroll":
    st.title("💰 Cash Flow Control")
    with st.container(border=True):
        with st.form("cash_log"):
            c1, c2, c3 = st.columns(3)
            cb = c1.selectbox("Bookie", df_meta["Bookies"].dropna().tolist() if not df_meta.empty else [])
            ct = c2.selectbox("Type", ["Deposit", "Withdrawal", "Bonus"])
            ca = c3.number_input("Amount", 0.0)
            if st.form_submit_button("Record Cash Move"):
                val = -ca if ct == "Withdrawal" else ca
                new_c = pd.DataFrame([[date.today(), cb, ct, val]], columns=["Date", "Bookie", "Type", "Amount"])
                st.session_state.cash_df = pd.concat([st.session_state.cash_df, new_c], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.rerun()

    # Balance Table
    st.subheader("Cloud Balance Summary")
    summary = []
    for b in [x for x in df_meta["Bookies"].dropna().tolist()]:
        c_flow = df_cash[df_cash['Bookie'] == b]['Amount'].sum()
        p_flow = df_bets[df_bets['Bookie'] == b]['P/L'].sum()
        risk = df_bets[(df_bets['Bookie'] == b) & (df_bets['Status'] == "Pending")]['Stake'].sum()
        summary.append({"Bookie": b, "Net Cash": f"${c_flow:,.2f}", "Profit": f"${p_flow:,.2f}", "Current Balance": f"${c_flow+p_flow-risk:,.2f}"})
    st.table(pd.DataFrame(summary))

# --- 8. CONFIG PAGE ---
elif nav == "⚙️ Config":
    st.title("⚙️ Global Settings")
    st.info("Edit your dropdown lists below. Remember to push to cloud to save permanently.")
    new_m = {}
    cols = st.columns(len(df_meta.columns))
    for i, cat in enumerate(df_meta.columns):
        with cols[i]:
            cur = [str(x) for x in df_meta[cat].dropna().tolist()]
            inp = st.text_area(f"Manage {cat}", value="\n".join(cur), height=300)
            new_m[cat] = inp.split("\n")

    if st.button("Apply Config Changes"):
        st.session_state.meta_df = pd.DataFrame.from_dict(new_m, orient='index').transpose()
        st.session_state.unsaved_count += 1
        st.success("New configuration applied to current session!")
