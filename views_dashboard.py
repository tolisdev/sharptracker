import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from analytics import get_streak_stats, basic_counters

def render_dashboard():
    df_bets = st.session_state.bets_df
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
        return

    counters = basic_counters(dff)
    s_text, s_color = get_streak_stats(dff)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Net Profit", f"${counters['net_pl']:,.2f}")
    m2.metric("Open Risk", f"${counters['open_risk']:,.2f}")
    m3.metric("Hit Rate", f"{counters['accuracy_pct']:.1f}%")
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
