import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

# --- 1. UI STYLING ---
st.set_page_config(page_title="SharpTracker", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stMetricValue"] { font-size: 30px; font-weight: 700; color: #00ffc8; }
    div[data-testid="stVerticalBlock"] > div:has(div.stMetric) {
        background-color: #161b22;
        border: 1px solid #30333d;
        padding: 20px;
        border-radius: 8px;
    }
    .sidebar-footer {
        position: fixed;
        bottom: 15px;
        left: 15px;
        font-size: 11px;
        color: #6e7681;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .streak-box {
        background: #161b22;
        border: 1px solid #30333d;
        padding: 18px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("SharpTracker")
    with st.container(border=True):
        pwd = st.text_input("Access Key", type="password")
        if st.button("Log In"):
            if pwd == st.secrets.get("APP_PASSWORD", "admin"):
                st.session_state["authenticated"] = True
                st.rerun()
    st.stop()

# --- 3. DATA ENGINE (The "RAM" Layer) ---
conn = st.connection("gsheets", type=GSheetsConnection)

if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0

if "bets_df" not in st.session_state:
    try:
        # Pulling Data from Cloud
        b_df = conn.read(worksheet="Bets", ttl="0s")
        c_df = conn.read(worksheet="Cash", ttl="0s")
        m_df = conn.read(worksheet="Meta", ttl="0s")

        # REQUIRED COLUMN VALIDATION (Prevents KeyErrors)
        bet_columns = ["id", "Date", "Sport", "League", "Bookie", "Type", "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"]
        for col in bet_columns:
            if col not in b_df.columns:
                if col in ["id", "Odds", "Stake", "P/L", "Cashout_Amt"]:
                    b_df[col] = 0.0
                else:
                    b_df[col] = ""

        meta_columns = ["Sports", "Leagues", "Bookies", "Types"]
        for col in meta_columns:
            if col not in m_df.columns:
                m_df[col] = ""

        # Formatting Dates for Python Processing
        if not b_df.empty:
            b_df['Date'] = pd.to_datetime(b_df['Date']).dt.date
        if not c_df.empty:
            c_df['Date'] = pd.to_datetime(c_df['Date']).dt.date

        st.session_state.bets_df = b_df
        st.session_state.cash_df = c_df
        st.session_state.meta_df = m_df
        st.session_state.last_sync = datetime.now().strftime("%H:%M")
    except Exception as e:
        st.error(f"Sync Failure: {e}")
        st.stop()

# Local References
df_bets = st.session_state.bets_df
df_cash = st.session_state.cash_df
df_meta = st.session_state.meta_df

# --- 4. ANALYTICS LOGIC ---
def get_streak_stats(df):
    if df.empty:
        return "N/A", "#8b949e"
    # Filtering for graded bets only
    graded = df[df['Status'].isin(['Won', 'Lost'])]
    if graded.empty:
        return "0-0", "#8b949e"

    # Sorting newest to oldest
    graded = graded.sort_values(['Date', 'id'], ascending=False)
    results = graded['Status'].tolist()

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
    st.subheader("SharpTracker")
    st.caption(f"Last Cloud Sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        st.warning(f"{st.session_state.unsaved_count} Unsaved Changes")
        if st.button("Push to Cloud", type="primary", use_container_width=True):
            conn.update(worksheet="Bets", data=st.session_state.bets_df)
            conn.update(worksheet="Cash", data=st.session_state.cash_df)
            conn.update(worksheet="Meta", data=st.session_state.meta_df)
            st.session_state.unsaved_count = 0
            st.session_state.last_sync = datetime.now().strftime("%H:%M")
            st.success("Cloud Updated")
            st.rerun()
    else:
        if st.button("Refresh from Cloud", use_container_width=True):
            for key in ["bets_df", "cash_df", "meta_df", "unsaved_count"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.divider()
    nav = st.radio("Navigation", ["Dashboard", "Wagers", "Bankroll", "Settings"], label_visibility="collapsed")

    # BRANDING
    st.markdown('<div class="sidebar-footer">Made by Akenza Web Studio</div>', unsafe_allow_html=True)

# --- 6. DASHBOARD PAGE ---
if nav == "Dashboard":
    st.title("Dashboard")

    # INLINE DYNAMIC FILTERS
    with st.expander("🔍 Filter Global Analytics", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        bookie_list = df_bets['Bookie'].unique().tolist()
        type_list = df_bets['Type'].unique().tolist()
        sport_list = df_bets['Sport'].unique().tolist()

        f_bookie = f_col1.multiselect("Bookie", bookie_list)
        f_type = f_col2.multiselect("Type", type_list)
        f_sport = f_col3.multiselect("Sport", sport_list)

    # Applying Filters to the view
    dff = df_bets.copy()
    if f_bookie:
        dff = dff[dff['Bookie'].isin(f_bookie)]
    if f_type:
        dff = dff[dff['Type'].isin(f_type)]
    if f_sport:
        dff = dff[dff['Sport'].isin(f_sport)]

    if dff.empty:
        st.info("No data available for the current filters.")
    else:
        # Metrics Calculation
        total_p_l = pd.to_numeric(dff['P/L']).sum()
        total_risk = pd.to_numeric(dff[dff['Status'] == "Pending"]['Stake']).sum()
        total_bets = len(dff)
        streak_text, streak_color = get_streak_stats(dff)

        # Metric Layout
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net Profit", f"${total_p_l:,.2f}")
        m2.metric("Open Risk", f"${total_risk:,.2f}")
        m3.metric("Total Bets", total_bets)
        with m4:
            st.markdown(f'''
                <div class="streak-box">
                    <span style="color:#8b949e;font-size:11px;font-weight:600;">STREAK</span><br>
                    <span style="color:{streak_color};font-size:22px;font-weight:800;">{streak_text}</span>
                </div>
            ''', unsafe_allow_html=True)

        # Main Growth Chart (Full Width)
        st.divider()
        dff_sorted = dff.sort_values('Date')
        dff_sorted['Cumulative'] = dff_sorted['P/L'].cumsum()

        fig_growth = go.Figure()
        fig_growth.add_trace(go.Scatter(
            x=dff_sorted['Date'],
            y=dff_sorted['Cumulative'],
            fill='tozeroy',
            line_color='#00ffc8',
            name="Profit"
        ))
        fig_growth.update_layout(template="plotly_dark", title="Profit Over Time", height=400)
        st.plotly_chart(fig_growth, use_container_width=True)

        # Multi-Graph Comparative Analytics
        st.divider()
        g1, g2, g3 = st.columns(3)

        # Profit by Sport
        sport_stats = dff.groupby("Sport")['P/L'].sum().reset_index()
        g1.plotly_chart(px.bar(sport_stats, x='Sport', y='P/L', title="Profit by Sport", template="plotly_dark", color_discrete_sequence=['#00ffc8']), use_container_width=True)

        # Volume by Bookie
        bookie_vol = dff.groupby("Bookie")['Stake'].sum().reset_index()
        g2.plotly_chart(px.pie(bookie_vol, values='Stake', names='Bookie', hole=.4, title="Volume by Bookie", template="plotly_dark"), use_container_width=True)

        # Profit by Bet Type
        type_stats = dff.groupby("Type")['P/L'].sum().reset_index()
        g3.plotly_chart(px.bar(type_stats, x='Type', y='P/L', title="Profit by Bet Type", template="plotly_dark", color_discrete_sequence=['#ff4b4b']), use_container_width=True)

# --- 7. WAGERS PAGE ---
elif nav == "Wagers":
    st.title("Wagers")
    tab_add, tab_pend, tab_hist = st.tabs(["Add Bet", "Pending Bets", "Full History"])

    with tab_add:
        with st.form("add_wager_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            # Fetching dropdowns from Meta
            sports_list = df_meta["Sports"].dropna().tolist()
            leagues_list = df_meta["Leagues"].dropna().tolist()
            bookies_list = df_meta["Bookies"].dropna().tolist()
            types_list = df_meta["Types"].dropna().tolist()

            w_date = col1.date_input("Date", date.today())
            w_sport = col1.selectbox("Sport", sports_list)
            w_league = col1.selectbox("League", leagues_list)

            w_bookie = col2.selectbox("Bookie", bookies_list)
            w_type = col2.selectbox("Bet Type", types_list)
            w_event = col2.text_input("Selection Name")

            w_odds = col3.number_input("Odds (Decimal)", 1.01, 1000.0, 1.91)
            w_stake = col3.number_input("Stake ($)", 1.0, 100000.0, 10.0)
            w_status = col3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("Save to Session"):
                # Calculate P/L
                if w_status == "Won":
                    calculated_pl = (w_stake * w_odds) - w_stake
                elif w_status == "Lost":
                    calculated_pl = -w_stake
                else:
                    calculated_pl = 0.0

                # New ID
                if df_bets.empty:
                    new_id = 1
                else:
                    new_id = int(df_bets['id'].max() + 1)

                new_bet = pd.DataFrame([[
                    new_id, w_date, w_sport, w_league, w_bookie, w_type, w_event, w_odds, w_stake, w_status, calculated_pl, 0.0
                ]], columns=df_bets.columns)

                st.session_state.bets_df = pd.concat([df_bets, new_bet], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.rerun()

    with tab_pend:
        open_bets = df_bets[df_bets['Status'] == "Pending"]
        if open_bets.empty:
            st.success("All bets are currently settled.")
        else:
            for idx, row in open_bets.iterrows():
                with st.container(border=True):
                    p_c1, p_c2, p_c3 = st.columns([3, 2, 1])
                    p_c1.write(f"**{row['Event']}**")
                    p_c1.caption(f"{row['Bookie']} | ${row['Stake']} @ {row['Odds']}")

                    new_res = p_c2.selectbox("Set Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"res_{row['id']}")

                    if new_res != "Pending":
                        cash_out_val = 0.0
                        if new_res == "Cashed Out":
                            cash_out_val = st.number_input("Payout Received", key=f"co_{row['id']}")

                        if st.button("Confirm", key=f"btn_{row['id']}"):
                            st.session_state.bets_df.at[idx, 'Status'] = new_res
                            if new_res == "Won":
                                st.session_state.bets_df.at[idx, 'P/L'] = (row['Stake'] * row['Odds']) - row['Stake']
                            elif new_res == "Lost":
                                st.session_state.bets_df.at[idx, 'P/L'] = -row['Stake']
                            elif new_res == "Cashed Out":
                                st.session_state.bets_df.at[idx, 'P/L'] = cash_out_val - row['Stake']
                                st.session_state.bets_df.at[idx, 'Cashout_Amt'] = cash_out_val

                            st.session_state.unsaved_count += 1
                            st.rerun()

    with tab_hist:
        h_c1, h_c2 = st.columns(2)
        filter_date = h_c1.date_input("Filter by Date", value=None)
        filter_text = h_c2.text_input("Search Selection")

        hist_view = df_bets.copy()
        if filter_date:
            hist_view = hist_view[hist_view['Date'] == filter_date]
        if filter_text:
            hist_view = hist_view[hist_view['Event'].str.contains(filter_text, case=False)]

        for idx, row in hist_view.sort_values(['Date', 'id'], ascending=False).iterrows():
            with st.expander(f"{row['Date']} | {row['Event']} ({row['Status']})"):
                info_c, del_c = st.columns([5, 1])
                info_c.write(f"**{row['Type']}** | **{row['Bookie']}** | Odds: {row['Odds']} | Stake: ${row['Stake']} | P/L: ${row['P/L']}")
                if del_c.button("Delete", key=f"del_{row['id']}", type="secondary"):
                    st.session_state.bets_df = df_bets.drop(idx)
                    st.session_state.unsaved_count += 1
                    st.rerun()

# --- 8. BANKROLL PAGE ---
elif nav == "Bankroll":
    st.title("Bankroll")
    with st.form("transaction_form"):
        tx_c1, tx_c2, tx_c3 = st.columns(3)
        tx_bookie = tx_c1.selectbox("Source", df_meta["Bookies"].dropna().tolist())
        tx_type = tx_c2.selectbox("Action", ["Deposit", "Withdrawal", "Bonus"])
        tx_amt = tx_c3.number_input("Amount ($)", 0.0)

        if st.form_submit_button("Log Transaction"):
            final_amt = -tx_amt if tx_type == "Withdrawal" else tx_amt
            new_tx = pd.DataFrame([[date.today(), tx_bookie, tx_type, final_amt]], columns=["Date", "Bookie", "Type", "Amount"])
            st.session_state.cash_df = pd.concat([df_cash, new_tx], ignore_index=True)
            st.session_state.unsaved_count += 1
            st.rerun()

    st.subheader("Transaction History")
    st.dataframe(st.session_state.cash_df.sort_values("Date", ascending=False), use_container_width=True)

# --- 9. SETTINGS PAGE ---
elif nav == "Settings":
    st.title("Settings")
    st.info("Edit your lists here. Remember to Push to Cloud to save these dropdown options permanently.")

    cfg_c1, cfg_c2, cfg_c3, cfg_c4 = st.columns(4)

    # sports
    s_val = "\n".join([str(x) for x in df_meta["Sports"].dropna().tolist()])
    new_s = cfg_c1.text_area("Sports", s_val, height=300)

    # leagues
    l_val = "\n".join([str(x) for x in df_meta["Leagues"].dropna().tolist()])
    new_l = cfg_c2.text_area("Leagues", l_val, height=300)

    # bookies
    b_val = "\n".join([str(x) for x in df_meta["Bookies"].dropna().tolist()])
    new_b = cfg_c3.text_area("Bookies", b_val, height=300)

    # types
    t_val = "\n".join([str(x) for x in df_meta["Types"].dropna().tolist()])
    new_t = cfg_c4.text_area("Bet Types", t_val, height=300)

    if st.button("Update Configuration"):
        updated_meta = {
            "Sports": [x.strip() for x in new_s.split("\n") if x.strip()],
            "Leagues": [x.strip() for x in new_l.split("\n") if x.strip()],
            "Bookies": [x.strip() for x in new_b.split("\n") if x.strip()],
            "Types": [x.strip() for x in new_t.split("\n") if x.strip()]
        }
        st.session_state.meta_df = pd.DataFrame.from_dict(updated_meta, orient='index').transpose()
        st.session_state.unsaved_count += 1
        st.success("Config updated locally!")
