import pandas as pd
import plotly.graph_objs as go
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
# Helpers
# =========================
def dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strip spaces in headers, make duplicates unique with _2, _3, ...
    Drop fully empty rows/cols.
    """
    if df.empty:
        return df
    base = [str(c).strip() for c in df.columns]
    seen = {}
    new_cols = []
    for c in base:
        seen[c] = seen.get(c, 0) + 1
        new_cols.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
    out = df.copy()
    out.columns = new_cols
    out = out.dropna(axis=1, how="all").dropna(axis=0, how="all")
    return out

def to_datetime_if_exists(df: pd.DataFrame, col: str) -> None:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

def table_values(df: pd.DataFrame):
    """
    For Plotly Table: list-of-lists (columns), pretty-print datetimes.
    """
    vals = []
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            s = s.dt.strftime("%Y-%m-%d %H:%M").fillna("")
        vals.append(s.astype(str).tolist())
    return vals

# =========================
# App
# =========================
st.set_page_config(page_title="Tables Report", layout="wide")
st.title("📚 Tables Report")

client = get_gspread_client()
sheet = client.open("Web_App")

ws_dashboard = sheet.worksheet("Dashboard")   # Forklift log (contains 'B' markers)
ws_tools     = sheet.worksheet("Sheet1")      # Tools transactions (your columns)
ws_forklift  = sheet.worksheet("Forklift")    # Not used below, but kept if you need later

# Pull values
values_dash   = ws_dashboard.get_all_values()
values_tools  = ws_tools.get_all_values()
values_fork   = ws_forklift.get_all_values()

# Build DataFrames + dedupe
df_dash  = pd.DataFrame(values_dash[1:],  columns=[c.strip() for c in values_dash[0]])
df_tools = pd.DataFrame(values_tools[1:], columns=[c.strip() for c in values_tools[0]])
df_fork  = pd.DataFrame(values_fork[1:],  columns=[c.strip() for c in values_fork[0]])

df_dash  = dedupe_columns(df_dash)
df_tools = dedupe_columns(df_tools)
df_fork  = dedupe_columns(df_fork)

# Convert Date columns where present
to_datetime_if_exists(df_dash,  "Date")
to_datetime_if_exists(df_tools, "Date")
to_datetime_if_exists(df_fork,  "Date")

# =========================================================
# ⚒️ Tools Inspection — Last Transactions (from Sheet1)
# Columns you reported: Status, Date, User, Equipment, Equipment_Selected, Transaction, Status, Comments
# After dedupe => Status, Date, User, Equipment, Equipment_Selected, Transaction, Status_2, Comments
# We'll use Status_2 if it exists; else fallback to Status.
# =========================================================
st.subheader("⚒️ Tools Inspection — Last Transactions")

status_col = "Status_2" if "Status_2" in df_tools.columns else ("Status" if "Status" in df_tools.columns else None)
txn_col    = "Transaction" if "Transaction" in df_tools.columns else None
date_col   = "Date" if "Date" in df_tools.columns else None

# Sidebar filters
status_opts = ["All"]
if status_col:
    status_opts += sorted([s for s in df_tools[status_col].dropna().unique().tolist() if s != ""])

txn_opts = ["All"]
if txn_col:
    txn_opts += sorted([t for t in df_tools[txn_col].dropna().unique().tolist() if t != ""])

status_filter = st.sidebar.selectbox("Filter by Status", status_opts, index=0, key="flt_status")
transaction_filter = st.sidebar.selectbox("Filter by Transaction", txn_opts, index=0, key="flt_txn")
sort_order_tools = st.sidebar.selectbox("Sort order (Tools)", ["Ascending", "Descending"], index=1)

tools_df = df_tools.copy()

# Apply filters if columns exist
if status_col and status_filter != "All":
    tools_df = tools_df[tools_df[status_col] == status_filter]
if txn_col and transaction_filter != "All":
    tools_df = tools_df[tools_df[txn_col] == transaction_filter]

# Sort by Date if present
if date_col:
    tools_df = tools_df.sort_values(by=date_col, ascending=(sort_order_tools == "Ascending"))

# Color rows red when "Broken Down" in status_col (if present)
if status_col and status_col in tools_df.columns:
    row_colors = ["red" if v == "Broken Down" else "white" for v in tools_df[status_col]]
    font_colors = ["white" if v == "Broken Down" else "black" for v in tools_df[status_col]]
else:
    row_colors = ["white"] * len(tools_df)
    font_colors = ["black"] * len(tools_df)

table_tools = go.Table(
    header=dict(
        values=list(tools_df.columns),
        fill_color="grey",
        font=dict(color="white", size=16),
        align="left",
    ),
    cells=dict(
        values=table_values(tools_df),
        fill_color=[row_colors],          # broadcast row colors to all columns
        font=dict(color=[font_colors]),   # broadcast font colors to all columns
        align="left",
    ),
)
fig_tools = go.Figure(data=[table_tools])
fig_tools.update_layout(height=420, title="⚒️ Tools — Last Transactions (Sheet1)")
st.plotly_chart(fig_tools, use_container_width=True)

st.markdown("---")

# =========================================================
# 🏎️ Forklift Breakdown Report (from Dashboard)
# We detect rows where ANY cell contains 'B'
# =========================================================
st.subheader("🏎️ Forklift Breakdown Report")

def filter_breakdowns(dfx: pd.DataFrame, sort_col=None, sort_order="asc"):
    if dfx.empty:
        return dfx
    mask = dfx.apply(lambda row: any("B" in str(v) for v in row.values), axis=1)
    out = dfx.loc[mask].copy()
    if sort_col and sort_col in out.columns:
        out = out.sort_values(by=sort_col, ascending=(sort_order == "asc"))
    return out

sort_col_forklift = st.sidebar.selectbox("Sort by (Forklift)", ["", "Date"], index=1)
sort_order_forklift = st.sidebar.selectbox("Sort order (Forklift)", ["asc", "desc"], index=1)

forklift_df = filter_breakdowns(df_dash, sort_col=sort_col_forklift or None, sort_order=sort_order_forklift)

if forklift_df.empty:
    st.info("No breakdown rows detected in `Dashboard` (looking for cells that contain 'B').")
else:
    table_f = go.Table(
        header=dict(
            values=list(forklift_df.columns),
            fill_color="grey",
            font=dict(color="white", size=14),
            align="left",
        ),
        cells=dict(
            values=table_values(forklift_df),
            fill_color="white",
            font=dict(color="black", size=12),
            align="left",
        ),
    )
    fig_f = go.Figure(data=[table_f])
    fig_f.update_layout(height=420, title="🏎️ Forklift Breakdown Report (Dashboard)")
    st.plotly_chart(fig_f, use_container_width=True)
