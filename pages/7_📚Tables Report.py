import pandas as pd
import plotly.graph_objs as go
import streamlit as st
import plotly.express as px

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
# Load Data
# =========================
st.set_page_config(page_title="Tables Report", layout="wide")
st.title("📚 Tables Report")

client = get_gspread_client()
sheet = client.open("Web_App")

ws_dashboard = sheet.worksheet("Dashboard")
ws_tools = sheet.worksheet("Sheet1")
ws_forklift = sheet.worksheet("Forklift")

# Pull values
values_dash = ws_dashboard.get_all_values()
values_tools = ws_tools.get_all_values()
values_forklift = ws_forklift.get_all_values()

# DataFrames
df = pd.DataFrame(values_dash[1:], columns=values_dash[0])
df2 = pd.DataFrame(values_tools[1:], columns=values_tools[0])
df3 = pd.DataFrame(values_forklift[1:], columns=values_forklift[0])

# Drop empties
df = df.dropna(how="all")
df2 = df2.dropna(how="all")
df3 = df3.dropna(how="all")

# Convert types
for col in ["Date"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    if col in df2.columns:
        df2[col] = pd.to_datetime(df2[col], errors="coerce")
    if col in df3.columns:
        df3[col] = pd.to_datetime(df3[col], errors="coerce")

# ================
# Tools Inspection Report (last transactions)
# ================
st.subheader("⚒️ Tools Inspection Last Transaction")

status_filter = st.sidebar.selectbox("Filter by Status", ["All", "Checked", "Broken Down"])
transaction_filter = st.sidebar.selectbox("Filter by Transaction", ["All", "Check In", "Check Out"])
sort_order_tools = st.sidebar.selectbox("Sort order (Tools)", ["Ascending", "Descending"])

df_tools_filtered = df2.copy()

if status_filter != "All":
    df_tools_filtered = df_tools_filtered[df_tools_filtered["Status"] == status_filter]
if transaction_filter != "All":
    df_tools_filtered = df_tools_filtered[df_tools_filtered["Transaction"] == transaction_filter]

if sort_order_tools == "Ascending":
    df_tools_filtered = df_tools_filtered.sort_values(by="Date", ascending=True)
else:
    df_tools_filtered = df_tools_filtered.sort_values(by="Date", ascending=False)

# Create table
table_tools = go.Table(
    header=dict(
        values=list(df_tools_filtered.columns),
        fill_color="grey",
        font=dict(color="white", size=16),
        align="left"
    ),
    cells=dict(
        values=[df_tools_filtered[col] for col in df_tools_filtered.columns],
        fill_color=[["red" if v == "Broken Down" else "white" for v in df_tools_filtered["Status"]]],
        font=dict(color=[["white" if v == "Broken Down" else "black" for v in df_tools_filtered["Status"]]]),
        align="left"
    )
)
fig_tools = go.Figure(data=[table_tools])
fig_tools.update_layout(height=400, title="⚒️ Tools Inspection Last Transaction")
st.plotly_chart(fig_tools, use_container_width=True)

# ================
# Forklift Breakdown Report
# ================
st.subheader("🏎️ Forklift Breakdown Report")

def filter_breakdowns(df, sort_col=None, sort_order="asc"):
    # Keep rows where any value contains "B" (breakdown marker)
    filtered = df[df.apply(lambda row: any("B" in str(v) for v in row.values), axis=1)]
    if sort_col and sort_col in filtered.columns:
        filtered = filtered.sort_values(by=sort_col, ascending=(sort_order == "asc"))
    return filtered

sort_col_forklift = st.sidebar.selectbox("Sort by (Forklift)", ["", "Date"])
sort_order_forklift = st.sidebar.selectbox("Sort order (Forklift)", ["asc", "desc"])

df_breakdowns = filter_breakdowns(df, sort_col=sort_col_forklift, sort_order=sort_order_forklift)

table_forklift = go.Table(
    header=dict(
        values=list(df_breakdowns.columns),
        fill_color="grey",
        font=dict(color="white", size=14),
        align="left"
    ),
    cells=dict(
        values=[df_breakdowns[col] for col in df_breakdowns.columns],
        fill_color="white",
        font=dict(color="black", size=12),
        align="left"
    )
)
fig_forklift = go.Figure(data=[table_forklift])
fig_forklift.update_layout(height=400, title="🏎️ Forklift Breakdown Report")
st.plotly_chart(fig_forklift, use_container_width=True)
