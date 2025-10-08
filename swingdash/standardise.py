import numpy as np, pandas as pd
from typing import Tuple

def _sample_df(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    if n <= 0 or df.empty:
        return df.iloc[0:0]
    if n >= len(df):
        return df
    return df.sample(n=n, random_state=seed, replace=False)

def _stratified_min_pair(old_df: pd.DataFrame, new_df: pd.DataFrame, by: list[str], seed: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Downsample each session per group to the MIN of (old_g, new_g), then concat groups."""
    if not by:
        return old_df, new_df
    # Build keys present in either frame
    old_groups = old_df.groupby(by, dropna=False)
    new_groups = new_df.groupby(by, dropna=False)
    # Unique group keys across both
    unique_keys = pd.concat([
        old_df[by].drop_duplicates(),
        new_df[by].drop_duplicates()
    ], ignore_index=True).drop_duplicates()
    old_parts, new_parts = [], []
    for _, key_row in unique_keys.iterrows():
        key_dict = {col: key_row[col] for col in by}
        # select group
        mask_old = np.logical_and.reduce([(old_df[col] == key_dict[col]) | (pd.isna(old_df[col]) & pd.isna(key_dict[col])) for col in by])
        mask_new = np.logical_and.reduce([(new_df[col] == key_dict[col]) | (pd.isna(new_df[col]) & pd.isna(key_dict[col])) for col in by])
        g_old = old_df[mask_old]
        g_new = new_df[mask_new]
        n_take = min(len(g_old), len(g_new))
        if n_take > 0:
            old_parts.append(_sample_df(g_old, n_take, seed))
            new_parts.append(_sample_df(g_new, n_take, seed))
    old_bal = pd.concat(old_parts, ignore_index=True) if old_parts else old_df.iloc[0:0]
    new_bal = pd.concat(new_parts, ignore_index=True) if new_parts else new_df.iloc[0:0]
    return old_bal, new_bal

def balance_samples(old_df: pd.DataFrame, new_df: pd.DataFrame, enable: bool, mode: str, seed: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Standardise shot counts to avoid one session dominating stats.
    mode:
      - 'Simple': downsample each session to global min(len(old), len(new))
      - 'Stratified: Club Type + Side': per (Club Type, Side) take min per group
    """
    if not enable:
        return old_df, new_df
    if old_df.empty or new_df.empty:
        return old_df, new_df
    if mode == "Simple":
        n = min(len(old_df), len(new_df))
        return _sample_df(old_df, n, seed), _sample_df(new_df, n, seed)
    elif mode == "Stratified: Club Type + Side":
        by = [c for c in ["Club Type", "Side"] if c in old_df.columns and c in new_df.columns]
        return _stratified_min_pair(old_df, new_df, by, seed)
    else:
        return old_df, new_df