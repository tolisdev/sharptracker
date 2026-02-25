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

# --- 3. CORE DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0
if "last_sync" not in st.session_state:
    st.session_state.last_sync = "Never"

# INITIAL FETCH
if "bets_df" not in st.session_state:
    try:
        b_df = conn.read(worksheet="Bets", ttl="0s")
        c_df = conn.read(worksheet="Cash", ttl="0s")
        m_df = conn.read(worksheet="Meta", ttl="0s")

        # SELF-HEALING: Ensure all required columns exist
        bet_cols = ["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"]
        for col in bet_cols:
            if col not in b_df.columns: b_df[col] = 0 if col in ["id", "Odds", "Stake", "P/L", "Cashout_Amt"] else ""

        meta_cols = ["Sports", "Leagues", "Bookies", "Types"]
        for col in meta_cols:
            if col not in m_df.columns: m_df[col] = ""

        st.session_state.bets_df = b_df
        st.session_state.cash_df = c_df
        st.session_state.meta_df = m_df
        st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")

        # Clean Data Types
        if not st.session_state.bets_df.empty:
            st.session_state.bets_df['Date'] = pd.to_datetime(st.session_state.bets_df['Date']).dt.date
    except Exception as e:
        st.error(f"Cloud Connection Failed. Check Secrets. Error: {e}")
        st.stop()

df_bets = st.session_state.bets_df
df_cash = st.session_state.cash_df
df_meta = st.session_state.meta_df

