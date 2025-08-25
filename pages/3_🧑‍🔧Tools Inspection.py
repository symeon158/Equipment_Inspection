import os
import datetime
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Email (optional)
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# =========================
# Page config
# =========================
st.set_page_config(page_title="Tools / Equipment Inspection", layout="centered")
st.title("🧑‍🔧 Tools / Equipment Inspection")

if os.path.exists("Tools.png"):
    st.image(Image.open("Tools.png"))

now = datetime.datetime.now()
date_string = now.strftime("%Y-%m-%d %H:%M:%S")


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

def load_tools_df(ws) -> pd.DataFrame:
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=[
            "DateTime","Date","User","Equipment","Equipment_Selected","Transaction","Status","Comments"
        ])
    df = pd.DataFrame(values[1:], columns=values[0])

    # Normalize column names exactly as expected
    expected = ["DateTime","Date","User","Equipment","Equipment_Selected","Transaction","Status","Comments"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        st.error(f"Missing expected columns in Sheet1: {missing}")
        st.stop()

    # Normalize string fields (trim spaces)
    for col in ["User","Equipment","Equipment_Selected","Transaction","Status","Comments"]:
        df[col] = df[col].astype(str).str.strip()

    # Parse DateTime (use for latest); tolerate different formats
    df["DateTime"] = pd.to_datetime(df["DateTime"], errors="coerce", infer_datetime_format=True)

    # Parse Date if present
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    return df

# ---------- DEBUG: show last transaction per Equipment_Selected ----------

def compute_last_by_equipment(df: pd.DataFrame) -> pd.DataFrame:
    # Clean strings
    for c in ["Equipment_Selected", "User", "Transaction", "Status", "Comments"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # Keep an original row order to break ties
    df = df.copy()
    df["_row"] = range(len(df))

    # Parse DateTime (robust)
    if "DateTime" in df.columns:
        df["_dt"] = pd.to_datetime(df["DateTime"], errors="coerce", infer_datetime_format=True)
    else:
        # If the column is missing (shouldn't be), create a NaT column
        df["_dt"] = pd.NaT

    # Normalized equipment key
    df["_equip"] = df["Equipment_Selected"].astype(str).str.strip()

    # Sort by equipment, then parsed datetime, then original order
    df_sorted = df.sort_values(["_equip", "_dt", "_row"], ascending=[True, True, True])

    # Take the last row per equipment
    last_by_equipment = df_sorted.dropna(subset=["_equip"]).drop_duplicates(subset=["_equip"], keep="last")

    return last_by_equipment

last_by_equipment = compute_last_by_equipment(df)

st.subheader("🔎 Last transaction per Equipment_Selected")
cols_display = [c for c in [
    "Equipment_Selected", "DateTime", "User", "Transaction", "Status", "Comments"
] if c in last_by_equipment.columns]
st.dataframe(last_by_equipment[cols_display].reset_index(drop=True))


def send_email(to, subject, message, image_file=None, image_file_2=None):
    cfg = st.secrets.get("email", {})
    from_address = cfg.get("user")
    password = cfg.get("app_password")
    if not (from_address and password and to):
        return
    host = cfg.get("smtp_host", "smtp.gmail.com")
    port_tls = int(cfg.get("smtp_port", 587))

    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    for path, fname in [(image_file, "picture.jpg"), (image_file_2, "signature.png")]:
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
                img.add_header("Content-Disposition", "attachment", filename=fname)
                msg.attach(img)

    try:
        server = smtplib.SMTP(host, port_tls, timeout=20)
        server.starttls()
        server.login(from_address, password)
        server.sendmail(from_address, [to], msg.as_string())
        server.quit()
    except Exception:
        server = smtplib.SMTP_SSL(host, 465, timeout=20)
        server.login(from_address, password)
        server.sendmail(from_address, [to], msg.as_string())
        server.quit()


# =========================
# Catalog (adjust if needed)
# =========================
equipments = [
    "", "Welding_Inverter", "Angle_Grinder_F180", "Angle_Grinder_F125", "POINT_4-KILL",
    "Hammer_Drills", "Rotary_Hammer_Drill", "Makita_Drill", "BLOWER", "Water_Pump",
    "Jigsaw", "Roter_Trypio", "MPALANTEZA", "WORLD_HEATING_AIR_DW_IT_2000W",
    "Circular_Saw", "Power_Strip"
]
employee_names = ["Please Select", "Alexandridis Christos", "Ntamaris Nikolaos", "Papadopoulos Symeon"]
transactions = ["Check In", "Check Out"]
statuses = ["Checked", "Broken Down"]


# =========================
# Helpers
# =========================
def latest_row_for_equipment(df: pd.DataFrame, equip_selected: str) -> pd.Series | None:
    """Get latest row by DateTime for a given Equipment_Selected; if all DateTime NaT, use last physical row."""
    if not equip_selected:
        return None
    equip_selected = str(equip_selected).strip()
    df_sel = df[df["Equipment_Selected"].astype(str).str.strip() == equip_selected]
    if df_sel.empty:
        return None

    # Prefer rows with valid DateTime
    df_valid = df_sel[df_sel["DateTime"].notna()]
    if not df_valid.empty:
        return df_valid.sort_values("DateTime").iloc[-1]

    # Fallback: use last physical row entered
    return df_sel.iloc[-1]


# =========================
# Form (auto clears)
# =========================
with st.form("tools_form", clear_on_submit=True):
    date = st.date_input("Date", datetime.date.today())
    user = st.selectbox("User", employee_names, index=0)

    c1, c2 = st.columns([1, 2])
    equipment = c1.selectbox("Equipment", equipments, index=0)
    selected_equipment = c2.text_input("Equipment_Selected (or scan result)", value=(equipment or "")).strip()

    transaction = st.selectbox("Transaction", ["Please Select"] + transactions, index=0)
    status = st.selectbox("Status", ["Please Select"] + statuses, index=0)
    comments = st.text_area("Comments (required if Broken Down)", max_chars=120, height=60)

    # Optional media
    picture = st.camera_input("Take a Photo (optional)")
    signature_canvas = st_canvas(
        fill_color="rgba(255,165,0,0.3)",
        stroke_width=5,
        stroke_color="rgb(0,0,0)",
        background_color="rgba(255,255,255,1)",
        height=150,
        drawing_mode="freedraw",
        key="canvas_tools",
    )

    # --- SAFETY VALVE LOOKUP (reads Web_App -> Sheet1) ---
    client = get_gspread_client()
    sheet = client.open("Web_App")
    ws_tools = sheet.worksheet("Sheet1")  # <-- your worksheet
    df = load_tools_df(ws_tools)

    last = latest_row_for_equipment(df, selected_equipment)
    is_blocked = False
    blocked_reason = ""
    
    if selected_equipment and last is not None:
        last_status = str(last["Status"]).strip().lower() if "Status" in last else None
        last_dt_display = str(last["DateTime"]) if "DateTime" in last else "unknown time"
    
        if last_status == "broken down" and transaction == "Check Out":
            is_blocked = True
            blocked_reason = (
                f"🚫 **Safety Valve**: **{selected_equipment}** is currently **Broken Down** "
                f"(last update: {last_dt_display}).\n\n"
                "You cannot **Check Out** this equipment.\n\n"
                "✅ Please choose **another equipment**, or **after repair**, "
                "submit a **Check In** for this item with **Status = Checked** to mark it fixed."
            )


    # Last transaction preview
    if last is not None:
        with st.expander("🔎 Last transaction for this equipment"):
            preview_cols = [c for c in ["DateTime","User","Equipment_Selected","Transaction","Status","Comments"] if c in df.columns]
            st.table(pd.DataFrame([last[preview_cols]]) if preview_cols else pd.DataFrame([last]))

    if is_blocked:
        st.error(blocked_reason)

    submitted = st.form_submit_button("Submit", disabled=is_blocked)


# =========================
# Handle submission
# =========================
if submitted:
    # Validation
    if (
        user == "Please Select" or
        transaction == "Please Select" or
        status == "Please Select" or
        not selected_equipment
    ):
        st.warning("Please complete all required fields (User, Equipment_Selected, Transaction, Status).")
        st.stop()
    if status == "Broken Down" and not comments.strip():
        st.warning("Please provide comments for the breakdown.")
        st.stop()

    # Re-check safety at submit time
    df = load_tools_df(ws_tools)
    last = latest_row_for_equipment(df, selected_equipment)
    last_status = (str(last["Status"]).strip() if last is not None and "Status" in last else None)
    if last_status and last_status.lower() == "broken down" and transaction == "Check Out":
        st.error(
            f"Safety Valve: **{selected_equipment}** cannot be **Checked Out** because the last status is **Broken Down**.\n\n"
            "Please choose another item or, after repair, **Check In** this equipment with **Status = Checked**."
        )
        st.stop()

    # Save media to /tmp now
    picture_path = None
    if picture is not None:
        picture_path = "/tmp/picture.jpg"
        with open(picture_path, "wb") as f:
            f.write(picture.getbuffer())

    signature_path = None
    if signature_canvas.image_data is not None:
        img = Image.fromarray(signature_canvas.image_data.astype("uint8"), "RGBA")
        signature_path = "/tmp/signature.png"
        img.save(signature_path)

    # Build record EXACTLY as your schema
    record = {
        "DateTime": date_string,           # full timestamp
        "Date": date.isoformat(),          # date only
        "User": user,
        "Equipment": equipment,
        "Equipment_Selected": selected_equipment,
        "Transaction": transaction,
        "Status": status,
        "Comments": comments,
    }
    out_df = pd.DataFrame([record])

    # Append to Google Sheet
    if not ws_tools.row_values(1):
        ws_tools.append_rows([out_df.columns.tolist()] + out_df.values.tolist())
    else:
        ws_tools.append_rows(out_df.values.tolist())

    # Optional email when a broken item is recorded
    if status == "Broken Down":
        to_addr = st.secrets.get("email", {}).get("to_alert", st.secrets.get("email", {}).get("user"))
        if to_addr:
            subject = f"Equipment Broken Down: {selected_equipment}"
            message = (
                f"Equipment {selected_equipment} reported Broken Down by {user}.\n\n"
                f"Record:\n{out_df.to_string(index=False)}"
            )
            send_email(to=to_addr, subject=subject, message=message, image_file=picture_path, image_file_2=signature_path)

    st.success("Form submitted successfully! (Form has been cleared.)")


