import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
from datetime import date, datetime

# =========================================================
# 1. GLOBAL CONFIG & THEME
# =========================================================
st.set_page_config(
    page_title="SharpTracker Elite",
    layout="wide",
    page_icon="🎯"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0d1117;
    }

    /* Core layout tweaks */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 32px;
        font-weight: 800;
        color: #00ffc8;
        letter-spacing: -0.5px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 13px;
        color: #8b949e;
        font-weight: 600;
        text-transform: uppercase;
    }

    div[data-testid="stVerticalBlock"] > div:has(div.stMetric) {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px 22px;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    }

    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3.0em;
        transition: all 0.15s ease-in-out;
        border: 1px solid #238636;
        background: #238636;
        color: #ffffff;
    }
    .stButton>button:hover {
        filter: brightness(1.08);
        box-shadow: 0 4px 14px rgba(0, 255, 200, 0.15);
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #21262d;
    }

    .sidebar-footer {
        position: fixed;
        bottom: 18px;
        left: 18px;
        font-size: 11px;
        color: #484f58;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }

    /* Streak card */
    .streak-card {
        background: linear-gradient(145deg, #161b22 0%, #111827 100%);
        border: 1px solid #30363d;
        padding: 22px 18px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }

    /* Containers / expanders */
    div[data-testid="stExpander"] {
        border-radius: 10px;
        border: 1px solid #21262d;
    }
    div[data-testid="stForm"] {
        border-radius: 10px;
        border: 1px solid #21262d;
        padding: 0.5rem 1rem 1rem 1rem;
        background-color: #0d1117;
    }

    /* Table tweaks */
    .stTable, .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 2. AUTHENTICATION
# =========================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None

def reset_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

if not st.session_state.authenticated:
    st.title("🎯 SharpTracker Elite")
    st.markdown("#### Secure System Access")

    with st.container(border=True):
        u_in = st.text_input("Username", placeholder="Your ID")
        p_in = st.text_input("Password", type="password", placeholder="••••••••")
        col_l, col_r = st.columns([1, 2])
        with col_l:
            login = st.button("Unlock Environment", use_container_width=True)
        with col_r:
            st.caption("Access is restricted to authorized users only.")

        if login:
            user_db = st.secrets.get("users", {})
            if u_in in user_db and p_in == user_db[u_in]:
                st.session_state.authenticated = True
                st.session_state.username = u_in
                st.success("Access granted. Loading your environment…")
                st.rerun()
            else:
                st.error("Invalid credentials. Please verify your username/password.")

    st.stop()

# =========================================================
# 3. DATA LAYER / USER ROUTING
# =========================================================
conn: GSheetsConnection = st.connection("gsheets", type=GSheetsConnection)
user = st.session_state.username

BETS_TAB = f"bets_{user}"
CASH_TAB = f"cash_{user}"
META_TAB = f"meta_{user}"

if "unsaved_count" not in st.session_state:
    st.session_state.unsaved_count = 0
if "last_sync" not in st.session_state:
    st.session_state.last_sync = "Never"

def safe_load(tab_name: str, columns: list[str]) -> pd.DataFrame:
    try:
        df = conn.read(worksheet=tab_name, ttl="0s")
        for col in columns:
            if col not in df.columns:
                df[col] = 0.0 if col in ["id", "Odds", "Stake", "P/L", "Cashout_Amt"] else ""
        return df
    except Exception:
        df = pd.DataFrame(columns=columns)
        conn.update(worksheet=tab_name, data=df)
        return df

if "bets_df" not in st.session_state:
    try:
        b_df = safe_load(
            BETS_TAB,
            ["id", "Date", "Sport", "League", "Bookie", "Type",
             "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt"],
        )
        c_df = safe_load(
            CASH_TAB,
            ["Date", "Bookie", "Type", "Amount"],
        )
        m_df = safe_load(
            META_TAB,
            ["Sports", "Leagues", "Bookies", "Types"],
        )

        if not b_df.empty:
            b_df["Date"] = pd.to_datetime(b_df["Date"]).dt.date
        if not c_df.empty:
            c_df["Date"] = pd.to_datetime(c_df["Date"]).dt.date

        st.session_state.bets_df = b_df
        st.session_state.cash_df = c_df
        st.session_state.meta_df = m_df
        st.session_state.last_sync = datetime.now().strftime("%H:%M")
    except Exception as e:
        st.error(f"Routing error: {e}")
        st.stop()

df_bets: pd.DataFrame = st.session_state.bets_df
df_cash: pd.DataFrame = st.session_state.cash_df
df_meta: pd.DataFrame = st.session_state.meta_df

def push_to_cloud():
    conn.update(worksheet=BETS_TAB, data=st.session_state.bets_df)
    conn.update(worksheet=CASH_TAB, data=st.session_state.cash_df)
    conn.update(worksheet=META_TAB, data=st.session_state.meta_df)
    st.session_state.unsaved_count = 0
    st.session_state.last_sync = datetime.now().strftime("%H:%M")
    st.success("All changes saved to cloud.")
    st.rerun()

# =========================================================
# 4. ANALYTICS HELPERS
# =========================================================
def get_streak_stats(df: pd.DataFrame):
    if df.empty:
        return "N/A", "#8b949e"

    graded = df[df["Status"].isin(["Won", "Lost"])].sort_values(
        ["Date", "id"], ascending=False
    )
    if graded.empty:
        return "0-0", "#8b949e"

    res = graded["Status"].tolist()
    curr, count = res[0], 0
    for r in res:
        if r == curr:
            count += 1
        else:
            break

    color = "#00ffc8" if curr == "Won" else "#ff4b4b"
    return f"{count} {curr}", color

# =========================================================
# 5. SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.subheader(f"🎯 SharpTracker: {user.upper()}")
    st.caption(f"Status: Synchronized  •  Last sync: {st.session_state.last_sync}")

    if st.session_state.unsaved_count > 0:
        st.warning(f"**{st.session_state.unsaved_count} Unsaved Changes**")
        if st.button("💾 Push to Cloud", type="primary", use_container_width=True):
            push_to_cloud()

    if st.button("🚪 Logout", use_container_width=True):
        reset_session()
        st.rerun()

    st.divider()
    nav = st.radio(
        "Navigation",
        ["Dashboard", "Wagers", "Bankroll", "Settings"],
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="sidebar-footer">Made by Akenza Web Studio</div>',
        unsafe_allow_html=True,
    )

# =========================================================
# 6. DASHBOARD
# =========================================================
if nav == "Dashboard":
    st.title("Performance Intelligence")

    with st.expander("🔍 Filter Global Analytics", expanded=False):
        f_c1, f_c2, f_c3 = st.columns(3)
        f_bookie = f_c1.multiselect("Bookie", sorted(df_bets["Bookie"].dropna().unique()))
        f_type = f_c2.multiselect("Bet Type", sorted(df_bets["Type"].dropna().unique()))
        f_sport = f_c3.multiselect("Sport", sorted(df_bets["Sport"].dropna().unique()))

    dff = df_bets.copy()
    if f_bookie:
        dff = dff[dff["Bookie"].isin(f_bookie)]
    if f_type:
        dff = dff[dff["Type"].isin(f_type)]
    if f_sport:
        dff = dff[dff["Sport"].isin(f_sport)]

    if dff.empty:
        st.info("Log your first bet in the **Wagers** hub to activate analytics.")
    else:
        # KPI bar
        p_val = pd.to_numeric(dff["P/L"]).sum()
        r_val = pd.to_numeric(dff[dff["Status"] == "Pending"]["Stake"]).sum()
        s_text, s_color = get_streak_stats(dff)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net Profit", f"${p_val:,.2f}")
        m2.metric("Open Risk", f"${r_val:,.2f}")
        m3.metric("Total Bets", len(dff))
        with m4:
            st.markdown(
                f"""
                <div class="streak-card">
                    <span style="color:#8b949e;font-size:11px;font-weight:600;">
                        CURRENT STREAK
                    </span><br>
                    <span style="color:{s_color};font-size:24px;font-weight:800;">
                        {s_text}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

        # Growth graph
        dff_s = dff.sort_values("Date").copy()
        dff_s["Cumulative"] = dff_s["P/L"].cumsum()
        growth_fig = go.Figure(
            go.Scatter(
                x=dff_s["Date"],
                y=dff_s["Cumulative"],
                fill="tozeroy",
                line_color="#00ffc8",
                line_width=3,
            )
        )
        growth_fig.update_layout(
            template="plotly_dark",
            title="Profit Growth Over Time",
            height=450,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(growth_fig, use_container_width=True)

        st.divider()

        # Comparative analytics
        g1, g2, g3 = st.columns(3)

        sport_pl = dff.groupby("Sport", dropna=False)["P/L"].sum().reset_index()
        bookie_vol = dff.groupby("Bookie", dropna=False)["Stake"].sum().reset_index()
        type_pl = dff.groupby("Type", dropna=False)["P/L"].sum().reset_index()

        g1.plotly_chart(
            px.bar(
                sport_pl,
                x="Sport",
                y="P/L",
                title="P/L by Sport",
                template="plotly_dark",
                color_discrete_sequence=["#00ffc8"],
            ),
            use_container_width=True,
        )

        g2.plotly_chart(
            px.pie(
                bookie_vol,
                values="Stake",
                names="Bookie",
                hole=0.45,
                title="Volume by Bookie",
                template="plotly_dark",
            ),
            use_container_width=True,
        )

        g3.plotly_chart(
            px.bar(
                type_pl,
                x="Type",
                y="P/L",
                title="P/L by Type",
                template="plotly_dark",
                color_discrete_sequence=["#ff4b4b"],
            ),
            use_container_width=True,
        )

# =========================================================
# 7. WAGERS
# =========================================================
elif nav == "Wagers":
    st.title(f"Wager Management · {user}")

    t_add, t_pend, t_hist = st.tabs(["➕ Add Bet", "✅ Settlement", "📚 History & Delete"])

    # ---------- Add Bet ----------
    with t_add:
        with st.form("add_w_f", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)

            s_l = df_meta["Sports"].dropna().tolist()
            l_l = df_meta["Leagues"].dropna().tolist()
            b_l = df_meta["Bookies"].dropna().tolist()
            t_l = df_meta["Types"].dropna().tolist()

            w_d = c1.date_input("Date", date.today())
            w_s = c1.selectbox("Sport", s_l)
            w_l = c1.selectbox("League", l_l)

            w_b = c2.selectbox("Bookie", b_l)
            w_t = c2.selectbox("Type", t_l)
            w_e = c2.text_input("Selection / Event")

            w_o = c3.number_input("Decimal Odds", 1.01, 1000.0, 1.91)
            w_st = c3.number_input("Stake", 1.0, 100000.0, 10.0)
            w_res = c3.selectbox("Status", ["Pending", "Won", "Lost", "Push", "Cashed Out"])

            submitted = st.form_submit_button("Log Locally")
            if submitted:
                if w_res == "Won":
                    pl = w_st * w_o - w_st
                elif w_res == "Lost":
                    pl = -w_st
                else:
                    pl = 0.0

                nid = int(df_bets["id"].max() + 1) if not df_bets.empty else 1
                new_row = pd.DataFrame(
                    [[nid, w_d, w_s, w_l, w_b, w_t, w_e, w_o, w_st, w_res, pl, 0.0]],
                    columns=df_bets.columns,
                )

                st.session_state.bets_df = pd.concat(
                    [df_bets, new_row], ignore_index=True
                )
                st.session_state.unsaved_count += 1
                st.success("Bet added locally. Remember to push to cloud.")
                st.rerun()

    # ---------- Settlement ----------
    with t_pend:
        pending = df_bets[df_bets["Status"] == "Pending"]
        if pending.empty:
            st.success("No active exposure.")
        else:
            st.caption(f"Open positions: {len(pending)}")
            for idx, row in pending.iterrows():
                with st.container(border=True):
                    pc1, pc2, pc3 = st.columns([3, 2, 1])

                    pc1.write(f"**{row['Event']}**  ·  ${row['Stake']:.2f}  ·  {row['Bookie']}")

                    res = pc2.selectbox(
                        "Result",
                        ["Pending", "Won", "Lost", "Push", "Cashed Out"],
                        key=f"r_{row['id']}",
                        index=0,
                    )

                    co = 0.0
                    if res == "Cashed Out":
                        co = pc3.number_input(
                            "Payout",
                            min_value=0.0,
                            key=f"c_{row['id']}",
                            value=float(row["Stake"]),
                        )

                    if res != "Pending" and st.button("Set Result", key=f"b_{row['id']}"):
                        if res == "Won":
                            pl_val = row["Stake"] * row["Odds"] - row["Stake"]
                        elif res == "Lost":
                            pl_val = -row["Stake"]
                        elif res == "Cashed Out":
                            pl_val = co - row["Stake"]
                        else:
                            pl_val = 0.0

                        st.session_state.bets_df.at[idx, "Status"] = res
                        st.session_state.bets_df.at[idx, "P/L"] = pl_val
                        if res == "Cashed Out":
                            st.session_state.bets_df.at[idx, "Cashout_Amt"] = co

                        st.session_state.unsaved_count += 1
                        st.rerun()

    # ---------- History & Delete ----------
    with t_hist:
        h1, h2 = st.columns(2)
        s_d = h1.date_input("Filter Date", value=None)
        s_t = h2.text_input("Search by event or selection")

        hist = df_bets.copy()
        if s_d:
            hist = hist[hist["Date"] == s_d]
        if s_t:
            hist = hist[hist["Event"].str.contains(s_t, case=False, na=False)]

        if hist.empty:
            st.info("No records match the current filters.")
        else:
            for idx, row in hist.sort_values(
                ["Date", "id"], ascending=False
            ).iterrows():
                label = f"{row['Date']} | {row['Event']} ({row['Status']})"
                with st.expander(label):
                    info_c, del_c = st.columns([5, 1])
                    info_c.write(
                        f"**{row['Type']}** · **{row['Bookie']}**  "
                        f"| Odds: {row['Odds']}  "
                        f"| Stake: ${row['Stake']:.2f}  "
                        f"| P/L: ${row['P/L']:.2f}"
                    )
                    if del_c.button("Delete", key=f"del_{row['id']}", type="secondary"):
                        st.session_state.bets_df = df_bets.drop(idx)
                        st.session_state.unsaved_count += 1
                        st.rerun()

# =========================================================
# 8. BANKROLL
# =========================================================
elif nav == "Bankroll":
    st.title("Bankroll Intelligence")

    with st.form("cash_log_f"):
        tx1, tx2, tx3 = st.columns(3)
        tx_b = tx1.selectbox("Bookie", df_meta["Bookies"].dropna().tolist())
        tx_t = tx2.selectbox("Action", ["Deposit", "Withdrawal", "Bonus"])
        tx_a = tx3.number_input("Amount", 0.0)

        submitted = st.form_submit_button("Record Transaction")
        if submitted:
            v = -tx_a if tx_t == "Withdrawal" else tx_a
            new_tx = pd.DataFrame(
                [[date.today(), tx_b, tx_t, v]],
                columns=["Date", "Bookie", "Type", "Amount"],
            )
            st.session_state.cash_df = pd.concat(
                [df_cash, new_tx], ignore_index=True
            )
            st.session_state.unsaved_count += 1
            st.success("Transaction recorded locally.")
            st.rerun()

    st.subheader("Liquidity Summary")

    summary_rows = []
    for b in df_meta["Bookies"].dropna().unique():
        net_c = df_cash[df_cash["Bookie"] == b]["Amount"].sum()
        net_p = df_bets[df_bets["Bookie"] == b]["P/L"].sum()
        risk = df_bets[
            (df_bets["Bookie"] == b) & (df_bets["Status"] == "Pending")
        ]["Stake"].sum()
        summary_rows.append(
            {
                "Bookie": b,
                "Net Cash": net_c,
                "Total P/L": net_p,
                "Balance (incl. open risk)": net_c + net_p - risk,
            }
        )

    if summary_rows:
        st.table(pd.DataFrame(summary_rows))
    else:
        st.info("No liquidity data yet. Record deposits/withdrawals above.")

    st.markdown("#### Raw Cashflow Ledger")
    if df_cash.empty:
        st.caption("No transactions yet.")
    else:
        st.dataframe(
            df_cash.sort_values("Date", ascending=False),
            use_container_width=True,
        )

# =========================================================
# 9. SETTINGS
# =========================================================
elif nav == "Settings":
    st.title("User Configuration")
    st.info("Edit your personal lists. Changes only affect your account.")

    cfg1, cfg2, cfg3, cfg4 = st.columns(4)

    s_v = cfg1.text_area(
        "Sports",
        "\n".join([str(x) for x in df_meta["Sports"].dropna().tolist()]),
        height=350,
    )
    l_v = cfg2.text_area(
        "Leagues",
        "\n".join([str(x) for x in df_meta["Leagues"].dropna().tolist()]),
        height=350,
    )
    b_v = cfg3.text_area(
        "Bookies",
        "\n".join([str(x) for x in df_meta["Bookies"].dropna().tolist()]),
        height=350,
    )
    t_v = cfg4.text_area(
        "Bet Types",
        "\n".join([str(x) for x in df_meta["Types"].dropna().tolist()]),
        height=350,
    )

    if st.button("Apply Config Updates", type="primary"):
        u_meta = {
            "Sports": [x.strip() for x in s_v.split("\n") if x.strip()],
            "Leagues": [x.strip() for x in l_v.split("\n") if x.strip()],
            "Bookies": [x.strip() for x in b_v.split("\n") if x.strip()],
            "Types": [x.strip() for x in t_v.split("\n") if x.strip()],
        }
        st.session_state.meta_df = pd.DataFrame.from_dict(
            u_meta, orient="index"
        ).transpose()
        st.session_state.unsaved_count += 1
        st.success("Configuration updated locally. Push to cloud to persist.")
