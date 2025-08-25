import os
import datetime
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gspread_dataframe as gsdf

# Email (optional alert when broken items submitted)
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# =========================
# Page config
# =========================
st.set_page_config(page_title="Tools / Equipment Inspection", layout="centered")
st.title("🧑‍🔧 Tools / Equipment Inspection")

# Optional banner
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
        return pd.DataFrame()
    # strip headers; dedupe duplicates (Status, etc.)
    headers = [str(c).strip() for c in values[0]]
    seen = {}
    new_cols = []
    for h in headers:
        seen[h] = seen.get(h, 0) + 1
        new_cols.append(h if seen[h] == 1 else f"{h}_{seen[h]}")
    df = pd.DataFrame(values[1:], columns=new_cols).replace({"": pd.NA}).dropna(how="all")
    # normalize expected cols (handle both "Selected Equipment" vs "Equipment_Selected")
    # we’ll create a consistent alias column: Selected_Equipment
    if "Selected Equipment" in df.columns:
        df["Selected_Equipment"] = df["Selected Equipment"]
    elif "Equipment_Selected" in df.columns:
        df["Selected_Equipment"] = df["Equipment_Selected"]
    else:
        # fall back to Equipment if needed
        df["Selected_Equipment"] = df.get("Equipment", pd.Series([pd.NA]*len(df)))
    # cast Date if present
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

def send_email(to, subject, message, image_file=None, image_file_2=None):
    """Optional: notify when a broken item is checked in."""
    cfg = st.secrets.get("email", {})
    from_address = cfg.get("user")
    password = cfg.get("app_password")
    if not (from_address and password):
        return  # silently skip if email not configured
    host = cfg.get("smtp_host", "smtp.gmail.com")
    port_tls = int(cfg.get("smtp_port", 587))

    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = to if isinstance(to, str) else ", ".join(to)
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
# Catalog (adjust to your list)
# =========================
equipments = [
    "", "Welding_Inverter", "Angle_Grinder_F180", "Angle_Grinder_F125", "POINT_4-KILL",
    "Hammer_Drills", "Rotary_Hammer_Drill", "Makita_Drill", "BLOWER", "Water_Pump",
    "Jigsaw", "Roter_Trypio", "MPALANTEZA", "WORLD_HEATING_AIR_DW_IT_2000W",
    "Circular_Saw", "Power_Strip"
]
employee_names = ["Please Select", "Alexandridis Christos", "Ntamaris Nikolaos", "Papadopoulos Symeon"]
transactions = ["Check In", "Check Out"]
situations = ["Checked", "Broken Down"]


