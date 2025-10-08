# swingdash/analytics.py
import numpy as np
import pandas as pd
from swingdash.config import KEY_METRICS, BETTER_DIRECTION


def describe_session(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    cols = [c for c in KEY_METRICS if c in df.columns] + [c for c in ["|Carry Dev|", "|Total Dev|"] if c in df.columns]
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return pd.DataFrame()
    desc = df[cols].agg(["count", "mean", "median", "std"]).T
    return desc.rename_axis("Metric").reset_index()

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

