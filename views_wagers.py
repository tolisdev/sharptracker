import streamlit as st
import pandas as pd
from datetime import date


def _init_ticket_buffer():
    if "ticket_legs" not in st.session_state:
        st.session_state.ticket_legs = []  # list of dicts: {sport, league, event, odds}
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
    st.markdown("##### Ticket Legs")

    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        st.caption("Build a multi‑match ticket. Final odds = product of all leg odds.")
    with col_add2:
        if st.button("➕ Add Match"):
            st.session_state.ticket_legs.append(
                {
                    "sport": df_meta["Sports"].dropna().tolist()[0]
                    if not df_meta["Sports"].dropna().empty
                    else "",
                    "league": df_meta["Leagues"].dropna().tolist()[0]
                    if not df_meta["Leagues"].dropna().empty
                    else "",
                    "event": "",
                    "odds": 1.91,
                }
            )

    if not st.session_state.ticket_legs:
        st.info("No legs added yet. Click **Add Match** to start.")
        return

    for i, leg in enumerate(st.session_state.ticket_legs):
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([1.4, 1.4, 2.5, 1.1, 0.6])

            sports = df_meta["Sports"].dropna().tolist()
            leagues = df_meta["Leagues"].dropna().tolist()

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
            leg["event"] = c3.text_input(
                "Event / Selection",
                value=leg["event"],
                key=f"leg_event_{i}",
            )
            leg["odds"] = c4.number_input(
                "Odds",
                min_value=1.01,
                max_value=1000.0,
                value=float(leg["odds"]),
                key=f"leg_odds_{i}",
            )
            remove = c5.button("✕", key=f"leg_remove_{i}")
            if remove:
                st.session_state.ticket_legs.pop(i)
                st.experimental_rerun()

    st.caption(f"Combined odds: **{_ticket_odds():.3f}**")


def render_wagers(user: str):
    df_bets = st.session_state.bets_df
    df_meta = st.session_state.meta_df

    _init_ticket_buffer()

    st.title(f"Wager Management · {user}")

    t_add, t_pend, t_hist = st.tabs(
        ["➕ Add Bet", "✅ Settlement", "📚 History & Delete"]
    )

    # ------------------------------------------------------------------
    # Add Bet (single or multi‑match ticket)
    # ------------------------------------------------------------------
    with t_add:
        mode_col1, mode_col2 = st.columns([1, 4])
        with mode_col1:
            st.session_state.ticket_mode = st.radio(
                "Mode",
                ["Single", "Multi‑match ticket"],
                horizontal=False,
            )
        with mode_col2:
            if st.session_state.ticket_mode == "Multi‑match ticket":
                st.info(
                    "Multi‑match ticket: odds will be the product of all leg odds. "
                    "Stake and settlement are handled at ticket level."
                )

        with st.form("add_w_f", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)

            sports_list = df_meta["Sports"].dropna().tolist()
            leagues_list = df_meta["Leagues"].dropna().tolist()
            bookies_list = df_meta["Bookies"].dropna().tolist()
            types_list = df_meta["Types"].dropna().tolist()

            w_d = c1.date_input("Date", date.today())
            w_s = c1.selectbox("Sport", sports_list, index=0 if sports_list else None)
            w_l = c1.selectbox("League", leagues_list, index=0 if leagues_list else None)

            w_b = c2.selectbox("Bookie", bookies_list, index=0 if bookies_list else None)
            w_t = c2.selectbox("Type", types_list, index=0 if types_list else None)

            if st.session_state.ticket_mode == "Single":
                w_e = c2.text_input("Selection / Event")
                w_o = c3.number_input("Decimal Odds", 1.01, 1000.0, 1.91)
            else:
                w_e = c2.text_input("Ticket Name / Notes")
                # odds come from legs, show read‑only current value
                current_ticket_odds = _ticket_odds()
                c3.metric("Ticket Odds", f"{current_ticket_odds:.3f}")
                _render_ticket_legs(df_meta)
                # also keep w_o to store final odds in row
                w_o = current_ticket_odds

            w_st = c3.number_input("Stake", 1.0, 100000.0, 10.0)
            w_res = c3.selectbox(
                "Status",
                ["Pending", "Won", "Lost", "Push", "Cashed Out"],
            )

            submitted = st.form_submit_button("Log Locally")
            if submitted:
                # P/L based on ticket odds (single or multi)
                if w_res == "Won":
                    pl = w_st * w_o - w_st
                elif w_res == "Lost":
                    pl = -w_st
                else:
                    pl = 0.0

                nid = int(df_bets["id"].max() + 1) if not df_bets.empty else 1

                # Store legs as JSON in a new column if multi‑match
                legs_json = ""
                if st.session_state.ticket_mode == "Multi‑match ticket":
                    legs_json = pd.io.json.dumps(st.session_state.ticket_legs)

                # Ensure column exists
                if "Legs" not in df_bets.columns:
                    df_bets["Legs"] = ""

                new_row = pd.DataFrame(
                    [
                        [
                            nid,
                            w_d,
                            w_s,
                            w_l,
                            w_b,
                            w_t,
                            w_e,
                            w_o,
                            w_st,
                            w_res,
                            pl,
                            0.0,
                            legs_json,
                        ]
                    ],
                    columns=list(df_bets.columns) + (["Legs"] if "Legs" not in df_bets.columns else []),
                )

                # Align columns if needed
                new_row = new_row[df_bets.columns]

                st.session_state.bets_df = pd.concat(
                    [df_bets, new_row], ignore_index=True
                )
                st.session_state.unsaved_count += 1

                if st.session_state.ticket_mode == "Multi‑match ticket":
                    st.session_state.ticket_legs = []

                st.success("Bet added locally. Remember to push to cloud.")
                st.experimental_rerun()

    # ------------------------------------------------------------------
    # Settlement
    # ------------------------------------------------------------------
    with t_pend:
        pending = st.session_state.bets_df[
            st.session_state.bets_df["Status"] == "Pending"
        ]
        if pending.empty:
            st.success("No active exposure.")
        else:
            st.caption(f"Open positions: {len(pending)}")
            for idx, row in pending.iterrows():
                with st.container(border=True):
                    pc1, pc2, pc3 = st.columns([3, 2, 1])
                    pc1.write(
                        f"**{row['Event']}**  ·  ${row['Stake']:.2f}  ·  {row['Bookie']}"
                    )

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
                        st.experimental_rerun()

    # ------------------------------------------------------------------
    # History & Delete
    # ------------------------------------------------------------------
    with t_hist:
        df_bets = st.session_state.bets_df
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

                    # show a short legs summary if present
                    if "Legs" in hist.columns and isinstance(row.get("Legs", ""), str) and row["Legs"]:
                        try:
                            legs = pd.io.json.loads(row["Legs"])
                            if legs:
                                st.markdown("**Ticket Legs:**")
                                for leg in legs:
                                    st.write(
                                        f"- {leg.get('sport','')} / {leg.get('league','')} "
                                        f"· {leg.get('event','')} @ {leg.get('odds','')}"
                                    )
                        except Exception:
                            pass

                    if del_c.button("Delete", key=f"del_{row['id']}", type="secondary"):
                        st.session_state.bets_df = df_bets.drop(idx)
                        st.session_state.unsaved_count += 1
                        st.experimental_rerun()
