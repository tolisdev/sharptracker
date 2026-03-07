import pandas as pd
import numpy as np


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
    """Core betting metrics"""
    if df.empty:
        return {
            'total_bets': 0,
            'net_pl': 0,
            'open_risk': 0,
            'accuracy_pct': 0,
            'roi_pct': 0,
            'turnover': 0
        }

    # Basic stats
    total_bets = len(df)
    net_pl = pd.to_numeric(df["P/L"]).sum()
    open_risk = pd.to_numeric(df[df["Status"] == "Pending"]["Stake"]).sum()
    turnover = pd.to_numeric(df["Stake"]).sum()

    # Win/Loss for accuracy
    graded = df[df["Status"].isin(["Won", "Lost"])]
    won = len(graded[graded["Status"] == "Won"])
    lost = len(graded[graded["Status"] == "Lost"])
    accuracy_pct = (won / (won + lost) * 100) if (won + lost) > 0 else 0

    # ROI
    roi_pct = (net_pl / turnover * 100) if turnover > 0 else 0

    return {
        'total_bets': total_bets,
        'net_pl': net_pl,
        'open_risk': open_risk,
        'accuracy_pct': accuracy_pct,
        'roi_pct': roi_pct,
        'turnover': turnover
    }
