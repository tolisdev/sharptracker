import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

# --- 1. PURE UI & SYSTEM STYLING ---
st.set_page_config(page_title="SharpTracker", layout="wide", page_icon="🎯")

# Explicit CSS Injection for Professional UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Metric Card Styling */
    [data-testid="stMetricValue"] {
        font-size: 32px;
        font-weight: 800;
        color: #00ffc8;
        letter-spacing: -0.5px;
    }

    [data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #8b949e;
        font-weight: 600;
    }

    /* Professional Containers */
    div[data-testid="stVerticalBlock"] > div:has(div.stMetric) {
        background-color: #161b22;
        border: 1px solid #30333d;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Sidebar Refinement */
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        left: 20px;
        font-size: 11px;
        color: #484f58;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }

    /* Streak Visualizer */
    .streak-card {
        background: #161b22;
        border: 1px solid #30333d;
        padding: 22px;
        border-radius: 12px;
        text-align: center;
        min-height: 100px;
    }

    /* Table & Dataframe UI */
    .stDataFrame {
        border: 1px solid #30333d;
        border-radius: 8px;
    }

    /* Form Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3.2em;
        transition: all 0.2s ease;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MULTI-LEVEL AUTHENTICATION ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🎯 SharpTracker Elite")
    st.markdown("### Secure Access Required")

    with st.container(border=True):
        auth_col1, auth_col2 = st.columns([2, 1])
        with auth_col1:
            pwd_input = st.text_input("Enter System Access Key", type="password")
        with auth_col2:
            st.write("##")
            if st.button("Unlock System", use_container_width=True):
                if pwd_input == st.secrets.get("APP_PASSWORD", "admin"):
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid Key")
    st.stop()

# --- 3. THE DATA ENGINE (Explicit RAM Mapping) ---
conn = st.connection("gsheets", type=GSheetsConnection)

if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0
if "last_sync" not in st.session_state:
    st.session_state.last_sync = "Never"

# Initial Fetch Logic (Explicit Load)
if "bets_df" not in st.session_state:
    try:
        # Pull Raw Dataframes
        raw_bets = conn.read(worksheet="Bets", ttl="0s")
        raw_cash = conn.read(worksheet="Cash", ttl="0s")
        raw_meta = conn.read(worksheet="Meta", ttl="0s")

        # SELF-HEALING & SCHEMA ENFORCEMENT
        # This prevents KeyErrors if columns are missing in the sheet
        required_bet_fields = [
            "id", "Date", "Sport", "League", "Bookie",
            "Type", "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"
        ]
        for field in required_bet_fields:
            if field not in raw_bets.columns:
                if field in ["id", "Odds", "Stake", "P/L", "Cashout_Amt"]:
                    raw_bets[field] = 0.0
                else:
                    raw_bets[field] = "N/A"

        required_meta_fields = ["Sports", "Leagues", "Bookies", "Types"]
        for field in required_meta_fields:
            if field not in raw_meta.columns:
                raw_meta[field] = ""

        # Date Sanitization
        if not raw_bets.empty:
            raw_bets['Date'] = pd.to_datetime(raw_bets['Date']).dt.date
        if not raw_cash.empty:
            raw_cash['Date'] = pd.to_datetime(raw_cash['Date']).dt.date

        # Commit to Session RAM
        st.session_state.bets_df = raw_bets
        st.session_state.cash_df = raw_cash
        st.session_state.meta_df = raw_meta
        st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")

    except Exception as e:
        st.error(f"FATAL SYNC ERROR: {e}")
        st.info("Check your Google Sheet tab names: 'Bets', 'Cash', 'Meta'")
        st.stop()

# Short-hand variables for readability
df_bets = st.session_state.bets_df
df_cash = st.session_state.cash_df
df_meta = st.session_state.meta_df

# --- 4. ADVANCED ANALYTICS LOGIC ---
def calculate_streak_intelligence(df):
    """Explicitly calculates the current win/loss momentum"""
    if df.empty:
        return "N/A", "#8b949e"

    # Filter for settled bets (Won/Lost)
    settled = df[df['Status'].isin(['Won', 'Lost'])]
    if settled.empty:
        return "0-0", "#8b949e"

    # Sort by Date descending, then ID descending
    settled = settled.sort_values(['Date', 'id'], ascending=[False, False])
    results_list = settled['Status'].tolist()

    first_result = results_list[0]
    streak_counter = 0

    for r in results_list:
        if r == first_result:
            streak_counter += 1
        else:
            break

    streak_color = "#00ffc8" if first_result == "Won" else "#ff4b4b"
    return f"{streak_counter} {first_result}", streak_color

# --- 5. SIDEBAR NAVIGATION & SYNC STATUS ---
with st.sidebar:
    st.title("🎯 SharpTracker")
    st.caption(f"Status: Connected | Sync: {st.session_state.last_sync}")

    st.divider()

    # Navigation Radio
    nav_choice = st.radio(
        "Navigation",
        ["Dashboard", "Wagers", "Bankroll", "Settings"],
        label_visibility="collapsed"
    )

    st.divider()

    # Explicit Sync Controls
    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} PENDING CHANGES**")
        if st.button("💾 PUSH TO CLOUD", type="primary", use_container_width=True):
            with st.spinner("Writing to Google..."):
                try:
                    conn.update(worksheet="Bets", data=st.session_state.bets_df)
                    conn.update(worksheet="Cash", data=st.session_state.cash_df)
                    conn.update(worksheet="Meta", data=st.session_state.meta_df)
                    st.session_state.unsaved_count = 0
                    st.session_state.last_sync = datetime.now().strftime("%H:%M:%S")
                    st.success("Cloud Updated")
                    st.rerun()
                except Exception as e:
                    st.error(f"Write Failed: {e}")
    else:
        st.success("✅ Cloud Synchronized")
        if st.button("🔄 Full Data Refresh", use_container_width=True):
            for key in ["bets_df", "cash_df", "meta_df", "unsaved_count"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # Studio Branding
    st.markdown('<div class="sidebar-footer">Made by Akenza Web Studio</div>', unsafe_allow_html=True)

# --- 6. DASHBOARD (Deep Visualization) ---
if nav_choice == "Dashboard":
    st.title("Dashboard")

    # INLINE FILTERS (Explicit Placement)
    with st.expander("🔍 GLOBAL ANALYTICS FILTERS", expanded=False):
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)

        # Explicit List Extraction
        all_bookies = df_bets['Bookie'].unique().tolist()
        all_types = df_bets['Type'].unique().tolist()
        all_sports = df_bets['Sport'].unique().tolist()
        all_leagues = df_bets['League'].unique().tolist()

        sel_bookies = f_col1.multiselect("Bookie", all_bookies)
        sel_types = f_col2.multiselect("Bet Type", all_types)
        sel_sports = f_col3.multiselect("Sport", all_sports)
        sel_leagues = f_col4.multiselect("League", all_leagues)

    # Filter Application
    dff = df_bets.copy()
    if sel_bookies: dff = dff[dff['Bookie'].isin(sel_bookies)]
    if sel_types: dff = dff[dff['Type'].isin(sel_types)]
    if sel_sports: dff = dff[dff['Sport'].isin(sel_sports)]
    if sel_leagues: dff = dff[dff['League'].isin(sel_leagues)]

    if dff.empty:
        st.info("No data entries found matching your filter selection.")
    else:
        # TOP ROW: METRICS GRID
        # Explicit calculations to avoid pandas errors
        numeric_pl = pd.to_numeric(dff['P/L'], errors='coerce').fillna(0)
        numeric_stake = pd.to_numeric(dff['Stake'], errors='coerce').fillna(0)

        total_p_l = numeric_pl.sum()
        total_risk = numeric_stake[dff['Status'] == "Pending"].sum()
        roi_calc = (total_p_l / numeric_stake.sum() * 100) if numeric_stake.sum() > 0 else 0

        streak_label, streak_hex = calculate_streak_intelligence(dff)

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Net Profit", f"${total_p_l:,.2f}", delta=f"{roi_calc:.1f}% ROI")
        m_col2.metric("Active Exposure", f"${total_risk:,.2f}")
        m_col3.metric("Total Volume", f"${numeric_stake.sum():,.2f}")
        with m_col4:
            st.markdown(f'''
                <div class="streak-card">
                    <span style="color:#8b949e; font-size:12px; font-weight:700; text-transform:uppercase;">Current Momentum</span><br>
                    <span style="color:{streak_hex}; font-size:26px; font-weight:800;">{streak_label}</span>
                </div>
            ''', unsafe_allow_html=True)

        # MAIN PERFORMANCE CHART (Explicit go.Figure)
        st.divider()
        chart_df = dff.sort_values('Date')
        chart_df['Cumulative_Profit'] = chart_df['P/L'].cumsum()

        fig_main = go.Figure()
        fig_main.add_trace(go.Scatter(
            x=chart_df['Date'],
            y=chart_df['Cumulative_Profit'],
            mode='lines',
            fill='tozeroy',
            line=dict(color='#00ffc8', width=3),
            fillcolor='rgba(0, 255, 200, 0.1)',
            name="P/L Growth"
        ))
        fig_main.update_layout(
            template="plotly_dark",
            title="Equity Growth (Selected Session)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#30333d'),
            height=450
        )
        st.plotly_chart(fig_main, use_container_width=True)

        # COMPARATIVE ANALYTICS GRID
        st.divider()
        g_col1, g_col2, g_col3 = st.columns(3)

        # Profit by Sport (Explicit Bar)
        sport_p = dff.groupby("Sport")['P/L'].sum().reset_index()
        g_col1.plotly_chart(px.bar(
            sport_p, x='Sport', y='P/L',
            title="P/L by Category", template="plotly_dark",
            color_discrete_sequence=['#00ffc8']
        ), use_container_width=True)

        # Volume by Bookie (Explicit Pie)
        bookie_v = dff.groupby("Bookie")['Stake'].sum().reset_index()
        g_col2.plotly_chart(px.pie(
            bookie_v, values='Stake', names='Bookie',
            hole=.4, title="Volume by Source", template="plotly_dark"
        ), use_container_width=True)

        # Profit by Bet Type (Explicit Bar)
        type_p = dff.groupby("Type")['P/L'].sum().reset_index()
        g_col3.plotly_chart(px.bar(
            type_p, x='Type', y='P/L',
            title="P/L by Wager Type", template="plotly_dark",
            color_discrete_sequence=['#ff4b4b']
        ), use_container_width=True)

# --- 7. WAGERS PAGE (Explicit Settlement & History) ---
elif nav_choice == "Wagers":
    st.title("Wager Hub")
    tab_new, tab_open, tab_history = st.tabs(["➕ LOG NEW WAGER", "🔔 PENDING SETTLEMENT", "📚 SEARCHABLE HISTORY"])

    with tab_new:
        with st.form("wager_submission_form", clear_on_submit=True):
            w_c1, w_c2, w_c3 = st.columns(3)

            # Explicit List Fetching from Meta
            sports_options = df_meta["Sports"].dropna().tolist()
            leagues_options = df_meta["Leagues"].dropna().tolist()
            bookies_options = df_meta["Bookies"].dropna().tolist()
            types_options = df_meta["Types"].dropna().tolist()

            # Form Inputs
            in_date = w_c1.date_input("Date of Wager", date.today())
            in_sport = w_c1.selectbox("Select Sport", sports_options)
            in_league = w_c1.selectbox("Select League", leagues_options)

            in_bookie = w_c2.selectbox("Select Bookie", bookies_options)
            in_type = w_c2.selectbox("Select Wager Type", types_options)
            in_event = w_c2.text_input("Selection Name (e.g. Celtics -4.5)")

            in_odds = w_c3.number_input("Decimal Odds", 1.01, 1000.0, 1.91)
            in_stake = w_c3.number_input("Stake Amount ($)", 1.0, 1000000.0, 10.0)
            in_status = w_c3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            if st.form_submit_button("SAVE TO LOCAL SESSION"):
                # Explicit P/L Calculation
                if in_status == "Won":
                    p_l_final = (in_stake * in_odds) - in_stake
                elif in_status == "Lost":
                    p_l_final = -in_stake
                else:
                    p_l_final = 0.0

                # ID Assignment
                new_wager_id = int(df_bets['id'].max() + 1) if not df_bets.empty else 1

                new_entry = pd.DataFrame([[
                    new_wager_id, in_date, in_sport, in_league, in_bookie,
                    in_type, in_event, in_odds, in_stake, in_status, p_l_final, 0.0
                ]], columns=df_bets.columns)

                st.session_state.bets_df = pd.concat([df_bets, new_entry], ignore_index=True)
                st.session_state.unsaved_count += 1
                st.rerun()

    with tab_open:
        pending_items = df_bets[df_bets['Status'] == "Pending"]
        if pending_items.empty:
            st.success("All wagers have been settled.")
        else:
            for idx, row in pending_items.iterrows():
                with st.container(border=True):
                    s_c1, s_c2, s_c3 = st.columns([3, 2, 1])
                    s_c1.write(f"**{row['Event']}**")
                    s_c1.caption(f"{row['Bookie']} | ${row['Stake']} @ {row['Odds']}")

                    outcome = s_c2.selectbox("Set Result", ["Pending", "Won", "Lost", "Push", "Cashed Out"], key=f"out_{row['id']}")

                    if outcome != "Pending":
                        co_amount = 0.0
                        if outcome == "Cashed Out":
                            co_amount = st.number_input("Payout Total", key=f"co_in_{row['id']}")

                        if st.button("SET RESULT", key=f"settle_btn_{row['id']}"):
                            st.session_state.bets_df.at[idx, 'Status'] = outcome
                            if outcome == "Won":
                                st.session_state.bets_df.at[idx, 'P/L'] = (row['Stake'] * row['Odds']) - row['Stake']
                            elif outcome == "Lost":
                                st.session_state.bets_df.at[idx, 'P/L'] = -row['Stake']
                            elif outcome == "Cashed Out":
                                st.session_state.bets_df.at[idx, 'P/L'] = co_amount - row['Stake']
                                st.session_state.bets_df.at[idx, 'Cashout_Amt'] = co_amount

                            st.session_state.unsaved_count += 1
                            st.rerun()

    with tab_history:
        # SEARCH & FILTER ENGINE
        search_c1, search_c2 = st.columns(2)
        target_date = search_c1.date_input("Filter by Date", value=None)
        target_text = search_c2.text_input("Search Selection Name")

        filtered_view = df_bets.copy()
        if target_date:
            filtered_view = filtered_view[filtered_view['Date'] == target_date]
        if target_text:
            filtered_view = filtered_view[filtered_view['Event'].str.contains(target_text, case=False)]

        # Display Loop
        for idx, row in filtered_view.sort_values(['Date', 'id'], ascending=False).iterrows():
            with st.expander(f"{row['Date']} | {row['Event']} ({row['Status']})"):
                info_col, action_col = st.columns([5, 1])
                info_col.write(f"**{row['Type']}** | {row['Bookie']} | Stake: ${row['Stake']} | P/L: **${row['P/L']}**")
                if action_col.button("❌ DELETE", key=f"rem_{row['id']}", type="secondary"):
                    st.session_state.bets_df = df_bets.drop(idx)
                    st.session_state.unsaved_count += 1
                    st.rerun()

# --- 8. BANKROLL PAGE (Explicit Balance Summary) ---
elif nav_choice == "Bankroll":
    st.title("Bankroll Intelligence")

    # 8a. Balance Summary Table (Explicit Restoration)
    st.subheader("Liquidity Summary")
    summary_rows = []

    active_bookies = df_meta["Bookies"].dropna().unique().tolist()

    for b in active_bookies:
        # Cash moves (deposits/withdrawals)
        bookie_cash = df_cash[df_cash['Bookie'] == b]['Amount'].sum()
        # Graded profits
        bookie_pl = df_bets[df_bets['Bookie'] == b]['P/L'].sum()
        # Current exposure
        bookie_risk = df_bets[(df_bets['Bookie'] == b) & (df_bets['Status'] == "Pending")]['Stake'].sum()

        summary_rows.append({
            "Bookie": b,
            "Net Cash Flow": bookie_cash,
            "Total P/L": bookie_pl,
            "Current Risk": bookie_risk,
            "Available Balance": (bookie_cash + bookie_pl - bookie_risk)
        })

    st.table(pd.DataFrame(summary_rows))

    st.divider()

    # 8b. Transaction Log
    st.subheader("Manual Cash Entry")
    with st.form("transaction_entry_form"):
        tx_c1, tx_c2, tx_c3 = st.columns(3)
        tx_bookie = tx_c1.selectbox("Select Source", active_bookies)
        tx_action = tx_c2.selectbox("Action Type", ["Deposit", "Withdrawal", "Bonus"])
        tx_amount = tx_c3.number_input("Amount ($)", min_value=0.0, step=10.0)

        if st.form_submit_button("LOG TRANSACTION"):
            final_val = -tx_amount if tx_action == "Withdrawal" else tx_amount
            new_tx = pd.DataFrame([[date.today(), tx_bookie, tx_action, final_val]], columns=["Date", "Bookie", "Type", "Amount"])
            st.session_state.cash_df = pd.concat([df_cash, new_tx], ignore_index=True)
            st.session_state.unsaved_count += 1
            st.rerun()

    st.subheader("Transaction History")
    st.dataframe(st.session_state.cash_df.sort_values("Date", ascending=False), use_container_width=True)

# --- 9. SETTINGS PAGE (Explicit Field Management) ---
elif nav_choice == "Settings":
    st.title("System Configuration")
    st.markdown("Edit your global drop-down lists below. These update the local session immediately.")

    set_col1, set_col2, set_col3, set_col4 = st.columns(4)

    # Sports List
    raw_s_list = df_meta["Sports"].dropna().tolist()
    s_input = set_col1.text_area("Category (Sports)", value="\n".join([str(x) for x in raw_s_list]), height=350)

    # Leagues List
    raw_l_list = df_meta["Leagues"].dropna().tolist()
    l_input = set_col2.text_area("League List", value="\n".join([str(x) for x in raw_l_list]), height=350)

    # Bookies List
    raw_b_list = df_meta["Bookies"].dropna().tolist()
    b_input = set_col3.text_area("Managed Bookies", value="\n".join([str(x) for x in raw_b_list]), height=350)

    # Types List
    raw_t_list = df_meta["Types"].dropna().tolist()
    t_input = set_col4.text_area("Bet Types", value="\n".join([str(x) for x in raw_t_list]), height=350)

    if st.button("APPLY CONFIGURATION UPDATES", type="primary"):
        # Explicit Reconstruction of the Meta Dataframe
        updated_meta_dict = {
            "Sports": [x.strip() for x in s_input.split("\n") if x.strip()],
            "Leagues": [x.strip() for x in l_input.split("\n") if x.strip()],
            "Bookies": [x.strip() for x in b_input.split("\n") if x.strip()],
            "Types": [x.strip() for x in t_input.split("\n") if x.strip()]
        }

        # Padding lengths so DataFrame construction doesn't fail
        max_len = max(len(v) for v in updated_meta_dict.values())
        for k in updated_meta_dict:
            while len(updated_meta_dict[k]) < max_len:
                updated_meta_dict[k].append("")

        st.session_state.meta_df = pd.DataFrame(updated_meta_dict)
        st.session_state.unsaved_count += 1
        st.success("Session settings updated. Remember to Push to Cloud to save permanently.")
