# swingdash/analytics.py
import numpy as np
import pandas as pd
from config import BETTER_DIRECTION
from typing import Sequence, Tuple, Dict

def compare_sessions(old_desc: pd.DataFrame, new_desc: pd.DataFrame) -> pd.DataFrame:
    """Return merged deltas DataFrame. Never returns None."""
    if old_desc is None or new_desc is None:
        return pd.DataFrame()
    if old_desc.empty or new_desc.empty:
        return pd.DataFrame()

    m = pd.merge(
        old_desc[["Metric", "mean", "median"]],
        new_desc[["Metric", "mean", "median"]],
        on="Metric",
        suffixes=("_old", "_new"),
        how="inner",
    )
    if m.empty:
        return pd.DataFrame()

    m["delta"] = m["mean_new"] - m["mean_old"]
    m["pct_change"] = np.where(
        m["mean_old"].abs() > 1e-9,
        100.0 * m["delta"] / m["mean_old"].replace(0, np.nan),
        np.nan,
    )

    def _improv(row):
        d = BETTER_DIRECTION.get(row["Metric"], 0)
        if d == 0 or not np.isfinite(row["delta"]):
            return np.nan
        return np.sign(row["delta"]) * d

    m["improvement_sign"] = m.apply(_improv, axis=1)
    return m.sort_values(by=["improvement_sign", "pct_change"], ascending=[False, False])

def describe_session(df: pd.DataFrame, metrics: Sequence[str]) -> pd.DataFrame:
    cols = [c for c in metrics if c in df.columns]
    if not cols:
        return pd.DataFrame(columns=["Metric","count","mean","median","std"])
    desc = df[cols].agg(["count", "mean", "median", "std"]).T
    return desc.rename_axis("Metric").reset_index()

def compute_kpis(
    old_desc: pd.DataFrame,
    new_desc: pd.DataFrame,
    kpi_metrics: Sequence[str]
) -> pd.DataFrame:
    """
    Return a tidy KPI table: Metric | old_mean | new_mean | delta | pct_change
    Input desc frames are from describe_session (have columns: Metric,count,mean,median,std).
    """
    if old_desc.empty or new_desc.empty:
        return pd.DataFrame(columns=["Metric","Old","New","Δ","%Δ"])

    m = pd.merge(
        old_desc[["Metric","mean"]].rename(columns={"mean": "Old"}),
        new_desc[["Metric","mean"]].rename(columns={"mean": "New"}),
        on="Metric",
        how="inner",
    )
    m = m[m["Metric"].isin(kpi_metrics)].copy()
    if m.empty:
        return pd.DataFrame(columns=["Metric","Old","New","Δ","%Δ"])

    m["Δ"] = m["New"] - m["Old"]
    m["%Δ"] = np.where(m["Old"].abs() > 1e-9, 100.0 * m["Δ"] / m["Old"], np.nan)
    # consistent order
    m = m[["Metric","Old","New","Δ","%Δ"]]
    return m

def kpi_series_for_metrics(
    old_desc: pd.DataFrame,
    new_desc: pd.DataFrame,
    kpi_metrics: Sequence[str]
) -> Dict[str, Dict[str, float]]:
    """
    For UI metric tiles. Returns:
      { metric: {"old": float, "new": float, "delta": float, "pct": float}, ... }
    """
    tbl = compute_kpis(old_desc, new_desc, kpi_metrics)
    out = {}
    for _, r in tbl.iterrows():
        out[r["Metric"]] = {
            "old": float(r["Old"]),
            "new": float(r["New"]),
            "delta": float(r["Δ"]),
            "pct": float(r["%Δ"]) if np.isfinite(r["%Δ"]) else np.nan
        }
    return out

def balance_samples(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    enable: bool,
    mode: str,
    seed: int,
    stratify_by: Sequence[str] = ("Club Type","Side"),
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Same behaviour you had: 'Simple' → global min; 'Stratified: Club Type + Side' → per-bin min.
    """
    if not enable or old_df.empty or new_df.empty:
        return old_df, new_df

    if mode == "Simple":
        n = min(len(old_df), len(new_df))
        return (old_df.sample(n=n, random_state=seed), new_df.sample(n=n, random_state=seed))

    if mode.startswith("Stratified"):
        by = [c for c in stratify_by if c in old_df.columns and c in new_df.columns]
        if not by:
            return old_df, new_df
        parts_old, parts_new = [], []
        keys = (pd.concat([old_df[by], new_df[by]], ignore_index=True).drop_duplicates())
        for _, key in keys.iterrows():
            mask_old = (old_df[by] == key.values).all(axis=1)
            mask_new = (new_df[by] == key.values).all(axis=1)
            g_old, g_new = old_df[mask_old], new_df[mask_new]
            n_take = min(len(g_old), len(g_new))
            if n_take > 0:
                parts_old.append(g_old.sample(n_take, random_state=seed))
                parts_new.append(g_new.sample(n_take, random_state=seed))
        return (
            pd.concat(parts_old, ignore_index=True) if parts_old else old_df.iloc[0:0],
            pd.concat(parts_new, ignore_index=True) if parts_new else new_df.iloc[0:0],
        )
    return old_df, new_df

