"""
Step 3 (experimental): a very simple "will this grid cell have a detection
tomorrow?" model.

Analogy: the map is cut into squares like a chessboard. For each square and
each day we ask "how busy was this square yesterday, over the last 3 days,
over the last week?" and learn how those answers relate to "was it busy the
next day?". It is like a weather forecaster who mostly says "tomorrow will be
like today" — and we check whether the model actually beats that simple rule.

This is a learning exercise, NOT an operational fire forecast. It ignores
weather, vegetation, land use and human activity.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

FEATURES = ["lag1", "sum3", "sum7", "days_since_last", "doy_sin", "doy_cos"]


def make_cell_days(raw: pd.DataFrame, cell_deg: float = 0.25) -> pd.DataFrame:
    """Build one row per (grid cell, day) with features and tomorrow's target."""
    df = raw[["latitude", "longitude", "date"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["cell_lat"] = (np.floor(df["latitude"] / cell_deg) * cell_deg).round(4)
    df["cell_lon"] = (np.floor(df["longitude"] / cell_deg) * cell_deg).round(4)
    df["cell"] = df["cell_lat"].astype(str) + "_" + df["cell_lon"].astype(str)

    counts = df.groupby(["cell", "date"]).size().rename("count")
    all_days = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    # Grid: every cell that ever burned x every day (zeros where quiet).
    wide = counts.unstack("date").reindex(columns=all_days).fillna(0)

    rows = []
    for cell, series in wide.iterrows():
        s = series.to_numpy()
        active = (s > 0).astype(int)
        # Days since the most recent detection (capped at 30).
        since = np.full(len(s), 30.0)
        last = None
        for t in range(len(s)):
            if active[t]:
                last = t
            since[t] = min(30, t - last) if last is not None else 30
        frame = pd.DataFrame({
            "cell": cell,
            "date": all_days,
            "lag1": s,                                   # today
            "sum3": pd.Series(s).rolling(3, min_periods=1).sum().to_numpy(),
            "sum7": pd.Series(s).rolling(7, min_periods=1).sum().to_numpy(),
            "days_since_last": since,
            "target": np.append(active[1:], np.nan),     # tomorrow
        })
        rows.append(frame)

    cd = pd.concat(rows, ignore_index=True)
    doy = cd["date"].dt.dayofyear
    cd["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    cd["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    lat_lon = cd["cell"].str.split("_", expand=True).astype(float)
    cd["cell_lat"], cd["cell_lon"] = lat_lon[0], lat_lon[1]
    return cd


def _scores(y_true, y_pred, y_prob=None) -> dict:
    out = {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if y_prob is not None and len(set(y_true)) > 1:
        out["roc_auc"] = roc_auc_score(y_true, y_prob)
    return out


def train_and_evaluate(cd: pd.DataFrame, train_fraction: float = 0.7, threshold: float = 0.5):
    """
    Time-based split: learn on earlier days, test on later days
    (never shuffle time series — that would let the model peek at the future).
    """
    labelled = cd.dropna(subset=["target"])
    days = np.sort(labelled["date"].unique())
    if len(days) < 10:
        raise ValueError("Need at least 10 days of data to train a model.")
    cutoff = days[int(len(days) * train_fraction)]
    train = labelled[labelled["date"] < cutoff]
    test = labelled[labelled["date"] >= cutoff]

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(train[FEATURES], train["target"].astype(int))

    prob = model.predict_proba(test[FEATURES])[:, 1]
    y = test["target"].astype(int)
    metrics = pd.DataFrame({
        "Model (logistic regression)": _scores(y, (prob >= threshold).astype(int), prob),
        "Baseline: 'tomorrow = today'": _scores(y, (test["lag1"] > 0).astype(int)),
    }).T

    info = {"cutoff": pd.Timestamp(cutoff).date(), "n_train": len(train), "n_test": len(test),
            "positive_rate_test": float(y.mean())}
    return model, metrics, info


def predict_next_day(model, cd: pd.DataFrame, as_of) -> pd.DataFrame:
    """Probability of at least one detection on (as_of + 1 day), per cell."""
    as_of = pd.Timestamp(as_of)
    today = cd[cd["date"] == as_of].copy()
    if today.empty:
        return today
    today["probability"] = model.predict_proba(today[FEATURES])[:, 1]
    today["forecast_for"] = (as_of + pd.Timedelta(days=1)).date()
    return today.sort_values("probability", ascending=False)


def coefficients(model) -> pd.DataFrame:
    return (pd.DataFrame({"feature": FEATURES, "weight": model.coef_[0]})
            .sort_values("weight", key=abs, ascending=False))
