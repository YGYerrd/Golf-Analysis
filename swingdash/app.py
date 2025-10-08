"""Streamlit application for analysing and comparing golf sessions."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Mapping

import pandas as pd
import streamlit as st

from .analytics import compare_sessions, describe_session
from .cleaning import add_side_column, iqr_filter, load_csv, preprocess
from .config import KEY_METRICS
from .plots import (
    make_comparison_table,
    make_session_summary_table,
    make_shot_count_table,
    make_shot_table,
    render_table,
)
from .standardise import balance_samples
from .ui import (
    SessionSelection,
    render_app_header,
    render_sidebar_filters,
    render_sidebar_session_inputs,
)

SHOT_TABLE_METRICS = [
    "Club Speed",
    "Ball Speed",
    "Launch Angle",
    "Spin Rate",
    "Carry Distance",
    "Total Distance",
    "Carry Deviation Distance",
    "Total Deviation Distance",
    "|Carry Dev|",
    "|Total Dev|",
]


def _discover_default_sessions() -> Mapping[str, Path]:
    """Return a mapping of friendly labels to CSV file paths bundled with the repo."""

    repo_root = Path(__file__).resolve().parents[1]
    candidate_dirs = [repo_root, repo_root / "data", repo_root / "datasets"]
    sessions: "OrderedDict[str, Path]" = OrderedDict()
    for directory in candidate_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.csv")):
            label = path.stem
            suffix = 1
            unique_label = label
            while unique_label in sessions:
                suffix += 1
                unique_label = f"{label} ({suffix})"
            sessions[unique_label] = path
    return sessions


def _load_session(selection: SessionSelection) -> pd.DataFrame:
    """Load and preprocess a session given the user's selection."""

    if selection.source is None:
        return pd.DataFrame()

    if isinstance(selection.source, Path):
        raw = load_csv(str(selection.source))
    else:
        uploaded = selection.source
        if hasattr(uploaded, "seek"):
            uploaded.seek(0)
        raw = pd.read_csv(uploaded, encoding="utf-8-sig")
    label = selection.label or "Session"
    return preprocess(raw, label)


def _apply_processing(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    processed = df.copy()
    if processed.empty:
        return processed

    if config.get("classify_side"):
        processed = add_side_column(
            processed,
            config.get("primary_deviation_col", "Carry Deviation Angle"),
            config.get("dead_zone", 2.0),
            config.get("handed", "Right-handed"),
            config.get("invert", False),
        )

    if config.get("apply_iqr"):
        cols = config.get("iqr_columns") or KEY_METRICS
        processed = iqr_filter(processed, cols, whisker=config.get("iqr_whisker", 3.0))
    return processed


def _summarise_sessions(
    old_df: pd.DataFrame,
    new_df: pd.DataFrame,
    *,
    config: dict,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Return processed, balanced, and descriptive statistics for both sessions."""

    old_processed = _apply_processing(old_df, config)
    new_processed = _apply_processing(new_df, config)

    balanced_old, balanced_new = balance_samples(
        old_processed,
        new_processed,
        config.get("balance", False),
        config.get("balance_mode", "Simple"),
        config.get("balance_seed", 42),
    )

    old_desc = describe_session(balanced_old)
    new_desc = describe_session(balanced_new)
    comparison = compare_sessions(old_desc, new_desc)

    return (
        old_processed,
        new_processed,
        balanced_old,
        balanced_new,
        old_desc,
        new_desc,
        comparison,
    )


def _render_results(
    selections: Mapping[str, SessionSelection],
    *,
    raw_old: pd.DataFrame,
    raw_new: pd.DataFrame,
    old_processed: pd.DataFrame,
    new_processed: pd.DataFrame,
    balanced_old: pd.DataFrame,
    balanced_new: pd.DataFrame,
    old_desc: pd.DataFrame,
    new_desc: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    baseline_label = selections["baseline"].label or "Baseline"
    comparison_label = selections["comparison"].label or "Comparison"

    counts_table = make_shot_count_table(
        old_label=baseline_label,
        new_label=comparison_label,
        raw_old=len(raw_old),
        raw_new=len(raw_new),
        processed_old=len(old_processed),
        processed_new=len(new_processed),
        balanced_old=len(balanced_old),
        balanced_new=len(balanced_new),
    )
    render_table("Shot counts", counts_table)

    col1, col2 = st.columns(2)
    with col1:
        render_table(
            f"{baseline_label} summary",
            make_session_summary_table(old_desc),
        )
    with col2:
        render_table(
            f"{comparison_label} summary",
            make_session_summary_table(new_desc),
        )

    render_table(
        "Session comparison",
        make_comparison_table(
            comparison,
            old_label=baseline_label,
            new_label=comparison_label,
        ),
    )

    combined = pd.concat([balanced_old, balanced_new], ignore_index=True)
    shot_table = make_shot_table(combined, metrics=SHOT_TABLE_METRICS, limit=1000)
    render_table("Balanced shots (first 1,000 rows)", shot_table, height=420)
    st.caption(
        "Use the sidebar to adjust filters. Only the first 1,000 balanced shots are shown "
        "for performance reasons."
    )


def run() -> None:
    """Entry-point for Streamlit."""

    st.set_page_config(page_title="SwingDash", page_icon="🏌️", layout="wide")
    render_app_header()

    available_sessions = _discover_default_sessions()
    selections = render_sidebar_session_inputs(available_sessions)
    config = render_sidebar_filters(KEY_METRICS)

    raw_baseline = _load_session(selections["baseline"])
    raw_comparison = _load_session(selections["comparison"])

    if raw_baseline.empty or raw_comparison.empty:
        st.info("Select or upload two sessions to begin the analysis.")
        return

    (
        processed_baseline,
        processed_comparison,
        balanced_baseline,
        balanced_comparison,
        baseline_desc,
        comparison_desc,
        comparison,
    ) = _summarise_sessions(
        raw_baseline,
        raw_comparison,
        config=config,
    )

    if processed_baseline.empty:
        st.warning(f"No data remains for {selections['baseline'].label} after applying the filters.")
        return
    if processed_comparison.empty:
        st.warning(
            f"No data remains for {selections['comparison'].label} after applying the filters."
        )
        return

    _render_results(
        selections,
        raw_old=raw_baseline,
        raw_new=raw_comparison,
        old_processed=processed_baseline,
        new_processed=processed_comparison,
        balanced_old=balanced_baseline,
        balanced_new=balanced_comparison,
        old_desc=baseline_desc,
        new_desc=comparison_desc,
        comparison=comparison,
    )


if __name__ == "__main__":  # pragma: no cover
    run()