"""UI helper functions for the SwingDash Streamlit app."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Union

import streamlit as st
import pandas as pd


try:  # pragma: no cover - streamlit is optional during type-checking
    from streamlit.runtime.uploaded_file_manager import UploadedFile  # type: ignore
except Exception:  # pragma: no cover
    UploadedFile = Any  # type: ignore

SessionSource = Union[Path, UploadedFile]


@dataclass
class SessionSelection:
    """Represents a session choice made in the sidebar."""

    label: str
    source: Optional[SessionSource]


def render_table(title: str, df: pd.DataFrame, height: int | None = None):
    if title:
        st.markdown(f"**{title}**")
    kwargs = {"use_container_width": True}
    if isinstance(height, int):
        kwargs["height"] = height
    st.dataframe(df, **kwargs)

def render_kpi_tiles(kpi_map: dict[str, dict[str, float]], max_cols: int = 5):
    metrics = list(kpi_map.keys())[:max_cols]
    cols = st.columns(len(metrics))
    for col, name in zip(cols, metrics):
        rec = kpi_map[name]
        with col:
            st.metric(
                name,
                value=f'{rec["new"]:.2f}',
                delta=f'{rec["delta"]:+.2f} ({rec["pct"]:+.1f}%)'
            )

def render_app_header() -> None:
    """Render the main title and description for the app."""

    st.title("SwingDash – Session Comparison")
    st.caption(
        "Upload or select two sessions to analyse summary metrics, compare averages, "
        "and review individual shots."
    )


def _render_session_picker(
    heading: str,
    available_sessions: Mapping[str, Path],
    *,
    key: str,
    fallback_label: str,
) -> SessionSelection:
    """Render a session picker section and return the selected session."""

    st.sidebar.subheader(heading)
    upload_option = "(Upload new file)"
    options = [upload_option] + sorted(available_sessions.keys())
    chosen = st.sidebar.selectbox(
        "Choose a session",
        options,
        key=f"{key}-select",
        help="Select from discovered CSV files or upload a new session.",
    )

    uploaded = st.sidebar.file_uploader(
        "Upload CSV",
        type=["csv"],
        key=f"{key}-upload",
        help="Upload a TrackMan/Launch Monitor export in CSV format.",
    )

    if chosen != upload_option:
        return SessionSelection(label=chosen, source=available_sessions[chosen])

    if uploaded is not None:
        return SessionSelection(label=uploaded.name or fallback_label, source=uploaded)

    return SessionSelection(label=fallback_label, source=None)


def render_sidebar_session_inputs(
    available_sessions: Mapping[str, Path],
) -> dict[str, SessionSelection]:
    """Render sidebar controls for selecting baseline and comparison sessions."""

    st.sidebar.header("Sessions")
    baseline = _render_session_picker(
        "Baseline session", available_sessions, key="baseline", fallback_label="Baseline"
    )
    comparison = _render_session_picker(
        "Comparison session", available_sessions, key="comparison", fallback_label="Comparison"
    )
    return {"baseline": baseline, "comparison": comparison}


def render_sidebar_filters(
    default_metrics: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Render sidebar controls for filtering and balancing shots."""

    st.sidebar.header("Shot processing")
    apply_iqr = st.sidebar.checkbox(
        "Apply IQR outlier filter",
        value=True,
        help="Removes shots outside the chosen interquartile range multiplier.",
    )
    whisker = st.sidebar.slider(
        "IQR whisker multiplier",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.5,
        disabled=not apply_iqr,
    )

    st.sidebar.header("Standardisation")
    balance = st.sidebar.checkbox(
        "Balance shot counts",
        value=False,
        help="Down-sample sessions so that each has the same shot count.",
    )
    balance_mode = st.sidebar.selectbox(
        "Balancing mode",
        options=["Simple", "Stratified: Club Type + Side"],
        index=0,
        disabled=not balance,
        help="Choose how the balancing algorithm samples shots.",
    )
    balance_seed = st.sidebar.number_input(
        "Random seed",
        min_value=0,
        max_value=9999,
        value=42,
        step=1,
        disabled=not balance,
    )

    st.sidebar.header("Side classification")
    classify_side = st.sidebar.checkbox(
        "Add Side column",
        value=True,
        help="Categorise shots into Left/Straight/Right based on deviation angle.",
    )
    primary_deviation_col = st.sidebar.selectbox(
        "Deviation column",
        options=["Carry Deviation Angle", "Total Deviation Angle"],
        index=0,
        disabled=not classify_side,
    )
    dead_zone = st.sidebar.slider(
        "Dead-zone ±°",
        min_value=0.0,
        max_value=10.0,
        value=2.0,
        step=0.5,
        disabled=not classify_side,
    )
    handed = st.sidebar.selectbox(
        "Player handedness",
        options=["Right-handed", "Left-handed"],
        index=0,
        disabled=not classify_side,
    )
    invert = st.sidebar.checkbox(
        "Invert deviation sign",
        value=False,
        disabled=not classify_side,
        help="Use when the launch monitor reports deviation opposite to the desired convention.",
    )

    return {
        "apply_iqr": apply_iqr,
        "iqr_whisker": whisker,
        "iqr_columns": list(default_metrics or []),
        "balance": balance,
        "balance_mode": balance_mode,
        "balance_seed": int(balance_seed),
        "classify_side": classify_side,
        "primary_deviation_col": primary_deviation_col,
        "dead_zone": dead_zone,
        "handed": handed,
        "invert": invert,
    }