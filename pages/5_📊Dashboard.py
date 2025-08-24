import datetime as dt
import os

import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import streamlit as st

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# Google Sheets via Secrets
# =========================
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    return gspread.authorize(creds)

# =========================
# App
# =========================
st.set_page_config(page_title="Dashboard", layout="centered")
st.title("📊 Dashboard")

# Connect
client = get_gspread_client()
sheet = client.open("Web_App")

# Worksheets
ws_dash = sheet.worksheet("Dashboard")  # metrics (Forklift, Operation, Date, hours, User, …)
ws_raw  = sheet.worksheet("Sheet1")     # optional auxiliary data

# Pull data
values_dash = ws_dash.get_all_values()
values_raw  = ws_raw.get_all_values()

# To DataFrames
df = pd.DataFrame(values_dash[1:], columns=values_dash[0])
df2 = pd.DataFrame(values_raw[1:], columns=values_raw[0])

# Clean empties
df = df.dropna(how="all").copy()
df2 = df2.dropna(how="all").copy()

# -------- Type conversions (robust) --------
# Dates
for col in ["Date"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# Numerics
for col in ["Operation", "hours"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Strings (trim)
for col in ["Forklift", "User"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

# Remove rows missing key fields
required = ["Forklift", "Operation"]
df = df.dropna(subset=[c for c in required if c in df.columns]).copy()

# ---------------- Sidebar selection ----------------
if "Forklift" not in df.columns:
    st.error("The 'Dashboard' worksheet must include a 'Forklift' column.")
    st.stop()

forklift_options = sorted([x for x in df["Forklift"].dropna().unique().tolist() if x != ""])
if not forklift_options:
    st.warning("No forklifts found in data.")
    st.stop()

selected_forklift = st.sidebar.radio("Select a forklift", forklift_options)

# ---------------- KPIs ----------------
# Max operation for selected forklift
if "Operation" not in df.columns:
    st.error("The 'Dashboard' worksheet must include an 'Operation' column.")
    st.stop()

max_operation = df.loc[df["Forklift"] == selected_forklift, "Operation"].max()
if pd.isna(max_operation):
    max_operation = 0

# Service thresholds (example rule)
next_service = 1000 if selected_forklift == "Forklift 1" else 500

remaining_hours = max(0, next_service - float(max_operation))
now = dt.datetime.now()
# Basic heuristic: 24 hours/day utilization → estimate next service date
days_to_next_service = (remaining_hours / 24.0) if remaining_hours > 0 else 0
next_service_date = now + dt.timedelta(days=days_to_next_service)

left_column, middle_column, right_column = st.columns(3)
with left_column:
    st.subheader("Next Service:")
    st.subheader(f"Hours {int(next_service):,}")
with middle_column:
    st.subheader("Remaining Hours:")
    st.subheader(f"{remaining_hours:.1f}")
with right_column:
    st.subheader("Service Progress:")
    st.progress(min(max_operation / next_service, 1.0))

st.caption(f"Estimated next service date: **{next_service_date.date()}**")
st.markdown("""---""")

# ---------------- Gauge ----------------
overall_max = df["Operation"].max() if "Operation" in df.columns else next_service
if pd.isna(overall_max) or overall_max <= 0:
    overall_max = next_service

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=float(max_operation),
    title={'text': "Operation Hours"},
    gauge={
        'axis': {'range': [0, float(overall_max)]},
        'bar': {'color': "darkblue"},
        'steps': [
            {'range': [0, overall_max / 3], 'color': "red"},
            {'range': [overall_max / 3, overall_max * 2 / 3], 'color': "orange"},
            {'range': [overall_max * 2 / 3, overall_max], 'color': "green"}
        ],
        'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': float(overall_max)}
    }
))
st.plotly_chart(fig_gauge, use_container_width=True)

# ---------------- Time-series views ----------------
df_f = df.loc[df["Forklift"] == selected_forklift].copy()

if "Date" in df_f.columns and "hours" in df_f.columns:
    # Ensure sorted by date
    df_f = df_f.sort_values("Date")
    # Line chart (daily)
    fig_line = go.Figure(data=go.Scatter(
        x=df_f["Date"], y=df_f["hours"], mode="lines", name="Daily Hours"
    ))
    fig_line.update_layout(title="Forklift Hours over Time", xaxis_title="Date", yaxis_title="Hours")

    # Year-Month aggregation
    df_f["Year-Month"] = df_f["Date"].dt.strftime("%Y-%m")
    df_sum = df_f.groupby("Year-Month", as_index=False)["hours"].sum()
    df_mean = df_f.groupby("Year-Month", as_index=False)["hours"].mean()

    fig_y_m = go.Figure()
    fig_y_m.add_trace(go.Bar(x=df_sum["Year-Month"], y=df_sum["hours"], name="Sum of Hours"))
    fig_y_m.add_trace(go.Scatter(x=df_mean["Year-Month"], y=df_mean["hours"], mode="lines", name="Avg Daily Hours"))
    fig_y_m.update_layout(title="Hours by Year-Month", xaxis_title="Year-Month", yaxis_title="Hours")

    view_type = st.radio("Select a view", ("Year-Month", "Daily Hours"), horizontal=True)
    st.plotly_chart(fig_y_m if view_type == "Year-Month" else fig_line, use_container_width=True)
else:
    st.info("Time-series not shown (need 'Date' and 'hours' columns).")

# ---------------- User distribution pie ----------------
if "User" in df.columns:
    user_count = df["User"].value_counts(dropna=True)
    if len(user_count) > 0:
        fig_pie = px.pie(names=user_count.index, values=user_count.values, title="User Distribution")
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No user data to display.")
else:
    st.info("Column 'User' not found for distribution chart.")

# ---------------- Component inspections (stacked) ----------------
components = [c for c in ["Brake Inspection", "Engine", "Lights", "Tires"] if c in df.columns]
if components and "User" in df.columns:
    fig_stack = go.Figure()
    for comp in components:
        # coerce to numeric; missing → 0
        yvals = pd.to_numeric(df[comp], errors="coerce").fillna(0)
        fig_stack.add_trace(go.Bar(name=comp, x=df["User"], y=yvals))
    fig_stack.update_layout(
        title="Inspections by Component and User",
        xaxis_title="User",
        yaxis_title="Number of Inspections",
        barmode="stack"
    )
    st.plotly_chart(fig_stack, use_container_width=True)
else:
    st.info("Component columns not found (need any of: Brake Inspection, Engine, Lights, Tires).")

# Optional: preview auxiliary sheet
# st.write(df2.head())