# =========================
# Form (auto clears)
# =========================
with st.form("tools_form", clear_on_submit=True):
    date = st.date_input("Date", datetime.date.today())
    employee_name = st.selectbox("Employee Name", employee_names, index=0)

    c1, c2 = st.columns([1, 2])
    equipment = c1.selectbox("Equipment", equipments, index=0)
    # selection typed/QR result goes here (keep simple text input)
    selected_equipment = c2.text_input("Selected Equipment (or scan result)", value=equipment or "")

    transaction_type = st.selectbox("Transaction Type", ["Please Select"] + transactions, index=0)
    situation = st.selectbox("Situation", ["Please Select"] + situations, index=0)
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

    # --- SAFETY VALVE LOOKUP ---
    # We check the last record for the selected_equipment
    client = get_gspread_client()
    sheet = client.open("Web_App")
    ws_tools = sheet.worksheet("Tools")  # make sure this exists
    df = load_tools_df(ws_tools)

    last_record = pd.DataFrame()
    is_blocked = False
    blocked_reason = ""
    if selected_equipment:
        last_record = df[df["Selected_Equipment"] == selected_equipment].sort_values(
            by="Date", ascending=True, na_position="last"
        ).tail(1)

        # Determine last status
        last_status = None
        if not last_record.empty:
            # tolerate both "Situation" & "Status" headers
            if "Situation" in last_record.columns:
                last_status = str(last_record.iloc[0]["Situation"]).strip()
            elif "Status" in last_record.columns:
                last_status = str(last_record.iloc[0]["Status"]).strip()
            elif "Status_2" in last_record.columns:
                last_status = str(last_record.iloc[0]["Status_2"]).strip()

        # SAFETY RULES:
        # If last status is Broken Down:
        # - Block any "Check Out" attempt.
        # - Encourage "Check In as Checked" (after repair) OR choose another equipment.
        if last_status == "Broken Down":
            if transaction_type == "Check Out":
                is_blocked = True
                blocked_reason = (
                    f"**{selected_equipment}** was last reported **Broken Down**.\n\n"
                    "➡️ You cannot *Check Out* this equipment.\n\n"
                    "✅ Options:\n"
                    "- Choose **another equipment**, **or**\n"
                    "- After it is repaired, **Check In** this same equipment with **Situation = Checked** to mark it fixed."
                )

    # Show a compact summary of the last record (if any)
    if not last_record.empty:
        with st.expander("🔎 Last record for this equipment"):
            summary_cols = [c for c in ["Date", "Employee Name", "Selected_Equipment", "Transaction Type", "Situation", "Comments"] if c in last_record.columns]
            if summary_cols:
                st.table(last_record[summary_cols])
            else:
                st.write(last_record)

    # Show blocking message
    if is_blocked:
        st.error(blocked_reason)

    # Submit button (we enforce again below)
    submitted = st.form_submit_button("Submit", disabled=is_blocked)


# =========================
# Handle submission
# =========================
if submitted:
    # Validation
    if (
        employee_name == "Please Select" or
        transaction_type == "Please Select" or
        situation == "Please Select" or
        not selected_equipment
    ):
        st.warning("Please complete all required fields (employee, equipment, transaction, situation).")
        st.stop()
    if situation == "Broken Down" and not comments.strip():
        st.warning("Please provide comments for the breakdown.")
        st.stop()

    # Double-check safety (in case of race conditions)
    df = load_tools_df(ws_tools)
    last_record = df[df["Selected_Equipment"] == selected_equipment].sort_values(
        by="Date", ascending=True, na_position="last"
    ).tail(1)
    last_status = None
    if not last_record.empty:
        if "Situation" in last_record.columns:
            last_status = str(last_record.iloc[0]["Situation"]).strip()
        elif "Status" in last_record.columns:
            last_status = str(last_record.iloc[0]["Status"]).strip()
        elif "Status_2" in last_record.columns:
            last_status = str(last_record.iloc[0]["Status_2"]).strip()

    if last_status == "Broken Down" and transaction_type == "Check Out":
        st.error(
            f"Safety valve: **{selected_equipment}** cannot be *Checked Out* because it is marked **Broken Down**.\n\n"
            "Please choose **another equipment** or **Check In** this one as **Checked** once it’s repaired."
        )
        st.stop()

    # Save media to /tmp only now
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

    # Build record (align with your sheet columns)
    record = {
        "Date": date_string,
        "Employee Name": employee_name,
        "Equipment": equipment,
        "Selected Equipment": selected_equipment,
        "Transaction Type": transaction_type,
        "Situation": situation,
        "Comments": comments,
    }
    out_df = pd.DataFrame([record])

    # Append to Google Sheet
    if not ws_tools.row_values(1):
        ws_tools.append_rows([out_df.columns.tolist()] + out_df.values.tolist())
    else:
        ws_tools.append_rows(out_df.values.tolist())

    # Optional email when a broken item is recorded
    if situation == "Broken Down":
        to_addr = st.secrets.get("email", {}).get("to_alert", st.secrets.get("email", {}).get("user"))
        if to_addr:
            subject = f"Equipment Broken Down: {selected_equipment}"
            message = f"Equipment {selected_equipment} reported Broken Down by {employee_name}.\n\nRecord:\n{out_df.to_string(index=False)}"
            send_email(to=to_addr, subject=subject, message=message, image_file=picture_path, image_file_2=signature_path)

    st.success("Form submitted successfully! (Form has been cleared.)")
