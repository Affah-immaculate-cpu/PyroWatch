"""
Step 2 of the pipeline: turn detections into daily summaries, a calendar
and rule-based alerts.

Analogy: if processing.py is the record clerk, this module is the shift
supervisor who reads the day's log book and says "today was unusually busy".
"""

import numpy as np
import pandas as pd


def daily_summary(raw: pd.DataFrame, groups: pd.DataFrame) -> pd.DataFrame:
    """One row per day: detections, harmonized groups, max FRP, per sensor."""
    if raw.empty:
        return pd.DataFrame(columns=["date", "detections", "groups", "max_frp"])

    by_day = raw.groupby("date").agg(detections=("obs_id", "count"),
                                     max_frp=("frp", "max"))
    per_sensor = raw.pivot_table(index="date", columns="sensor", values="obs_id",
                                 aggfunc="count", fill_value=0)
    per_sensor.columns = [f"{c.lower()}_detections" for c in per_sensor.columns]
    g = groups.groupby("date").size().rename("groups")

    daily = by_day.join(per_sensor).join(g)

    # Fill missing days with zeros so charts don't skip quiet days.
    full_range = pd.date_range(min(daily.index), max(daily.index), freq="D").date
    daily = daily.reindex(full_range)
    daily.index.name = "date"
    count_cols = [c for c in daily.columns if c != "max_frp"]
    daily[count_cols] = daily[count_cols].fillna(0).astype(int)
    return daily.reset_index()


def calendar_matrix(daily: pd.DataFrame, value_col: str = "detections"):
    """
    Reshape daily values into a weeks x weekdays grid (like GitHub's
    contribution calendar). Returns (z, x_labels, y_labels, hover_text).
    """
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    start = d["date"].min() - pd.Timedelta(days=d["date"].min().weekday())
    d["week"] = ((d["date"] - start).dt.days // 7).astype(int)
    d["weekday"] = d["date"].dt.weekday

    n_weeks = d["week"].max() + 1
    z = np.full((7, n_weeks), np.nan)
    text = np.full((7, n_weeks), "", dtype=object)
    for _, r in d.iterrows():
        z[r["weekday"], r["week"]] = r[value_col]
        text[r["weekday"], r["week"]] = f"{r['date']:%a %d %b %Y}<br>{value_col}: {int(r[value_col])}"

    x_labels = [(start + pd.Timedelta(weeks=w)).strftime("%d %b") for w in range(n_weeks)]
    y_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return z, x_labels, y_labels, text


def build_alerts(daily: pd.DataFrame, groups: pd.DataFrame,
                 spike_sigma: float = 2.0, frp_threshold: float = 100.0,
                 window: int = 14) -> pd.DataFrame:
    """
    Simple, transparent rules (NOT emergency warnings):
      1. Activity spike: today's detections > rolling mean + spike_sigma * std
      2. High intensity: a harmonized group with max FRP >= frp_threshold
      3. Persistent fire: a group seen for 48 hours or more
    """
    alerts = []

    if not daily.empty:
        d = daily.copy()
        past = d["detections"].shift(1).rolling(window, min_periods=5)
        d["baseline"] = past.mean()
        d["limit"] = d["baseline"] + spike_sigma * past.std()
        spikes = d[d["detections"] > d["limit"]]
        for _, r in spikes.iterrows():
            alerts.append({
                "date": r["date"], "level": "warning", "rule": "Activity spike",
                "message": (f"{int(r['detections'])} detections vs a "
                            f"{window}-day baseline of {r['baseline']:.0f}"),
                "latitude": np.nan, "longitude": np.nan,
            })

    if not groups.empty:
        hot = groups[groups["max_frp"] >= frp_threshold]
        for _, r in hot.iterrows():
            alerts.append({
                "date": r["date"], "level": "high", "rule": "High intensity",
                "message": f"Group #{r['group_id']} max FRP {r['max_frp']:.0f} MW ({r['sensors']})",
                "latitude": r["latitude"], "longitude": r["longitude"],
            })
        long_lived = groups[groups["duration_hours"] >= 48]
        for _, r in long_lived.iterrows():
            alerts.append({
                "date": r["date"], "level": "info", "rule": "Persistent activity",
                "message": f"Group #{r['group_id']} active for {r['duration_hours']:.0f} h",
                "latitude": r["latitude"], "longitude": r["longitude"],
            })

    cols = ["date", "level", "rule", "message", "latitude", "longitude"]
    if not alerts:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(alerts)[cols].sort_values("date", ascending=False).reset_index(drop=True)
