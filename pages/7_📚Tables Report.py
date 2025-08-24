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
# Helpers
# =========================
def dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strip spaces from column headers and make duplicates unique with _2, _3, ...
    Also drop all-empty rows/cols.
    """
    if df.empty:
        return df
    clean = [str(c).strip() for c in df.columns]
    counts = {}
    new_cols = []
    for c in clean:
        counts[c] = counts.get(c, 0) + 1
        new_cols.append(c if counts[c] == 1 else f"{c}_{counts[c]}")
    out = df.copy()
    out.columns = new_cols
    out = out.dropna(axis=1, how="all").dropna(axis=0, how="all")
    return out

def to_datetime_if_exists(df: pd.DataFrame, col: str) -> None:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

def table_values(df: pd.DataFrame):
    """
    Convert a DataFrame to a list-of-lists suitable for Plotly Table cells,
    pretty-printing datetimes.
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

# Connect and pull data
client = get_gspread_client()
sheet = client.open("Web_App")

ws_dashboard = sheet.worksheet("Dashboard")
ws_tools     = sheet.worksheet("Sheet1")
ws_forklift  = sheet.worksheet("Forklift")

values_dash = ws_dashboard.get_all_values()
values_tools = ws_tools.get_all_values()
values_forklift = ws_forklift.get_all_values()

# Build DataFrames and sanitize columns
df  = pd.DataFrame(values_dash[1:],  columns=[c.strip() for c in values_dash[0]])
df2 = pd.DataFrame(values_tools[1:], columns=[c.strip() for c in values_tools[0]])
df3 = pd.DataFrame(values_forklift[1:], columns=[c.strip() for c in values_forklift[0]])

df  = dedupe_columns(df)
df2 = dedupe_columns(df2)
df3 = dedupe_columns(df3)

# Parse dates if present
to_datetime_if_exists(df, "Date")
to_datetime_if_exists(df2, "Date")
to_datetime_if_exists(df3, "Date")

# =========================
# ⚒️ Tools Inspection Last Transaction (from Sheet1)
# =========================
st.subheader("⚒️ Tools Inspection — Last Transactions")

# Filters
status_opts = ["All", "Checked", "Broken Down"]
txn_opts = ["All", "Check In", "Check Out"]

status_filter = st.sidebar.selectbox("Filter by Status", status_opts, index=0, key="flt_status")
transaction_filter = st.sidebar.selectbox("Filter by Transaction", txn_opts, index=0, key="flt_txn")
sort_order_tools = st.sidebar.selectbox("Sort order (Tools)", ["Ascending", "Descending"], index=1)

tools_df = df2.copy()

# Defensive: ensure expected columns exist
missing_cols = [c for c in ["Status", "Transaction", "Date"] if c not in tools_df.columns]
if missing_cols:
    st.warning(f"`Sheet1` is missing expected columns: {', '.join(missing_cols)}. Showing raw table.")
    st.dataframe(tools_df, use_container_width=True)
else:
    if status_filter != "All":
        tools_df = tools_df[tools_df["Status"] == status_filter]
    if transaction_filter != "All":
        tools_df = tools_df[tools_df["Transaction"] == transaction_filter]

    tools_df = tools_df.sort_values(by="Date", ascending=(sort_order_tools == "Ascending"))

    # Build Plotly table with colored rows for Broken Down
    # Create per-row color arrays matching the number of rows
    if "Status" in tools_df.columns:
        row_colors = ["red" if v == "Broken Down" else "white" for v in tools_df["Status"]]
        font_colors = ["white" if v == "Broken Down" else "black" for v in tools_df["Status"]]
    else:
        row_colors = ["white"] * len(tools_df)
        font_colors = ["black"] * len(tools_df)

    # Plotly Table expects column-wise lists; for colors we can pass a single list and Plotly will broadcast per column
    table_tools = go.Table(
        header=dict(
            values=list(tools_df.columns),
            fill_color="grey",
            font=dict(color="white", size=16),
            align="left",
        ),
        cells=dict(
            values=table_values(tools_df),
            fill_color=[row_colors],   # broadcast to all columns
            font=dict(color=[font_colors]),
            align="left",
        ),
    )

    fig_tools = go.Figure(data=[table_tools])
    fig_tools.update_layout(height=420, title="⚒️ Tools — Last Transactions")
    st.plotly_chart(fig_tools, use_container_width=True)

st.markdown("---")

# =========================
# 🏎️ Forklift Breakdown Report (from Dashboard)
# =========================
st.subheader("🏎️ Forklift Breakdown Report")

def filter_breakdowns(dfx: pd.DataFrame, sort_col=None, sort_order="asc"):
    if dfx.empty:
        return dfx
    # Keep rows where ANY cell contains "B" (breakdown mark)
    filt = dfx.apply(lambda row: any("B" in str(v) for v in row.values), axis=1)
    out = dfx.loc[filt].copy()
    if sort_col and sort_col in out.columns:
        out = out.sort_values(by=sort_col, ascending=(sort_order == "asc"))
    return out

sort_col_forklift = st.sidebar.selectbox("Sort by (Forklift)", ["", "Date"], index=1)
sort_order_forklift = st.sidebar.selectbox("Sort order (Forklift)", ["asc", "desc"], index=1)

# Defensive: show duplicates if any (debug aid)
# dupes = df.columns[df.columns.duplicated()].tolist()
# st.write("Duplicate cols in Dashboard:", dupes)

forklift_df = filter_breakdowns(df, sort_col=sort_col_forklift or None, sort_order=sort_order_forklift)

if forklift_df.empty:
    st.info("No breakdown rows detected in `Dashboard` (looking for cells that contain 'B').")
else:
    table_forklift = go.Table(
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
    fig_forklift = go.Figure(data=[table_forklift])
    fig_forklift.update_layout(height=420, title="🏎️ Forklift Breakdown Report")
    st.plotly_chart(fig_forklift, use_container_width=True)
