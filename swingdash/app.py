import pandas as pd
import streamlit as st

from config import KEY_METRICS  # keep your config central if you like
from analytics import describe_session, compare_sessions, balance_samples, kpi_series_for_metrics
from cleaning import preprocess, iqr_filter
from ui import render_table, render_kpi_tiles
import plots 

st.set_page_config(page_title="Swing Progress Dashboard", layout="wide")
st.title("Swing Progress Dashboard")

# --- Uploads
c1, c2 = st.columns(2)
with c1: f_old = st.file_uploader("Upload OLD session CSV", type=["csv"], key="old")
with c2: f_new = st.file_uploader("Upload NEW session CSV", type=["csv"], key="new")
if not f_old or not f_new:
    st.info("Upload two CSVs to begin.")
    st.stop()

old_raw, new_raw = pd.read_csv(f_old), pd.read_csv(f_new)
old, new = preprocess(old_raw, "Old"), preprocess(new_raw, "New")

# --- Sidebar filters (players, clubs, iqr, etc.) — same as before but ONLY filtering here ---
st.sidebar.header("Filters")
players = sorted(set(old.get("Player", pd.Series()).dropna()).union(new.get("Player", pd.Series()).dropna()))
clubs   = sorted(set(old.get("Club Type", pd.Series()).dropna()).union(new.get("Club Type", pd.Series()).dropna()))
sel_players = st.sidebar.multiselect("Player", players, default=players)
sel_clubs   = st.sidebar.multiselect("Club Type", clubs, default=clubs)
apply_iqr   = st.sidebar.checkbox("Apply IQR filter (3× IQR)", True)

def _apply_filters(df):
    if sel_players and "Player" in df.columns:
        df = df[df["Player"].isin(sel_players)]
    if sel_clubs and "Club Type" in df.columns:
        df = df[df["Club Type"].isin(sel_clubs)]
    return df

old_f, new_f = _apply_filters(old), _apply_filters(new)
if apply_iqr:
    iqr_cols = [c for c in ["Club Speed","Ball Speed","Smash Factor","Spin Rate","Carry Distance","Total Distance","|Carry Dev|","|Total Dev|"] if c in old_f.columns]
    old_f, new_f = iqr_filter(old_f, iqr_cols), iqr_filter(new_f, iqr_cols)

# --- Balancing
st.sidebar.header("Sample-size standardisation")
std_enable = st.sidebar.checkbox("Standardise shot counts", False)
std_mode   = st.sidebar.selectbox("Mode", ["Simple", "Stratified: Club Type + Side"], 1)
std_seed   = st.sidebar.number_input("Random seed", value=42, step=1)
old_b, new_b = balance_samples(old_f, new_f, std_enable, std_mode, int(std_seed))

# --- Counts
cA, cB, cC = st.columns(3)
with cA: st.metric("Old (filtered)", value=f"{len(old_f):,}")
with cB: st.metric("New (filtered)", value=f"{len(new_f):,}")
with cC: st.metric("Used in analysis", value=f"{len(old_b):,} vs {len(new_b):,}")

# --- Descriptives + KPI table/tiles
old_desc = describe_session(old_b, KEY_METRICS)
new_desc = describe_session(new_b, KEY_METRICS)

# KPIs to show (you can import from config)
kpi_list = ["Club Speed","Ball Speed","Smash Factor","Carry Distance"]
acc = "|Total Dev|" if "|Total Dev|" in old_b.columns and "|Total Dev|" in new_b.columns else ("|Carry Dev|" if "|Carry Dev|" in old_b.columns and "|Carry Dev|" in new_b.columns else None)
if acc: kpi_list.append(acc)

kpi_map = kpi_series_for_metrics(old_desc, new_desc, kpi_list)
st.subheader("Session KPIs")
render_kpi_tiles(kpi_map, max_cols=5)

# --- Comparison table
delta = compare_sessions(old_desc, new_desc)
if not delta.empty:
    render_table("Session comparison", delta.rename(columns={
        "mean_old":"Old mean","mean_new":"New mean","delta":"Δ mean","pct_change":"% change","improvement_sign":"Improved?"
    }), height=360)
else:
    st.info("Not enough overlapping metrics to compute deltas.")

# --- Plot tabs (figures from plots.py)
st.subheader("Interactive charts")
tabs = st.tabs(["Scatter","Histograms","Boxplots","Shot table","Groups","Left/Right"])
combined = pd.concat([old_b.assign(Session="Old"), new_b.assign(Session="New")], ignore_index=True)

with tabs[0]:
    metric_opts = [m for m in KEY_METRICS if m in combined.columns]
    if len(metric_opts) >= 2:
        cX, cY, cC = st.columns(3)
        with cX: x = st.selectbox("X-axis", metric_opts, 0)
        with cY: y = st.selectbox("Y-axis", metric_opts, 1)
        with cC: colour = st.selectbox("Colour by", [c for c in ["Session","Group","Side"] if c in combined.columns], 0)
        fig = plots.scatter(combined, x=x, y=y, color_by=colour,
                            hover_cols=["Date_parsed","Player","Club Type","Club Name","Group","Side"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select CSVs with more numeric metrics to plot scatter.")

with tabs[1]:
    if metric_opts:
        metric_hist = st.selectbox("Histogram metric", metric_opts, 0, key="hist")
        bins = st.slider("Bins", 10, 80, 30, 5)
        st.plotly_chart(plots.histogram(combined, metric_hist, bins=bins), use_container_width=True)

with tabs[2]:
    acc_col = "|Total Dev|" if "|Total Dev|" in combined.columns else ("|Carry Dev|" if "|Carry Dev|" in combined.columns else None)
    if acc_col:
        st.plotly_chart(plots.box_deviation(combined, acc_col, ytitle=f"{acc_col} (distance units)"), use_container_width=True)
    else:
        st.info("No deviation columns for boxplot.")

with tabs[3]:
    show_cols = [c for c in ["Session","Date_parsed","Player","Club Type","Club Name","Club Speed","Ball Speed","Smash Factor","Launch Angle","Spin Rate","Carry Distance","Total Distance","Side","Group","|Carry Dev|","|Total Dev|"] if c in combined.columns]
    render_table("Balanced shots (first 1,000 rows)", combined[show_cols].head(1000), height=420) if show_cols else st.info("No columns to show.")

with tabs[4]:
    if "Group" in combined.columns:
        cnt = (combined.pivot_table(index="Group", columns="Session", values=combined.columns[0], aggfunc="count").fillna(0).astype(int)
               .reset_index().rename_axis(None, axis=1))
        render_table("Group counts", cnt, height=220)
        y_metric = st.selectbox("Group boxplot metric", [m for m in ["Carry Distance","Total Distance","|Carry Dev|","|Total Dev|"] if m in combined.columns], 0)
        st.plotly_chart(plots.group_box(combined, y_metric), use_container_width=True)
    else:
        st.info("Enable rule-based grouping if you want this tab.")

with tabs[5]:
    if "Side" in combined.columns:
        cnt = (combined.groupby(["Session","Side"]).size().reset_index(name="Count"))
        st.plotly_chart(plots.bar_side_counts(cnt), use_container_width=True)
        if {"Club Face","Club Path"}.issubset(combined.columns):
            st.plotly_chart(plots.scatter_face_vs_path(combined), use_container_width=True)
        metric = st.selectbox("Box metric", [c for c in ["Club Face","Club Path","Face to Path","Attack Angle","Spin Axis"] if c in combined.columns], 2)
        st.plotly_chart(plots.box_by_side(combined, metric), use_container_width=True)
    else:
        st.info("No 'Side' column available.")