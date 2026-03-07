import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta


def _period_stats(df, days_back):
    """Calculate stats for specific period"""
    cutoff = datetime.now().date() - timedelta(days=days_back)
    period_df = df[df['Date'] >= cutoff]
    if period_df.empty:
        return {'bets': 0, 'pl': 0, 'roi': 0, 'hit_rate': 0, 'turnover': 0}

    # Reuse basic_counters logic
    total_bets = len(period_df)
    net_pl = pd.to_numeric(period_df["P/L"]).sum()
    turnover = pd.to_numeric(period_df["Stake"]).sum()

    graded = period_df[period_df["Status"].isin(["Won", "Lost"])]
    won = len(graded[graded["Status"] == "Won"])
    lost = len(graded[graded["Status"] == "Lost"])
    hit_rate = (won / (won + lost) * 100) if (won + lost) > 0 else 0
    roi = (net_pl / turnover * 100) if turnover > 0 else 0

    return {
        'bets': total_bets,
        'pl': net_pl,
        'roi': roi,
        'hit_rate': hit_rate,
        'turnover': turnover
    }


def get_streak_stats(df):
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


def basic_counters(df):
    if df.empty:
        return {
            'total_bets': 0, 'net_pl': 0, 'open_risk': 0,
            'accuracy_pct': 0, 'roi_pct': 0, 'turnover': 0
        }

    total_bets = len(df)
    net_pl = pd.to_numeric(df["P/L"]).sum()
    open_risk = pd.to_numeric(df[df["Status"] == "Pending"]["Stake"]).sum()
    turnover = pd.to_numeric(df["Stake"]).sum()

    graded = df[df["Status"].isin(["Won", "Lost"])]
    won = len(graded[graded["Status"] == "Won"])
    lost = len(graded[graded["Status"] == "Lost"])
    accuracy_pct = (won / (won + lost) * 100) if (won + lost) > 0 else 0

    roi_pct = (net_pl / turnover * 100) if turnover > 0 else 0

    return {
        'total_bets': total_bets,
        'net_pl': net_pl,
        'open_risk': open_risk,
        'accuracy_pct': accuracy_pct,
        'roi_pct': roi_pct,
        'turnover': turnover
    }


def render_dashboard():
    df_bets = st.session_state.bets_df.copy()
    st.title("📊 Performance Intelligence")

    # Filters
    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        bookie_f = col1.multiselect("Bookie", sorted(df_bets['Bookie'].dropna().unique()))
        type_f = col2.multiselect("Bet Type", sorted(df_bets['Type'].dropna().unique()))
        sport_f = col3.multiselect("Sport", sorted(df_bets['Sport'].dropna().unique()))

        df_filtered = df_bets.copy()
        if bookie_f:
            df_filtered = df_filtered[df_filtered['Bookie'].isin(bookie_f)]
        if type_f:
            df_filtered = df_filtered[df_filtered['Type'].isin(type_f)]
        if sport_f:
            df_filtered = df_filtered[df_filtered['Sport'].isin(sport_f)]
    else:
        df_filtered = df_bets

    if df_filtered.empty:
        st.info("👆 Add filters or log your first bet!")
        return

    # Period stats
    st.markdown("### 📅 By Period")
    today_stats = _period_stats(df_filtered, 1)
    week_stats = _period_stats(df_filtered, 7)
    month_stats = _period_stats(df_filtered, 30)
    total_stats = basic_counters(df_filtered)

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric("Today", f"{today_stats['bets']} bets")
        st.caption(f"${today_stats['pl']:,.0f}")

    with r2:
        st.metric("Week", f"{week_stats['bets']} bets")
        st.caption(f"${week_stats['pl']:,.0f}")

    with r3:
        st.metric("Month", f"{month_stats['bets']} bets")
        st.caption(f"${month_stats['pl']:,.0f}")

    with r4:
        st.metric("Total", f"{total_stats['total_bets']} bets")
        st.caption(f"${total_stats['net_pl']:,.0f}")

    st.divider()

    # Core metrics
    st.markdown("### 🎯 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Net P/L", f"${total_stats['net_pl']:,.0f}")

    with col2:
        st.metric("ROI", f"{total_stats['roi_pct']:.1f}%")

    with col3:
        st.metric("Hit Rate", f"{total_stats['accuracy_pct']:.1f}%")

    s_text, s_color = get_streak_stats(df_filtered)
    with col4:
        st.markdown(f"""
            <div style='text-align:center;padding:16px;background:#1a2332;border-radius:10px;border:1px solid #2a3444;'>
                <div style='color:#8b9ba5;font-size:12px;font-weight:600;'>STREAK</div>
                <div style='color:{s_color};font-size:24px;font-weight:800;'>{s_text}</div>
            </div>
        """, unsafe_allow_html=True)

    # More metrics
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Turnover", f"${total_stats['turnover']:,.0f}")
    with col6:
        avg_odds = pd.to_numeric(df_filtered['Odds']).mean()
        st.metric("Avg Odds", f"{avg_odds:.2f}")
    with col7:
        avg_stake = pd.to_numeric(df_filtered['Stake']).mean()
        st.metric("Avg Stake", f"${avg_stake:.0f}")
    with col8:
        open_risk = total_stats['open_risk']
        st.metric("Open Risk", f"${open_risk:.0f}")

    st.divider()

    # Charts
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        sport_pl = df_filtered.groupby('Sport')['P/L'].sum().sort_values(ascending=False).head(6)
        fig1 = px.bar(x=sport_pl.index, y=sport_pl.values,
                     title="P/L by Sport", color_discrete_sequence=['#00ffc8'])
        fig1.update_layout(height=280, margin=dict(t=30))
        st.plotly_chart(fig1, use_container_width=True)

    with col_c2:
        bookie_stake = df_filtered.groupby('Bookie')['Stake'].sum().sort_values(ascending=False).head(6)
        fig2 = px.pie(values=bookie_stake.values, names=bookie_stake.index, title="Stake by Bookie")
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        fig2.update_layout(height=280, margin=dict(t=30))
        st.plotly_chart(fig2, use_container_width=True)

    with col_c3:
        type_pl = df_filtered.groupby('Type')['P/L'].sum()
        fig3 = px.bar(x=type_pl.index, y=type_pl.values, title="P/L by Type",
                     color_discrete_sequence=['#ff6b6b'])
        fig3.update_layout(height=280, margin=dict(t=30))
        st.plotly_chart(fig3, use_container_width=True)

    # Growth chart
    df_growth = df_filtered.sort_values('Date').copy()
    df_growth['Cumulative'] = pd.to_numeric(df_growth['P/L']).cumsum()

    fig_growth = go.Figure(go.Scatter(
        x=df_growth['Date'], y=df_growth['Cumulative'],
        fill='tozeroy', line=dict(color='#00ffc8', width=3)
    ))
    fig_growth.update_layout(template='plotly_dark', title="Cumulative P/L", height=350)
    st.plotly_chart(fig_growth, use_container_width=True)
