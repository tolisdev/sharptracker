import streamlit as st
import pandas as pd
from datetime import date


def render_bankroll():
    df_bets = st.session_state.bets_df
    df_cash = st.session_state.cash_df
    df_meta = st.session_state.meta_df

    st.title("Bankroll Intelligence")

    # --- Cash transaction form ---
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

    # --- Summary ---
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

    # --- Ledger ---
    st.markdown("#### Raw Cashflow Ledger")
    if df_cash.empty:
        st.caption("No transactions yet.")
    else:
        st.dataframe(
            df_cash.sort_values("Date", ascending=False),
            use_container_width=True,
        )
