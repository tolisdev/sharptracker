import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json


def _period_stats(df, days_back):
    cutoff = datetime.now().date() - timedelta(days=days_back)
    period_df = df[df["Date"] >= cutoff]
    if period_df.empty:
        return {"bets": 0, "pl": 0, "roi": 0, "hit_rate": 0, "turnover": 0}
    total_bets = len(period_df)
    net_pl = pd.to_numeric(period_df["P/L"]).sum()
    turnover = pd.to_numeric(period_df["Stake"]).sum()
    graded = period_df[period_df["Status"].isin(["Won", "Lost"])]
    won = len(graded[graded["Status"] == "Won"])
    lost = len(graded[graded["Status"] == "Lost"])
    hit_rate = (won / (won + lost) * 100) if (won + lost) > 0 else 0
    roi = (net_pl / turnover * 100) if turnover > 0 else 0
    return {"bets": total_bets, "pl": net_pl, "roi": roi, "hit_rate": hit_rate, "turnover": turnover}


def get_streak_stats(df):
    if df.empty:
        return "N/A", "#8b949e"
    graded = df[df["Status"].isin(["Won", "Lost"])].sort_values(["Date", "id"], ascending=False)
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


def basic_counters(df):
    if df.empty:
        return {"total_bets": 0, "net_pl": 0, "open_risk": 0, "accuracy_pct": 0, "roi_pct": 0, "turnover": 0}
    total_bets = len(df)
    net_pl = pd.to_numeric(df["P/L"]).sum()
    open_risk = pd.to_numeric(df[df["Status"] == "Pending"]["Stake"]).sum()
    turnover = pd.to_numeric(df["Stake"]).sum()
    graded = df[df["Status"].isin(["Won", "Lost"])]
    won = len(graded[graded["Status"] == "Won"])
    lost = len(graded[graded["Status"] == "Lost"])
    accuracy_pct = (won / (won + lost) * 100) if (won + lost) > 0 else 0
    roi_pct = (net_pl / turnover * 100) if turnover > 0 else 0
    return {"total_bets": total_bets, "net_pl": net_pl, "open_risk": open_risk,
            "accuracy_pct": accuracy_pct, "roi_pct": roi_pct, "turnover": turnover}


def _explode_for_sport_analysis(df):
    """
    Expand parlay legs into individual rows for sport/league chart analysis.
    Each leg gets proportional P/L (total P/L / number of legs).
    Regular single bets pass through unchanged.
    """
    rows = []
    for _, row in df.iterrows():
        if row.get("Sport") == "Parlay" and row.get("Legs"):
            try:
                legs = json.loads(row["Legs"])
                if legs:
                    leg_pl = float(row["P/L"]) / len(legs)
                    leg_stake = float(row["Stake"]) / len(legs)
                    for leg in legs:
                        r = row.copy()
                        r["Sport"] = leg.get("sport", "Parlay")
                        r["League"] = leg.get("league", "Multi")
                        r["P/L"] = leg_pl
                        r["Stake"] = leg_stake
                        rows.append(r)
                    continue
            except Exception:
                pass
        rows.append(row)
    return pd.DataFrame(rows)


