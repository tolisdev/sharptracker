import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

# --- 1. SETTINGS & LUXE UI STYLING ---
st.set_page_config(page_title="SharpTracker Elite", layout="wide", page_icon="📈")

# Professional Studio Styling
st.markdown("""
    <style>
    /* Metric Card Styling */
    [data-testid="stMetricValue"] { font-size: 32px; font-weight: 800; color: #00ffc8; letter-spacing: -1px; }
    [data-testid="stMetricDelta"] { font-size: 16px; }

    /* Global Background & Cards */
    .main { background-color: #0d1117; }
    div[data-testid="stVerticalBlock"] > div:has(div.stMetric) {
        background-color: #161b22;
        border: 1px solid #30333d;
        padding: 15px;
        border-radius: 12px;
    }

    /* Sidebar Branding */
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        left: 20px;
        font-size: 12px;
        color: #8b949e;
        letter-spacing: 1px;
    }

    /* Custom Buttons */
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30333d;
        transition: 0.3s;
    }
    .stButton>button:hover {
        border-color: #00ffc8;
        color: #00ffc8;
    }

    /* Streak Banner */
    .streak-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30333d;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("📈 SharpTracker Elite")
    with st.container(border=True):
        pwd_input = st.text_input("System Access Key", type="password")
        if st.button("Initialize System"):
            if pwd_input == st.secrets.get("APP_PASSWORD", "admin"):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Access Denied")
    st.stop()

# --- 3. CORE DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0

if "bets_df" not in st.session_state:
    try:
        b_df = conn.read(worksheet="Bets", ttl="0s")
        c_df = conn.read(worksheet="Cash", ttl="0s")
        m_df = conn.read(worksheet="Meta", ttl="0s")

        # Self-Healing Logic
        REQUIRED = {"Bets": ["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"],
                    "Meta": ["Sports", "Leagues", "Bookies", "Types"]}
        for col in REQUIRED["Bets"]:
            if col not in b_df.columns: b_df[col] = 0.0 if col in ["Odds", "Stake", "P/L", "Cashout_Amt"] else ""
        for col in REQUIRED["Meta"]:
            if col not in m_df.columns: m_df[col] = ""

        st.session_state.bets_df = b_df
        st.session_state.cash_df = c_df
        st.session_state.meta_df = m_df
        st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
    except Exception as e:
        st.error(f"Sync Failure: {e}"); st.stop()

# Date sanitization
st.session_state.bets_df['Date'] = pd.to_datetime(st.session_state.bets_df['Date']).dt.date
df_bets = st.session_state.bets_df
df_cash = st.session_state.cash_df
df_meta = st.session_state.meta_df

# --- 4. GLOBAL ANALYTICS LOGIC ---
def get_streak_stats(df):
    if df.empty: return "N/A", "#8b949e"
    graded = df[df['Status'].isin(['Won', 'Lost'])].sort_values(['Date', 'id'], ascending=False)
    if graded.empty: return "0-0", "#8b949e"
    results = graded['Status'].tolist()
    curr, count = results[0], 0
    for r in results:
        if r == curr: count += 1
        else: break
    return f"{count} {curr}", ("#00ffc8" if curr == "Won" else "#ff4b4b")

# --- 5. SIDEBAR & BRANDING ---
with st.sidebar:
    st.markdown("### 🛰️ CONTROL CENTER")

    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} Pending Syncs**")
        if st.button("💾 PUSH TO CLOUD", type="primary"):
            conn.update(worksheet="Bets", data=st.session_state.bets_df)
            conn.update(worksheet="Cash", data=st.session_state.cash_df)
            conn.update(worksheet="Meta", data=st.session_state.meta_df)
            st.session_state.unsaved_count = 0
            st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
            st.rerun()
    else:
        st.success("Cloud Synchronized")
        if st.button("🔄 Force Refresh"):
            for key in ["bets_df", "cash_df", "meta_df", "unsaved_count"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()

    st.divider()
    nav = st.radio("NAVIGATION", ["📊 Dashboard", "📝 Wager Hub", "💰 Treasury", "⚙️ Studio Config"], label_visibility="collapsed")

    # Global Filters for Dashboard
    if nav == "📊 Dashboard":
        st.divider()
        st.markdown("### 🔍 GLOBAL FILTERS")
        with st.container():
            f_bookie = st.multiselect("Filter Bookie", df_bets['Bookie'].unique())
            f_type = st.multiselect("Filter Bet Type", df_bets['Type'].unique())
            f_sport = st.multiselect("Filter Sport", df_bets['Sport'].unique())

    # Akenza Branding
    st.markdown('<div class="sidebar-footer">MADE BY <b>AKENZA WEB STUDIO</b></div>', unsafe_allow_html=True)

# --- 6. DASHBOARD (GLOBAL FILTERS APPLIED) ---
if nav == "📊 Dashboard":
    st.title("📊 Intelligence Dashboard")

    # Apply Filters
    dff = df_bets.copy()
    if f_bookie: dff = dff[dff['Bookie'].isin(f_bookie)]
    if f_type: dff = dff[dff['Type'].isin(f_type)]
    if f_sport: dff = dff[dff['Sport'].isin(f_sport)]

    if dff.empty:
        st.info("No data matches current filters.")
    else:
        # Top KPI Grid
        p_val = pd.to_numeric(dff['P/L']).sum()
        r_val = pd.to_numeric(dff[dff['Status'] == "Pending"]['Stake']).sum()
        s_text, s_color = get_streak_stats(dff)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Net Profit", f"${p_val:,.2f}")
        kpi2.metric("Active Risk", f"${r_val:,.2f}")
        kpi3.metric("Total Wagers", len(dff))
        with kpi4:
            st.markdown(f"""<div class="streak-card">
                <span style="color:#8b949e; font-size:12px; font-weight:bold;">STREAK</span><br>
                <span style="color:{s_color}; font-size:24px; font-weight:800;">{s_text}</span>
            </div>""", unsafe_allow_html=True)

        # Performance Over Time
        st.divider()
        c_time, c_res = st.columns([4, 1])
        res_map = {"Daily": 'D', "Monthly": 'M', "Yearly": 'Y'}
        t_choice = c_res.selectbox("Timeframe", list(res_map.keys()))

        dff['Date'] = pd.to_datetime(dff['Date'])
        time_df = dff.groupby(dff['Date'].dt.to_period(res_map[t_choice])).agg({'P/L': 'sum'}).reset_index()
        time_df['Date'] = time_df['Date'].astype(str)
        time_df['Cum'] = time_df['P/L'].cumsum()

        fig_main = go.Figure()
        fig_main.add_trace(go.Scatter(x=time_df['Date'], y=time_df['Cum'], fill='tozeroy', line_color='#00ffc8', name="Cumulative P/L"))
        fig_main.update_layout(template="plotly_dark", title=f"Profit Growth ({t_choice})", height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_main, use_container_width=True)

        # Comparative Analytics Grid
        st.divider()
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(px.bar(dff.groupby("Sport")['P/L'].sum().reset_index(), x='Sport', y='P/L', title="P/L by Sport", template="plotly_dark", color_discrete_sequence=['#00ffc8']), use_container_width=True)
        with g2:
            st.plotly_chart(px.pie(dff, values='Stake', names='Bookie', hole=.4, title="Volume by Bookie", template="plotly_dark"), use_container_width=True)
        with g3:
            st.plotly_chart(px.bar(dff.groupby("Type")['P/L'].sum().reset_index(), x='Type', y='P/L', title="P/L by Bet Type", template="plotly_dark", color_discrete_sequence=['#ff4b4b']), use_container_width=True)

# --- 7. WAGER HUB ---
elif nav == "📝 Wager Hub":
    st.title("📝 Wager Management")
    t_add, t_pend, t_hist = st.tabs(["➕ LOG NEW", "🔔 PENDING", "📚 SEARCH HISTORY"])

    with t_add:
        with st.form("new_w_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            s_l = df_meta["Sports"].dropna().tolist() if "Sports" in df_meta.columns else []
            l_l = df_meta["Leagues"].dropna().tolist() if "Leagues" in df_meta.columns else []
            b_l = df_meta["Bookies"].dropna().tolist() if "Bookies" in df_meta.columns else []
            t_l = df_meta["Types"].dropna().tolist() if "Types" in df_meta.columns else []

            d_i = c1.date_input("Date", date.today())
            s_i = c1.selectbox("Sport", s_l)
            l_i = c1.selectbox("League", l_l)
            b_i = c2.selectbox("Bookie", b_l)
            t_i = c2.selectbox("Type", t_l)
            e_i = c2.text_input("Selection/Event")
            o_i = c3.number_input("Decimal Odds", 1.01, 500.0, 1.91)
            st_i = c3.number_input("Stake", 1.0, 50000.0, 10.0)
            res_i = c3.selectbox("Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("ADD TO LOCAL SESSION"):
                pl = (st_i * o_i - st_i) if res_i == "Won" else (-st_i if res_i == "Lost" else 0.0)
                nid = int(df_bets['id'].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame([[nid, d_i, s_i, l_i, b_i, t_i, e_i, o_i, st_i, res_i, pl, 0.0]], columns=df_bets.columns)
                st.session_state.bets_df = pd.concat([df_bets, new_row], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.rerun()

    with t_pend:
        pending = df_bets[df_bets['Status'] == "Pending"]
        if pending.empty: st.success("No active exposure.")
        for idx, row in pending.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{row['Event']}** | ${row['Stake']} @ {row['Odds']}")
                res = c2.selectbox("Set Outcome", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"r_{row['id']}")
                if res != "Pending":
                    co = st.number_input("Cashout Payout", key=f"c_{row['id']}") if res == "Cashed Out" else 0.0
                    if st.button("SET RESULT", key=f"b_{row['id']}"):
                        st.session_state.bets_df.at[idx, 'Status'] = res
                        st.session_state.bets_df.at[idx, 'P/L'] = (row['Stake']*row['Odds']-row['Stake']) if res=="Won" else (-row['Stake'] if res=="Lost" else co-row['Stake'])
                        st.session_state.unsaved_count += 1
                        st.rerun()

    with t_hist:
        h_col1, h_col2 = st.columns(2)
        s_date = h_col1.date_input("Filter Date", value=None)
        s_text = h_col2.text_input("Search Selection")

        hist_df = df_bets.copy()
        if s_date: hist_df = hist_df[hist_df['Date'] == s_date]
        if s_text: hist_df = hist_df[hist_df['Event'].str.contains(s_text, case=False)]

        for idx, row in hist_df.sort_values(['Date', 'id'], ascending=False).iterrows():
            with st.expander(f"{row['Date']} | {row['Event']} ({row['Status']})"):
                ci, cd = st.columns([5, 1])
                ci.write(f"Type: {row['Type']} | Bookie: {row['Bookie']} | P/L: ${row['P/L']}")
                if cd.button("DELETE", key=f"del_{row['id']}", type="secondary"):
                    st.session_state.bets_df = df_bets.drop(idx)
                    st.session_state.unsaved_count += 1
                    st.rerun()

# --- 8. TREASURY & CONFIG ---
elif nav == "💰 Treasury":
    st.title("💰 Treasury Management")
    with st.form("cash_log_f"):
        c1, c2, c3 = st.columns(3)
        cb = c1.selectbox("Bookie Source", df_meta["Bookies"].dropna().tolist() if not df_meta.empty else [])
        ct = c2.selectbox("Move Type", ["Deposit", "Withdrawal", "Bonus"])
        ca = c3.number_input("Amount", 0.0)
        if st.form_submit_button("RECORD MOVE"):
            val = -ca if ct == "Withdrawal" else ca
            new_c = pd.DataFrame([[date.today(), cb, ct, val]], columns=["Date", "Bookie", "Type", "Amount"])
            st.session_state.cash_df = pd.concat([df_cash, new_c], ignore_index=True)
            st.session_state.unsaved_count += 1
            st.rerun()
    st.dataframe(st.session_state.cash_df.sort_values("Date", ascending=False), use_container_width=True)

elif nav == "⚙️ Studio Config":
    st.title("⚙️ Studio Configuration")
    c1, c2, c3, c4 = st.columns(4)
    with c1: s_txt = st.text_area("Sports List", "\n".join([str(x) for x in df_meta["Sports"].dropna().tolist()]), height=300)
    with c2: l_txt = st.text_area("Leagues List", "\n".join([str(x) for x in df_meta["Leagues"].dropna().tolist()]), height=300)
    with c3: b_txt = st.text_area("Bookies List", "\n".join([str(x) for x in df_meta["Bookies"].dropna().tolist()]), height=300)
    with c4: t_txt = st.text_area("Bet Types", "\n".join([str(x) for x in df_meta["Types"].dropna().tolist()]), height=300)

    if st.button("UPDATE STUDIO CONFIG"):
        new_meta = {
            "Sports": [x.strip() for x in s_txt.split("\n") if x.strip()],
            "Leagues": [x.strip() for x in l_txt.split("\n") if x.strip()],
            "Bookies": [x.strip() for x in b_txt.split("\n") if x.strip()],
            "Types": [x.strip() for x in t_txt.split("\n") if x.strip()]
        }
        st.session_state.meta_df = pd.DataFrame.from_dict(new_meta, orient='index').transpose()
        st.session_state.unsaved_count += 1
        st.success("Session Config Updated!")
