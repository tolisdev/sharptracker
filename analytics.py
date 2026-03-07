import pandas as pd

def get_streak_stats(df: pd.DataFrame):
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

def basic_counters(df: pd.DataFrame):
    net_pl = pd.to_numeric(df["P/L"]).sum()
    open_risk = pd.to_numeric(df[df["Status"] == "Pending"]["Stake"]).sum()
    total_bets = len(df)
    won = len(df[df["Status"] == "Won"])
    lost = len(df[df["Status"] == "Lost"])
    accuracy = (won / (won + lost) * 100) if (won + lost) > 0 else 0
    turnover = pd.to_numeric(df["Stake"]).sum()
    roi = (net_pl / turnover * 100) if turnover > 0 else 0
    return {
        "net_pl": net_pl,
        "open_risk": open_risk,
        "total_bets": total_bets,
        "accuracy_pct": accuracy,
        "turnover": turnover,
        "roi_pct": roi,
    }
