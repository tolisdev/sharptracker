import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

# --- 1. CONFIG & UI STYLING ---
st.set_page_config(page_title="SharpTracker Elite", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; color: #00ffc8; }
    .stButton>button { border-radius: 8px; height: 3em; width: 100%; font-weight: 600; }
    .stExpander { border: 1px solid #30333d; border-radius: 10px; background-color: #161b22; }
    .streak-container { padding: 10px; border-radius: 5px; text-align: center; background: #1e2129; border: 1px solid #30333d; }
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

# --- 3. SESSION STATE & CLOUD ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0
if "last_sync" not in st.session_state:
    st.session_state.last_sync = "Never"

# Initial Fetch
if "bets_df" not in st.session_state:
    try:
        st.session_state.bets_df = conn.read(worksheet="Bets", ttl="0s")
        st.session_state.cash_df = conn.read(worksheet="Cash", ttl="0s")
        st.session_state.meta_df = conn.read(worksheet="Meta", ttl="0s")
        st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")

        if not st.session_state.bets_df.empty:
            st.session_state.bets_df['id'] = pd.to_numeric(st.session_state.bets_df['id'])
            st.session_state.bets_df['Date'] = pd.to_datetime(st.session_state.bets_df['Date']).dt.date
        if not st.session_state.cash_df.empty:
            st.session_state.cash_df['Date'] = pd.to_datetime(st.session_state.cash_df['Date']).dt.date

    except Exception as e:
        st.error(f"Cloud Connection Failed. Check Secrets. Error: {e}")
        st.stop()

df_bets = st.session_state.bets_df
df_cash = st.session_state.cash_df
df_meta = st.session_state.meta_df

# --- 4. STREAK LOGIC ---
def get_streak(df):
    if df.empty: return "N/A", "#ffffff"
    # Sort by date and id to get the exact sequence
    sorted_df = df.sort_values(['Date', 'id'], ascending=[False, False])
    results = sorted_df[sorted_df['Status'].isin(['Won', 'Lost'])]['Status'].tolist()

    if not results: return "No graded bets", "#777777"

    current_status = results[0]
    count = 0
    for res in results:
        if res == current_status:
            count += 1
        else:
            break

    color = "#00ffc8" if current_status == "Won" else "#ff4b4b"
    return f"{count} {current_status}", color

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("SharpTracker Elite")
    st.caption(f"Last Sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        st.warning(f"⚠️ {st.session_state.unsaved_count} Unsaved Changes")
        if st.button("💾 PUSH TO CLOUD", type="primary"):
            conn.update(worksheet="Bets", data=st.session_state.bets_df)
            conn.update(worksheet="Cash", data=st.session_state.cash_df)
            conn.update(worksheet="Meta", data=st.session_state.meta_df)
            st.session_state.unsaved_count = 0
            st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
            st.rerun()
    else:
        st.success("✅ Cloud Synced")
        if st.button("🔄 Refresh Data"):
            for key in ["bets_df", "cash_df", "meta_df", "unsaved_count"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    st.divider()
    nav = st.radio("MENU", ["📊 Analytics", "📝 Wagers", "💰 Bankroll", "⚙️ Config"])

# --- 6. ANALYTICS (STREAK ADDED) ---
if nav == "📊 Analytics":
    st.title("📊 Performance Intelligence")
    if df_bets.empty:
        st.info("Log wagers to see analytics.")
    else:
        p_val = pd.to_numeric(df_bets['P/L']).sum()
        r_val = df_bets[df_bets['Status'] == "Pending"]['Stake'].sum()
        streak_text, streak_color = get_streak(df_bets)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net P/L", f"${p_val:,.2f}")
        m2.metric("Total Risk", f"${r_val:,.2f}")
        m3.metric("Total Wagers", len(df_bets))

        # Streak Visual
        with m4:
            st.markdown(f"**Current Streak**")
            st.markdown(f"<div class='streak-container'><h2 style='color:{streak_color};margin:0;'>{streak_text}</h2></div>", unsafe_allow_html=True)

        st.divider()
        dff_s = df_bets.sort_values("Date")
        dff_s['Cum'] = dff_s['P/L'].cumsum()
        st.plotly_chart(px.area(dff_s, x="Date", y="Cum", title="Session Profit Growth", template="plotly_dark", color_discrete_sequence=['#00ffc8']), use_container_width=True)

# --- 7. WAGERS PAGE ---
elif nav == "📝 Wagers":
    st.title("📝 Wager Management")
    tab_new, tab_open, tab_hist = st.tabs(["➕ Add New Bet", "🔔 Pending Bets", "📚 Session History"])

    with tab_new:
        with st.form("new_wager_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            s_list = df_meta["Sports"].dropna().tolist() if "Sports" in df_meta.columns else []
            l_list = df_meta["Leagues"].dropna().tolist() if "Leagues" in df_meta.columns else []
            b_list = df_meta["Bookies"].dropna().tolist() if "Bookies" in df_meta.columns else []
            t_list = df_meta["Types"].dropna().tolist() if "Types" in df_meta.columns else []

            d_i = col1.date_input("Date", date.today())
            s_i = col1.selectbox("Sport", s_list)
            l_i = col1.selectbox("League", l_list)
            b_i = col2.selectbox("Bookie", b_list)
            t_i = col2.selectbox("Bet Type", t_list)
            e_i = col2.text_input("Selection/Event")
            o_i = col3.number_input("Odds", 1.01, 500.0, 1.91)
            st_i = col3.number_input("Stake", 1.0, 50000.0, 10.0)
            res_i = col3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("Save to Local Session"):
                pl = (st_i * o_i - st_i) if res_i == "Won" else (-st_i if res_i == "Lost" else 0.0)
                new_id = int(df_bets['id'].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame([[new_id, d_i, s_i, l_i, b_i, t_i, e_i, o_i, st_i, res_i, pl, 0.0]], columns=df_bets.columns)
                st.session_state.bets_df = pd.concat([df_bets, new_row], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.rerun()

    with tab_open:
        pending = df_bets[df_bets['Status'] == "Pending"]
        if pending.empty:
            st.success("No open bets!")
        else:
            for idx, row in pending.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"**{row['Event']}** | {row['Bookie']} | ${row['Stake']}")
                    res = c2.selectbox("Set Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"p_{row['id']}")
                    if res != "Pending":
                        co_val = st.number_input("Payout", key=f"co_{row['id']}") if res == "Cashed Out" else 0.0
                        if st.button("Confirm Result", key=f"btn_{row['id']}"):
                            st.session_state.bets_df.at[idx, 'Status'] = res
                            st.session_state.bets_df.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake']) if res=="Won" else (-row['Stake'] if res=="Lost" else co_val-row['Stake'])
                            st.session_state.unsaved_count += 1
                            st.rerun()

    with tab_hist:
        for idx, row in df_bets.sort_values("Date", ascending=False).iterrows():
            with st.expander(f"{row['Date']} | {row['Event']} | {row['Status']}"):
                col_info, col_del = st.columns([5, 1])
                col_info.write(f"**Bookie:** {row['Bookie']} | **Odds:** {row['Odds']} | **Stake:** ${row['Stake']} | **P/L:** ${row['P/L']}")
                if col_del.button("❌ Delete", key=f"del_{row['id']}"):
                    st.session_state.bets_df = st.session_state.bets_df.drop(idx)
                    st.session_state.unsaved_count += 1
                    st.rerun()

# --- 8. BANKROLL & CONFIG (Remains Expanded) ---
elif nav == "💰 Bankroll":
    st.title("💰 Bankroll Tracking")
    with st.form("cash_log"):
        c1, c2, c3 = st.columns(3)
        cb = c1.selectbox("Source", df_meta["Bookies"].dropna().tolist() if not df_meta.empty else [])
        ct = c2.selectbox("Type", ["Deposit", "Withdrawal", "Bonus"])
        ca = c3.number_input("Amount", 0.0)
        if st.form_submit_button("Record Move"):
            val = -ca if ct == "Withdrawal" else ca
            new_c = pd.DataFrame([[date.today(), cb, ct, val]], columns=df_cash.columns)
            st.session_state.cash_df = pd.concat([df_cash, new_c], ignore_index=True)
            st.session_state.unsaved_count += 1
            st.rerun()
    st.dataframe(st.session_state.cash_df.sort_values("Date", ascending=False), use_container_width=True)

elif nav == "⚙️ Config":
    st.title("⚙️ Global Settings")
    c1, c2, c3, c4 = st.columns(4)
    with c1: s_text = st.text_area("Sports", "\n".join([str(x) for x in df_meta["Sports"].dropna().tolist()]), height=300)
    with c2: l_text = st.text_area("Leagues", "\n".join([str(x) for x in df_meta["Leagues"].dropna().tolist()]), height=300)
    with c3: b_text = st.text_area("Bookies", "\n".join([str(x) for x in df_meta["Bookies"].dropna().tolist()]), height=300)
    with c4: t_text = st.text_area("Types", "\n".join([str(x) for x in df_meta["Types"].dropna().tolist()]), height=300)
    if st.button("Apply Config to Session"):
        new_data = {
            "Sports": [x.strip() for x in s_text.split("\n") if x.strip()],
            "Leagues": [x.strip() for x in l_text.split("\n") if x.strip()],
            "Bookies": [x.strip() for x in b_text.split("\n") if x.strip()],
            "Types": [x.strip() for x in t_text.split("\n") if x.strip()],
        }
        st.session_state.meta_df = pd.DataFrame.from_dict(new_data, orient='index').transpose()
        st.session_state.unsaved_count += 1
        st.success("Config updated locally!")
