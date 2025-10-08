# swingdash/cleaning.py
import re
import pandas as pd
import os
import numpy as np
from config import CANDIDATE_NUMERIC, UNIT_PATTERNS


_UNIT_RE = re.compile("|".join(UNIT_PATTERNS), flags=re.IGNORECASE)

def load_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeError:
        return pd.read_csv(path)

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def parse_date_series(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    p1 = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S%z", errors="coerce")
    if p1.notna().any():
        return p1
    p2 = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    if p2.notna().any():
        return p2
    return pd.to_datetime(s, errors="coerce", dayfirst=False, utc=False)


def coerce_numeric_series(s: pd.Series) -> pd.Series:
    if s.dtype.kind in "biufc":
        return s.astype(float)
    s = s.astype(str)
    s = s.str.replace(_UNIT_RE, "", regex=True)
    s = s.str.replace(r"[^0-9\.\-eE+]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def drop_units_row_if_present(df: pd.DataFrame) -> pd.DataFrame:
    if df.shape[0] == 0:
        return df
    candidate_cols = [c for c in [
        "Club Speed", "Attack Angle", "Launch Angle", "Spin Rate", "Apex Height",
        "Carry Distance", "Total Distance", "Air Density", "Temperature", "Air Pressure", "Relative Humidity"
    ] if c in df.columns]
    if not candidate_cols:
        return df
    first = df.iloc[0][candidate_cols].astype(str).str.contains(r"^\s*\[.*\]\s*$", na=False)
    if first.any():
        return df.iloc[1:].reset_index(drop=True)
    return df


def preprocess(df: pd.DataFrame, session_label: str) -> pd.DataFrame:
    df = drop_units_row_if_present(df.copy())
    for c in CANDIDATE_NUMERIC:
        if c in df.columns:
            df[c] = coerce_numeric_series(df[c])
    if "Carry Deviation Distance" in df.columns:
        df["|Carry Dev|"] = df["Carry Deviation Distance"].abs()
    if "Total Deviation Distance" in df.columns:
        df["|Total Dev|"] = df["Total Deviation Distance"].abs()
    if "Date" in df.columns:
        df["Date_parsed"] = parse_date_series(df["Date"])
    df["Session"] = session_label
    return df


def iqr_filter(df: pd.DataFrame, cols, whisker=3.0) -> pd.DataFrame:
    dfc = df.copy()
    mask = pd.Series(True, index=dfc.index)
    for c in cols:
        if c not in dfc.columns:
            continue
        x = dfc[c]
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        if np.isfinite(iqr) and iqr > 0:
            lo, hi = q1 - whisker*iqr, q3 + whisker*iqr
            mask &= (x.isna() | ((x >= lo) & (x <= hi)))
    return dfc[mask]

def _signed_series(df: pd.DataFrame, col: str, invert: bool) -> pd.Series:
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index)
    s = pd.to_numeric(df[col], errors="coerce")
    return -s if invert else s

def classify_side(df: pd.DataFrame, primary_col: str, dead_zone_deg: float, handed: str, invert: bool) -> pd.Series:
    """Return categorical 'Left'/'Right'/'Straight' using the chosen column's sign and a dead-zone."""
    s = _signed_series(df, primary_col, invert)
    side = np.where(s.abs() <= dead_zone_deg, "Straight",
            np.where(s > 0, "Right", "Left")).astype(object)
    if handed == "Left-handed":
        side = np.where(side == "Right", "Left",
                np.where(side == "Left", "Right", side))
    return pd.Categorical(side, categories=["Left", "Straight", "Right"], ordered=True)

def add_side_column(df: pd.DataFrame, primary_col: str, dead_zone_deg: float, handed: str, invert: bool) -> pd.DataFrame:
    df = df.copy()
    df["Side"] = classify_side(df, primary_col, dead_zone_deg, handed, invert)
    return df