import numpy as np, pandas as pd

def assign_group(df: pd.DataFrame, cs_low: float, spin_low: float, carry_low: float, dev_col: str | None, dev_high: float) -> pd.DataFrame:
    df = df.copy()
    cs = df["Club Speed"] if "Club Speed" in df.columns else pd.Series(np.nan, index=df.index)
    spin = df["Spin Rate"] if "Spin Rate" in df.columns else pd.Series(np.nan, index=df.index)
    carry = df["Carry Distance"] if "Carry Distance" in df.columns else pd.Series(np.nan, index=df.index)
    dev = df[dev_col] if (dev_col and dev_col in df.columns) else pd.Series(np.nan, index=df.index)

    cond_short = (cs <= cs_low) & (spin <= spin_low) & (carry <= carry_low)
    cond_shank = (dev >= dev_high)

    group = np.where(cond_short, "Short practice",
             np.where(cond_shank, "Long shank", "Normal"))
    df["Group"] = pd.Categorical(group, categories=["Normal", "Short practice", "Long shank"], ordered=False)
    return df