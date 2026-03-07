import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from analytics import get_streak_stats, basic_counters

def _period_stats(df, days_back):
    """Calculate stats for specific period"""
    cutoff = datetime.now().date() - timedelta(days=days_back)
    period_df = df[df['Date'] >= cutoff]
    if period_df.empty:
        return {'bets': 0, 'pl': 0, 'roi': 0, 'hit_rate': 0, 'turnover': 0}
    c = basic_counters(period_df)
    return {
        'bets': c['total_bets'],
        'pl': c['net_pl'],
        'roi': c['roi_pct'],
        'hit_rate': c['accuracy_pct'],
        'turnover': c['turnover']
    }

def render_dashboard():
    df_bets = st.session_state.bets_df.copy()
    st.title("📊 Performance Intelligence")

    # ========== FILTERS ==========
    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        bookie_f = col1.multiselect("Bookie", sorted(df_bets['Bookie'].dropna().unique()))
        type_f = col2.multiselect("Bet Type", sorted(df_bets['Type'].dropna().unique()))
        sport_f = col3.multiselect("Sport", sorted(df_bets['Sport'].dropna().unique()))

        df_filtered = df_bets.copy()
        if bookie_f: df_filtered = df_filtered[df_filtered['Bookie'].isin(bookie_f)]
        if type_f: df_filtered = df_filtered[df_filtered['Type'].isin(type_f)]
        if sport_f: df_filtered = df_filtered[df_filtered['Sport'].isin(sport_f)]
    else:
        df_filtered = df_bets

    if df_filtered.empty:
        st.info("👆 Add filters or log your first bet!")
        return

    # ========== PERIOD STATS (like BetDiary) ==========
    st.markdown("### 📅 By Period")
    today_stats = _period_stats(df_filtered, 1)
    week_stats = _period_stats(df_filtered, 7)
    month_stats = _period_stats(df_filtered, 30)
    total_stats = basic_counters(df_filtered)

    r1, r2, r3, r4 = st.columns(4)

    # Today
    with r1:
        st.metric("Today", f"{today_stats['bets']} bets")
        st.caption(f"${today_stats['pl']:,.0f} • {today_stats['roi']:.0f}%")

    # Week
    with r2:
        st.metric("Week", f"{week_stats['bets']} bets")
        st.caption(f"${week_stats['pl']:,.0f} • {week_stats['roi']:.0f}%")

    # Month
    with r3:
        st.metric("Month", f"{month_stats['bets']} bets")
        st.caption(f"${month_stats['pl']:,.0f} • {month_stats['roi']:.0f}%")

    # Total
    with r4:
        st.metric("Total", f"{total_stats['total_bets']} bets")
        st.caption(f"${total_stats['net_pl']:,.0f} • {total_stats['roi_pct']:.1f}%")

    st.divider()

    # ========== CORE METRICS ==========
    st.markdown("### 🎯 Core Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Net P/L", f"${total_stats['net_pl']:,.0f}")

    with col2:
        st.metric("ROI", f"{total_stats['roi_pct']:.1f}%")

    with col3:
        st.metric("Hit Rate", f"{total_stats['accuracy_pct']:.1f}%")

    with col4:
        s_text, s_color = get_streak_stats(df_filtered)
        st.markdown(f"""
            <div style='text-align: center; padding: 16px;
                        background: #1a2332; border-radius: 10px; border: 1px solid #2a3444;'>
                <div style='color: #8b9ba5; font-size: 12px; font-weight: 600;'>STREAK</div>
                <div style='color: {s_color}; font-size: 24px; font-weight: 800;'>
                    {s_text}
                </div>
            </div>
        """, unsafe_allow_html=True)

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
        open_risk = pd.to_numeric(df_filtered[df_filtered['Status']=='Pending']['Stake']).sum()
        st.metric("Open Risk", f"${open_risk:.0f}")

    st.divider()

    # ========== BREAKDOWN CHARTS ==========
    st.markdown("### 📈 Breakdown")

    # Profit by sport
    col_chart1, col_chart2, col_chart3 = st.columns(3)

    with col_chart1:
        sport_pl = df_filtered.groupby('Sport')['P/L'].sum().sort_values(ascending=False).head(8)
        fig1 = px.bar(x=sport_pl.index, y=sport_pl.values,
                     title="P/L by Sport",
                     color_discrete_sequence=['#00ffc8'])
        fig1.update_layout(height=300, margin=dict(t=40, b=20, l=0, r=0), showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        bookie_vol = df_filtered.groupby('Bookie')['Stake'].sum().sort_values(ascending=False).head(8)
        fig2 = px.pie(values=bookie_vol.values, names=bookie_vol.index,
                     title="Stake by Bookie", hole=0.4)
        fig2.update_layout(height=300, margin=dict(t=40, b=20, l=0, r=0))
        st.plotly_chart(fig2, use_container_width=True)

    with col_chart3:
        type_pl = df_filtered.groupby('Type')['P/L'].sum()
        fig3 = px.bar(x=type_pl.index, y=type_pl.values,
                     title="P/L by Type", color_discrete_sequence=['#ff6b6b'])
        fig3.update_layout(height=300, margin=dict(t=40, b=20, l=0, r=0), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ========== GROWTH CHART ==========
    st.markdown("### 📊 Growth")
    df_growth = df_filtered.sort_values('Date').copy()
    df_growth['Cumulative'] = pd.to_numeric(df_growth['P/L']).cumsum()

    fig_growth = go.Figure()
    fig_growth.add_trace(go.Scatter(
        x=df_growth['Date'],
        y=df_growth['Cumulative'],
        fill='tozeroy',
        line=dict(color='#00ffc8', width=3),
        name='Cumulative P/L'
    ))
    fig_growth.update_layout(
        template='plotly_dark',
        title="Profit Evolution",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False
    )
    st.plotly_chart(fig_growth, use_container_width=True)

    # ========== TABLE SUMMARY ==========
    st.markdown("### 📋 Summary Table")
    summary_df = pd.DataFrame({
        'Period': ['Today', 'Week', 'Month', 'Total'],
        'Bets': [today_stats['bets'], week_stats['bets'], month_stats['bets'], total_stats['total_bets']],
        'Turnover': [f"${today_stats['turnover']:,.0f}", f"${week_stats['turnover']:,.0f}",
                    f"${month_stats['turnover']:,.0f}", f"${total_stats['turnover']:,.0f}"],
        'P/L': [f"${today_stats['pl']:,.0f}", f"${week_stats['pl']:,.0f}",
               f"${month_stats['pl']:,.0f}", f"${total_stats['net_pl']:,.0f}"],
        'ROI': [f"{today_stats['roi']:.1f}%", f"{week_stats['roi']:.1f}%",
               f"{month_stats['roi']:.1f}%", f"{total_stats['roi_pct']:.1f}%"],
        'Hit Rate': [f"{today_stats['hit_rate']:.1f}%", f"{week_stats['hit_rate']:.1f}%",
                    f"{month_stats['hit_rate']:.1f}%", f"{total_stats['accuracy_pct']:.1f}%"]
    })
    st.dataframe(summary_df, use_container_width=True)