# --- 4. ANALYTICS LOGIC ---
def get_streak(df):
    if df.empty: return "N/A", "#777777"
    graded = df[df['Status'].isin(['Won', 'Lost'])].sort_values(['Date', 'id'], ascending=False)
    if graded.empty: return "0-0", "#777777"
    results = graded['Status'].tolist()
    curr = results[0]
    count = 0
    for r in results:
        if r == curr: count += 1
        else: break
    return f"{count} {curr}", ("#00ffc8" if curr == "Won" else "#ff4b4b")

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
        if st.button("🔄 Pull Fresh Data"):
            for key in ["bets_df", "cash_df", "meta_df", "unsaved_count"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    st.divider()
    nav = st.radio("MENU", ["📊 Analytics", "📝 Wagers", "💰 Bankroll", "⚙️ Config"])

# --- 6. ANALYTICS ---
if nav == "📊 Analytics":
    st.title("📊 Performance Intelligence")
    if df_bets.empty:
        st.info("Log wagers to see analytics.")
    else:
        p_val = pd.to_numeric(df_bets['P/L']).sum()
        r_val = pd.to_numeric(df_bets[df_bets['Status'] == "Pending"]['Stake']).sum()
        s_text, s_color = get_streak(df_bets)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net Profit", f"${p_val:,.2f}")
        m2.metric("Exposure", f"${r_val:,.2f}")
        m3.metric("Total Bets", len(df_bets))
        with m4:
            st.markdown(f"**Current Streak**")
            st.markdown(f"<div class='streak-container'><h2 style='color:{s_color};margin:0;'>{s_text}</h2></div>", unsafe_allow_html=True)

        dff_s = df_bets.sort_values("Date")
        dff_s['Cum'] = dff_s['P/L'].cumsum()
        st.plotly_chart(px.area(dff_s, x="Date", y="Cum", title="Profit Curve", template="plotly_dark", color_discrete_sequence=['#00ffc8']), use_container_width=True)

# --- 7. WAGERS PAGE ---
elif nav == "📝 Wagers":
    st.title("📝 Wager Management")
    t_add, t_pend, t_hist = st.tabs(["➕ Add New", "🔔 Pending", "📚 History"])

    with t_add:
        with st.form("new_w_f", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            # Fetch lists safely
            s_l = df_meta["Sports"].dropna().tolist() if "Sports" in df_meta.columns else []
            l_l = df_meta["Leagues"].dropna().tolist() if "Leagues" in df_meta.columns else []
            b_l = df_meta["Bookies"].dropna().tolist() if "Bookies" in df_meta.columns else []
            t_l = df_meta["Types"].dropna().tolist() if "Types" in df_meta.columns else []

            d_i = c1.date_input("Date", date.today())
            s_i = c1.selectbox("Sport", s_l)
            l_i = c1.selectbox("League", l_l)
            b_i = c2.selectbox("Bookie", b_l)
            t_i = c2.selectbox("Type", t_l)
            e_i = c2.text_input("Selection")
            o_i = c3.number_input("Odds", 1.01, 500.0, 1.91)
            st_i = c3.number_input("Stake", 1.0, 50000.0, 10.0)
            res_i = c3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("Add Locally"):
                pl = (st_i * o_i - st_i) if res_i == "Won" else (-st_i if res_i == "Lost" else 0.0)
                nid = int(df_bets['id'].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame([[nid, d_i, s_i, l_i, b_i, t_i, e_i, o_i, st_i, res_i, pl, 0.0]], columns=df_bets.columns)
                st.session_state.bets_df = pd.concat([df_bets, new_row], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.rerun()

    with t_pend:
        pending = df_bets[df_bets['Status'] == "Pending"]
        for idx, row in pending.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{row['Event']}** | ${row['Stake']}")
                res = c2.selectbox("Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"r_{row['id']}")
                if res != "Pending":
                    co = st.number_input("Payout", key=f"c_{row['id']}") if res == "Cashed Out" else 0.0
                    if st.button("Set Result", key=f"b_{row['id']}"):
                        st.session_state.bets_df.at[idx, 'Status'] = res
                        st.session_state.bets_df.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake']) if res=="Won" else (-row['Stake'] if res=="Lost" else co-row['Stake'])
                        st.session_state.unsaved_count += 1
                        st.rerun()

    with t_hist:
        for idx, row in df_bets.sort_values("Date", ascending=False).iterrows():
            with st.expander(f"{row['Date']} | {row['Event']} ({row['Status']})"):
                c1, c2 = st.columns([5, 1])
                c1.write(f"**Bookie:** {row['Bookie']} | **Odds:** {row['Odds']} | **P/L:** ${row['P/L']}")
                if c2.button("❌ Delete", key=f"d_{row['id']}"):
                    st.session_state.bets_df = df_bets.drop(idx)
                    st.session_state.unsaved_count += 1
                    st.rerun()

# --- 8. BANKROLL & CONFIG ---
elif nav == "💰 Bankroll":
    st.title("💰 Cash Management")
    with st.form("cash_log"):
        c1, c2, c3 = st.columns(3)
        cb = c1.selectbox("Bookie", df_meta["Bookies"].dropna().tolist() if "Bookies" in df_meta.columns else [])
        ct = c2.selectbox("Type", ["Deposit", "Withdrawal", "Bonus"])
        ca = c3.number_input("Amount", 0.0)
        if st.form_submit_button("Record"):
            val = -ca if ct == "Withdrawal" else ca
            new_c = pd.DataFrame([[date.today(), cb, ct, val]], columns=["Date", "Bookie", "Type", "Amount"])
            st.session_state.cash_df = pd.concat([st.session_state.cash_df, new_c], ignore_index=True)
            st.session_state.unsaved_count += 1
            st.rerun()
    st.dataframe(st.session_state.cash_df, use_container_width=True)

elif nav == "⚙️ Config":
    st.title("⚙️ Global Settings")
    c1, c2, c3, c4 = st.columns(4)
    # Check for column existence before drawing text areas
    s_val = "\n".join([str(x) for x in df_meta["Sports"].dropna().tolist()]) if "Sports" in df_meta.columns else ""
    l_val = "\n".join([str(x) for x in df_meta["Leagues"].dropna().tolist()]) if "Leagues" in df_meta.columns else ""
    b_val = "\n".join([str(x) for x in df_meta["Bookies"].dropna().tolist()]) if "Bookies" in df_meta.columns else ""
    t_val = "\n".join([str(x) for x in df_meta["Types"].dropna().tolist()]) if "Types" in df_meta.columns else ""

    with c1: s_txt = st.text_area("Sports", s_val, height=300)
    with c2: l_txt = st.text_area("Leagues", l_val, height=300)
    with c3: b_txt = st.text_area("Bookies", b_val, height=300)
    with c4: t_txt = st.text_area("Types", t_val, height=300)

    if st.button("Update Session Config"):
        new_meta = {
            "Sports": [x.strip() for x in s_txt.split("\n") if x.strip()],
            "Leagues": [x.strip() for x in l_txt.split("\n") if x.strip()],
            "Bookies": [x.strip() for x in b_txt.split("\n") if x.strip()],
            "Types": [x.strip() for x in t_txt.split("\n") if x.strip()]
        }
        st.session_state.meta_df = pd.DataFrame.from_dict(new_meta, orient='index').transpose()
        st.session_state.unsaved_count += 1
        st.success("Config updated locally! Push to cloud to save.")
