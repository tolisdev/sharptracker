import streamlit as st
import pandas as pd
from datetime import date
import json


def _init_ticket_buffer():
    if "ticket_legs" not in st.session_state:
        st.session_state.ticket_legs = []
    if "ticket_mode" not in st.session_state:
        st.session_state.ticket_mode = "Single"


def _ticket_odds():
    if not st.session_state.ticket_legs:
        return 1.0
    o = 1.0
    for leg in st.session_state.ticket_legs:
        try:
            o *= float(leg["odds"])
        except Exception:
            pass
    return o


def _render_ticket_legs(df_meta):
    sports = df_meta["Sports"].dropna().tolist()
    leagues = df_meta["Leagues"].dropna().tolist()
    tipsters = ["— None —"] + df_meta["Tipsters"].dropna().tolist() if "Tipsters" in df_meta.columns else ["— None —"]

    st.markdown("##### Ticket Legs")
    add_col, odds_col = st.columns([3, 1])
    with add_col:
        st.caption("Each leg has its own sport, league, tipster and odds.")
    with odds_col:
        if st.button("➕ Add Match"):
            st.session_state.ticket_legs.append({
                "sport": sports[0] if sports else "",
                "league": leagues[0] if leagues else "",
                "event": "",
                "odds": 1.91,
                "tipster": "",
            })
            st.rerun()

    if not st.session_state.ticket_legs:
        st.info("Click Add Match to build your ticket.")
        return

    for i, leg in enumerate(st.session_state.ticket_legs):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 0.5])
            leg["sport"] = c1.selectbox(
                "Sport",
                sports if sports else [leg["sport"]],
                index=(sports.index(leg["sport"]) if leg["sport"] in sports else 0),
                key=f"leg_sport_{i}",
            )
            leg["league"] = c2.selectbox(
                "League",
                leagues if leagues else [leg["league"]],
                index=(leagues.index(leg["league"]) if leg["league"] in leagues else 0),
                key=f"leg_league_{i}",
            )
            leg["tipster"] = c3.selectbox(
                "Tipster",
                tipsters,
                index=(tipsters.index(leg["tipster"]) if leg.get("tipster") in tipsters else 0),
                key=f"leg_tipster_{i}",
            )
            if c4.button("✕", key=f"leg_remove_{i}"):
                st.session_state.ticket_legs.pop(i)
                st.rerun()

            e1, e2 = st.columns([3, 1])
            leg["event"] = e1.text_input(
                "Event / Selection",
                value=leg["event"],
                key=f"leg_event_{i}",
            )
            leg["odds"] = e2.number_input(
                "Odds",
                min_value=1.01,
                max_value=1000.0,
                value=float(leg["odds"]),
                key=f"leg_odds_{i}",
            )

    combined = _ticket_odds()
    st.markdown(
        f"""
        <div style="padding: 10px 14px; background: rgba(0,255,200,0.08);
                    border: 1px solid rgba(0,255,200,0.25); border-radius: 8px; margin-top: 8px;">
            <span style="color:#8b9ba5;font-size:12px;">COMBINED ODDS</span>
            <span style="color:#00ffc8;font-size:20px;font-weight:800;margin-left:12px;">
                {combined:.3f}
            </span>
            <span style="color:#8b9ba5;font-size:12px;margin-left:12px;">
                {len(st.session_state.ticket_legs)} legs
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_wagers(user: str):
    df_bets = st.session_state.bets_df
    df_meta = st.session_state.meta_df

    _init_ticket_buffer()

    st.title(f"Wager Management: {user}")

    t_add, t_pend, t_hist = st.tabs(
        ["➕ Add Bet", "✅ Settlement", "📚 History & Delete"]
    )

    # ------------------------------------------------------------------
    # ADD BET
    # ------------------------------------------------------------------
    with t_add:
        mode_col1, mode_col2 = st.columns([1, 4])
        with mode_col1:
            st.session_state.ticket_mode = st.radio(
                "Mode",
                ["Single", "Multi-match ticket"],
                horizontal=False,
            )

        is_multi = st.session_state.ticket_mode == "Multi-match ticket"

        if is_multi:
            _render_ticket_legs(df_meta)

        with st.form("add_w_f", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)

            sports_list = df_meta["Sports"].dropna().tolist()
            leagues_list = df_meta["Leagues"].dropna().tolist()
            bookies_list = df_meta["Bookies"].dropna().tolist()
            types_list = df_meta["Types"].dropna().tolist()
            tipsters_list = ["— None —"] + df_meta["Tipsters"].dropna().tolist() \
                if "Tipsters" in df_meta.columns else ["— None —"]

            w_d = c1.date_input("Date", date.today())

            if not is_multi:
                w_s = c1.selectbox("Sport", sports_list)
                w_l = c1.selectbox("League", leagues_list)
            else:
                c1.markdown(
                    "<div style='color:#8b9ba5;font-size:12px;padding-top:8px;'>"
                    "Sport & League set per leg above.</div>",
                    unsafe_allow_html=True,
                )
                w_s = "Parlay"
                w_l = "Multi"

            w_b = c2.selectbox("Bookie", bookies_list)
            w_t = c2.selectbox("Type", types_list)

            if not is_multi:
                w_e = c2.text_input("Selection / Event")
                w_o = c3.number_input("Decimal Odds", 1.01, 1000.0, 1.91)
                w_tip = c3.selectbox("Tipster", tipsters_list)
            else:
                w_e = c2.text_input("Ticket Name / Notes")
                current_odds = _ticket_odds()
                c3.metric("Ticket Odds", f"{current_odds:.3f}")
                w_o = current_odds
                w_tip = "— None —"

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

                legs_json = ""
                if is_multi:
                    legs_json = json.dumps(st.session_state.ticket_legs)

                tipster_val = "" if w_tip == "— None —" else w_tip

                if "Legs" not in st.session_state.bets_df.columns:
                    st.session_state.bets_df["Legs"] = ""
                if "Tipster" not in st.session_state.bets_df.columns:
                    st.session_state.bets_df["Tipster"] = ""

                new_row = pd.DataFrame(
                    [[nid, w_d, w_s, w_l, w_b, w_t, w_e, w_o, w_st, w_res, pl, 0.0, legs_json, tipster_val]],
                    columns=["id", "Date", "Sport", "League", "Bookie", "Type",
                             "Event", "Odds", "Stake", "Status", "P/L", "Cashout_Amt",
                             "Legs", "Tipster"],
                )

                for col in st.session_state.bets_df.columns:
                    if col not in new_row.columns:
                        new_row[col] = ""
                new_row = new_row[st.session_state.bets_df.columns]

                st.session_state.bets_df = pd.concat(
                    [st.session_state.bets_df, new_row], ignore_index=True
                )
                st.session_state.unsaved_count += 1

                if is_multi:
                    st.session_state.ticket_legs = []

                st.success("Bet logged locally. Push to cloud to save.")
                st.rerun()

    # ------------------------------------------------------------------
    # SETTLEMENT
    # ------------------------------------------------------------------
    with t_pend:
        pending = st.session_state.bets_df[st.session_state.bets_df["Status"] == "Pending"]
        if pending.empty:
            st.success("No active exposure.")
        else:
            st.caption(f"Open positions: {len(pending)}")
            for idx, row in pending.iterrows():
                with st.container(border=True):
                    pc1, pc2, pc3 = st.columns([3, 2, 1])
                    pc1.write(f"**{row['Event']}**  ·  ${float(row['Stake']):.2f}  ·  {row['Bookie']}")
                    if row.get("Tipster"):
                        pc1.caption(f"Tipster: {row['Tipster']}")

                    if row.get("Sport") == "Parlay" and row.get("Legs"):
                        try:
                            legs = json.loads(row["Legs"])
                            with pc1:
                                for leg in legs:
                                    tip_label = f" · {leg.get('tipster','')}" if leg.get("tipster") and leg.get("tipster") != "— None —" else ""
                                    st.caption(f"└ {leg.get('sport','')} · {leg.get('event','')} @ {leg.get('odds','')}{tip_label}")
                        except Exception:
                            pass

                    res = pc2.selectbox(
                        "Result",
                        ["Pending", "Won", "Lost", "Push", "Cashed Out"],
                        key=f"r_{row['id']}",
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
                            pl_val = float(row["Stake"]) * float(row["Odds"]) - float(row["Stake"])
                        elif res == "Lost":
                            pl_val = -float(row["Stake"])
                        elif res == "Cashed Out":
                            pl_val = co - float(row["Stake"])
                        else:
                            pl_val = 0.0

                        st.session_state.bets_df.at[idx, "Status"] = res
                        st.session_state.bets_df.at[idx, "P/L"] = pl_val
                        if res == "Cashed Out":
                            st.session_state.bets_df.at[idx, "Cashout_Amt"] = co

                        st.session_state.unsaved_count += 1
                        st.rerun()

    # ------------------------------------------------------------------
    # HISTORY & DELETE
    # ------------------------------------------------------------------
    with t_hist:
        df_view = st.session_state.bets_df
        h1, h2 = st.columns(2)
        s_d = h1.date_input("Filter Date", value=None)
        s_t = h2.text_input("Search by event")

        hist = df_view.copy()
        if s_d:
            hist = hist[hist["Date"] == s_d]
        if s_t:
            hist = hist[hist["Event"].str.contains(s_t, case=False, na=False)]

        if hist.empty:
            st.info("No records match the current filters.")
        else:
            for idx, row in hist.sort_values(["Date", "id"], ascending=False).iterrows():
                tag = "🎯 PARLAY" if row.get("Sport") == "Parlay" else row.get("Sport", "")
                tipster_tag = f" · {row['Tipster']}" if row.get("Tipster") else ""
                label = f"{row['Date']} | {tag} | {row['Event']} ({row['Status']}){tipster_tag}"
                with st.expander(label):
                    info_c, del_c = st.columns([5, 1])
                    info_c.write(
                        f"**{row['Type']}** · **{row['Bookie']}**  "
                        f"| Odds: {row['Odds']}  "
                        f"| Stake: ${float(row['Stake']):.2f}  "
                        f"| P/L: ${float(row['P/L']):.2f}"
                    )
                    if row.get("Tipster"):
                        info_c.caption(f"Tipster: {row['Tipster']}")

                    if row.get("Sport") == "Parlay" and row.get("Legs"):
                        try:
                            legs = json.loads(row["Legs"])
                            if legs:
                                st.markdown("**Legs:**")
                                for leg in legs:
                                    tip_label = f" · _{leg.get('tipster','')}_" if leg.get("tipster") and leg.get("tipster") != "— None —" else ""
                                    st.write(
                                        f"• **{leg.get('sport','')}** / {leg.get('league','')} "
                                        f"— {leg.get('event','')} @ **{leg.get('odds','')}**{tip_label}"
                                    )
                        except Exception:
                            pass

                    if del_c.button("Delete", key=f"del_{row['id']}", type="secondary"):
                        st.session_state.bets_df = df_view.drop(idx)
                        st.session_state.unsaved_count += 1
                        st.rerun()
