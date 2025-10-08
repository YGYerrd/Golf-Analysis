"""Plotting and tabular presentation helpers for the SwingDash app."""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px


def _format_float(value: float | int | None, *, decimals: int = 2, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "—"
    return f"{value:.{decimals}f}{suffix}"


def make_session_summary_table(desc_df: pd.DataFrame) -> pd.DataFrame:
    """Return a formatted summary table for a single session."""

    if desc_df is None or desc_df.empty:
        return pd.DataFrame()

    table = desc_df.copy()
    rename_map = {"count": "Shots", "mean": "Mean", "median": "Median", "std": "Std Dev"}
    table = table.rename(columns=rename_map)

    if "Shots" in table.columns:
        table["Shots"] = table["Shots"].astype("Int64")

    for col in ["Mean", "Median", "Std Dev"]:
        if col in table.columns:
            table[col] = table[col].apply(lambda v: _format_float(v, decimals=2))

    desired_cols = [c for c in ["Metric", "Shots", "Mean", "Median", "Std Dev"] if c in table.columns]
    return table[desired_cols]


def make_comparison_table(
    comp_df: pd.DataFrame,
    *,
    old_label: str,
    new_label: str,
) -> pd.DataFrame:
    """Return a formatted comparison table between two sessions."""

    if comp_df is None or comp_df.empty:
        return pd.DataFrame()

    table = comp_df.copy()
    rename_map = {
        "mean_old": f"Mean ({old_label})",
        "mean_new": f"Mean ({new_label})",
        "median_old": f"Median ({old_label})",
        "median_new": f"Median ({new_label})",
    }
    table = table.rename(columns=rename_map)

    table["Δ Mean"] = table["delta"].apply(lambda v: _format_float(v, decimals=2))
    table["Δ %"] = table["pct_change"].apply(lambda v: _format_float(v, decimals=1, suffix="%"))

    direction_map = {1: "↑ Improved", -1: "↓ Worse", 0: "—"}
    table["Direction"] = table["improvement_sign"].map(direction_map).fillna("—")

    ordered_cols = [
        "Metric",
        f"Mean ({old_label})",
        f"Mean ({new_label})",
        "Δ Mean",
        "Δ %",
        f"Median ({old_label})",
        f"Median ({new_label})",
        "Direction",
    ]
    existing_cols = [c for c in ordered_cols if c in table.columns]
    return table[existing_cols]


def make_shot_count_table(
    *,
    old_label: str,
    new_label: str,
    raw_old: int,
    raw_new: int,
    processed_old: int,
    processed_new: int,
    balanced_old: int,
    balanced_new: int,
) -> pd.DataFrame:
    """Return a small table that summarises shot counts at each pipeline stage."""

    rows = [
        ("Raw", raw_old, raw_new),
        ("Processed", processed_old, processed_new),
        ("Balanced", balanced_old, balanced_new),
    ]
    table = pd.DataFrame(rows, columns=["Stage", old_label, new_label])
    return table


def make_shot_table(df: pd.DataFrame, metrics: Optional[Iterable[str]] = None, *, limit: int = 1000) -> pd.DataFrame:
    """Return a tidy table of individual shots limited to key columns."""

    if df is None or df.empty:
        return pd.DataFrame()

    columns = ["Session"]
    if "Date_parsed" in df.columns:
        columns.append("Date_parsed")
    for c in ["Player", "Club Name", "Club Type", "Note", "Tag", "Side"]:
        if c in df.columns and c not in columns:
            columns.append(c)
    if metrics:
        for metric in metrics:
            if metric in df.columns and metric not in columns:
                columns.append(metric)

    columns = [c for c in columns if c in df.columns]
    table = df[columns].copy()

    if "Date_parsed" in table.columns:
        table["Date"] = table["Date_parsed"].dt.strftime("%Y-%m-%d %H:%M")
        table = table.drop(columns=["Date_parsed"])

    if limit and len(table) > limit:
        table = table.head(limit)

    return table


def render_table(title: str, table: pd.DataFrame, *, height: Optional[int] = None) -> None:
    """Render a pandas DataFrame using Streamlit with consistent styling."""

    st.subheader(title)
    if table is None or table.empty:
        st.info("No data available for this section.")
        return
    if height is None:
        st.dataframe(table, use_container_width=True, height="auto")
    else:
        st.dataframe(table, use_container_width=True, height=height)



def scatter(
    df: pd.DataFrame,
    x: str,
    y: str,
    color_by: str,
    hover_cols = None,
    height: int = 520
):
    fig = px.scatter(
        df, x=x, y=y, color=color_by,
        hover_data=[c for c in (hover_cols or []) if c in df.columns],
        opacity=0.75, template="plotly_white"
    )
    fig.update_layout(height=height)
    return fig

def histogram(
    df: pd.DataFrame, metric: str, bins: int = 30, height: int = 460
):
    fig = px.histogram(df, x=metric, color="Session",
                       barmode="overlay", nbins=bins, opacity=0.55,
                       template="plotly_white")
    fig.update_layout(height=height)
    return fig

def box_deviation(df: pd.DataFrame, acc_col: str, height: int = 460, ytitle: str | None = None):
    fig = px.box(df.dropna(subset=[acc_col]), x="Session", y=acc_col,
                 points="outliers", template="plotly_white")
    fig.update_layout(height=height, yaxis_title=ytitle or acc_col)
    return fig

def bar_side_counts(df_counts: pd.DataFrame, height: int = 420):
    # expects columns: Session | Side | Count
    fig = px.bar(df_counts, x="Session", y="Count", color="Side",
                 barmode="stack", template="plotly_white",
                 category_orders={"Side": ["Left","Straight","Right"]})
    fig.update_layout(height=height, title="Counts by side")
    return fig

def scatter_face_vs_path(df: pd.DataFrame, height: int = 520):
    fig = px.scatter(
        df, x="Club Path", y="Club Face",
        color="Side", symbol="Session",
        hover_data=[c for c in ["Face to Path","Carry Distance","Total Distance","Spin Axis"] if c in df.columns],
        template="plotly_white", opacity=0.8
    )
    fig.update_layout(height=height, title="Club Face vs Club Path (quadrants)")
    fig.add_hline(y=0, line_dash="dash")
    fig.add_vline(x=0, line_dash="dash")
    return fig

def box_by_side(df: pd.DataFrame, metric: str, height: int = 460):
    fig = px.box(
        df.dropna(subset=[metric]), x="Side", y=metric, color="Session",
        points="outliers", template="plotly_white",
        category_orders={"Side": ["Left","Straight","Right"]}
    )
    fig.update_layout(height=height, title=f"{metric} distribution by side")
    return fig

def group_box(df: pd.DataFrame, y_metric: str, height: int = 460):
    fig = px.box(
        df.dropna(subset=[y_metric]), x="Group", y=y_metric,
        color="Session", points="outliers", template="plotly_white"
    )
    fig.update_layout(height=height, yaxis_title=y_metric)
    return fig