def render_dashboard():
    df_bets = st.session_state.bets_df.copy()
    st.title("Performance Intelligence")

    df_filtered = df_bets.copy()

    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        bookie_f = col1.multiselect("Bookie", sorted(df_bets["Bookie"].dropna().unique()))
        type_f = col2.multiselect("Bet Type", sorted(df_bets["Type"].dropna().unique()))
        sport_f = col3.multiselect("Sport", sorted(df_bets["Sport"].dropna().unique()))
        if bookie_f:
            df_filtered = df_filtered[df_filtered["Bookie"].isin(bookie_f)]
        if type_f:
            df_filtered = df_filtered[df_filtered["Type"].isin(type_f)]
        if sport_f:
            df_filtered = df_filtered[df_filtered["Sport"].isin(sport_f)]

    if df_filtered.empty:
        st.info("Log your first bet to activate analytics.")
        return

    # Exploded df for sport/league charts (parlays split into legs)
    df_exploded = _explode_for_sport_analysis(df_filtered)

    today_s = _period_stats(df_filtered, 1)
    week_s = _period_stats(df_filtered, 7)
    month_s = _period_stats(df_filtered, 30)
    total_s = basic_counters(df_filtered)

    # Period row
    st.markdown("### 📅 By Period")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Today", f"{today_s['bets']} bets", f"${today_s['pl']:,.0f}")
    r2.metric("Week", f"{week_s['bets']} bets", f"${week_s['pl']:,.0f}")
    r3.metric("Month", f"{month_s['bets']} bets", f"${month_s['pl']:,.0f}")
    r4.metric("Total", f"{total_s['total_bets']} bets", f"${total_s['net_pl']:,.0f}")

    st.divider()

    # Core metrics
    st.markdown("### 🎯 Key Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net P/L", f"${total_s['net_pl']:,.2f}")
    c2.metric("ROI", f"{total_s['roi_pct']:.1f}%")
    c3.metric("Hit Rate", f"{total_s['accuracy_pct']:.1f}%")

    s_text, s_color = get_streak_stats(df_filtered)
    with c4:
        st.metric("Streak", s_text)


    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Turnover", f"${total_s['turnover']:,.2f}")
    c6.metric("Avg Odds", f"{pd.to_numeric(df_filtered['Odds']).mean():.2f}")
    c7.metric("Avg Stake", f"${pd.to_numeric(df_filtered['Stake']).mean():.2f}")
    c8.metric("Open Risk", f"${total_s['open_risk']:,.2f}")

    st.divider()

    # Charts - uses exploded df so parlay legs count per sport
    st.markdown("### 📊 Breakdown")
    ch1, ch2, ch3 = st.columns(3)

    with ch1:
        sport_pl = df_exploded.groupby("Sport")["P/L"].sum().sort_values(ascending=False).head(8)
        fig1 = px.bar(x=sport_pl.index, y=sport_pl.values,
                      title="P/L by Sport (incl. parlay legs)",
                      color_discrete_sequence=["#00ffc8"])
        fig1.update_layout(height=280, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig1, use_container_width=True)

    with ch2:
        bookie_stake = df_filtered.groupby("Bookie")["Stake"].sum().sort_values(ascending=False).head(6)
        fig2 = px.pie(values=bookie_stake.values, names=bookie_stake.index,
                      title="Stake by Bookie", hole=0.4)
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(height=280, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

    with ch3:
        type_pl = df_filtered.groupby("Type")["P/L"].sum()
        fig3 = px.bar(x=type_pl.index, y=type_pl.values,
                      title="P/L by Type",
                      color_discrete_sequence=["#ff6b6b"])
        fig3.update_layout(height=280, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig3, use_container_width=True)

    # League breakdown (exploded)
    league_pl = df_exploded.groupby("League")["P/L"].sum().sort_values(ascending=False).head(8)
    if len(league_pl) > 0:
        fig_l = px.bar(x=league_pl.index, y=league_pl.values,
                       title="P/L by League (incl. parlay legs)",
                       color_discrete_sequence=["#00d4ff"])
        fig_l.update_layout(height=280, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_l, use_container_width=True)

    st.divider()

    # Growth chart
    st.markdown("### 📈 Cumulative P/L")
    df_growth = df_filtered.sort_values("Date").copy()
    df_growth["Cumulative"] = pd.to_numeric(df_growth["P/L"]).cumsum()
    fig_g = go.Figure(go.Scatter(
        x=df_growth["Date"], y=df_growth["Cumulative"],
        fill="tozeroy", line=dict(color="#00ffc8", width=3)
    ))
    fig_g.update_layout(template="plotly_dark", height=380, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_g, use_container_width=True)
