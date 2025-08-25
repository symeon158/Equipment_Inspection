import os
import io
import datetime
import pandas as pd
import numpy as np
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# QR scanner (browser) – enlarged via CSS below
HAS_BROWSER_QR = True
try:
    from streamlit_qrcode_scanner import qrcode_scanner
except Exception:
    HAS_BROWSER_QR = False

# Optional static decode (snapshot/upload) with pyzbar + OpenCV
HAS_PYZBAR = True
try:
    import cv2
    from pyzbar.pyzbar import decode as pyzbar_decode
except Exception:
    HAS_PYZBAR = False

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gspread_dataframe as gsdf

# Email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# =========================
# Page & CSS (make scanner big on tablets)
# =========================
st.set_page_config(page_title="Tools Inspection", layout="wide")
st.markdown("""
<style>
/* Make camera/video surfaces fill width & be taller */
video, canvas {
  width: 100% !important;
  height: auto !important;
  max-height: 70vh !important;
}

/* Give the main container some breathing room */
.block-container {
  padding-top: 1rem;
  padding-left: 2rem;
  padding-right: 2rem;
}
</style>
""", unsafe_allow_html=True)


# =========================
# Session defaults
# =========================
DEFAULTS = {
    "warning_displayed": False,
    "enable_camera": False,
    "equipment_input": "",
    "comments": "",
    "sign": False,
    "picture_path": None,
    "signature_path": None,
    "unique_key_1": "Please Select",   # employee
    "unique_key_2": "",                # equipment dropdown
    "unique_key_3": "Please Select",   # transaction
    "unique_key_4": "Please Select",   # situation
    "unique_key_6": "",                # comments key
    "qr_mode": "Browser Scanner",      # selected QR mode
    "scanning": False,                 # browser scanner toggle
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =========================
# Config & Secrets
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

def send_email(to, subject, message, image_file=None, image_file_2=None):
    """Gmail with TLS (587) and SSL (465) fallback. Uses Streamlit secrets."""
    cfg = st.secrets["email"]
    from_address = cfg["user"]
    password = cfg["app_password"]
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

    # Try STARTTLS
    try:
        server = smtplib.SMTP(host, port_tls)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(from_address, password)
        server.sendmail(from_address, [to] if isinstance(to, str) else to, msg.as_string())
        server.quit()
        st.success("Email sent via TLS (587)!")
        return
    except Exception as e:
        st.warning(f"TLS failed: {e}")

    # Fallback to SSL 465
    try:
        server = smtplib.SMTP_SSL(host, 465)
        server.login(from_address, password)
        server.sendmail(from_address, [to] if isinstance(to, str) else to, msg.as_string())
        server.quit()
        st.success("Email sent via SSL (465)!")
    except Exception as e:
        st.error(f"SSL failed: {e}")


# =========================
# QR helpers (snapshot/upload)
# =========================
def decode_image_bytes(image_bytes: bytes) -> str | None:
    """Decode QR from an image buffer using pyzbar."""
    if not HAS_PYZBAR:
        return None
    file_bytes = np.frombuffer(image_bytes, dtype='uint8')
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return None
    codes = pyzbar_decode(img)
    if codes:
        return codes[0].data.decode("utf-8")
    return None


# =========================
# UI
# =========================
st.title("⚙️ Tools Inspection")

if os.path.exists("Tools.png"):
    st.image(Image.open("Tools.png"))

now = datetime.datetime.now()
date_string = now.strftime("%Y-%m-%d %H:%M:%S")

equipments = [
    "", "Welding_Inverter", "Angle_Grinder_F180", "Angle_Grinder_F125", "POINT_4-KILL",
    "Hammer_Drills", "Rotary_Hammer_Drill", "Makita_Drill", "BLOWER", "Water_Pump",
    "Jigsaw", "Roter_Trypio", "MPALANTEZA", "WORLD_HEATING_AIR_DW_IT_2000W",
    "Circular_Saw", "Power_Strip"
]
employee_names = ["Please Select", "Alexandridis Christos", "Ntamaris Nikolaos", "Papadopoulos Symeon"]

# Form fields
date = st.date_input("Date", datetime.date.today())
employee_name = st.selectbox("Employee Name", employee_names, key="unique_key_1")

col1, col2 = st.columns([1, 2])
equipment = col1.selectbox("Equipment", equipments, key="unique_key_2")

# Keep text field in sync
if equipment:
    st.session_state.equipment_input = equipment

with col2:
    st.subheader("🔎 QR Scanner")
    qr_mode = st.selectbox(
        "Mode",
        ["Browser Scanner", "Snapshot/Upload"],
        index=["Browser Scanner", "Snapshot/Upload"].index(st.session_state.qr_mode),
        key="qr_mode"
    )

    if qr_mode == "Browser Scanner":
        if not HAS_BROWSER_QR:
            st.warning("Browser QR scanner not available. Try Snapshot/Upload.")
        else:
            # Start/Stop controls (full-width area, bigger preview due to CSS above)
            if not st.session_state.scanning:
                if st.button("📷 Start Scanning", use_container_width=True):
                    st.session_state.scanning = True
            else:
                code = qrcode_scanner(key="qr_tools")
                if code:
                    st.session_state.equipment_input = code
                    st.success(f"QR: {code}")
                    st.session_state.scanning = False
                if st.button("❌ Stop Scanning", use_container_width=True):
                    st.session_state.scanning = False

    else:  # Snapshot / Upload
        st.caption("Take a photo or upload an image with a QR code; static decoding is often more accurate.")
        upl = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"], accept_multiple_files=False, key="qr_upload")
        snap = st.camera_input("Or take a snapshot")

        decoded_val = None
        if upl is not None:
            decoded_val = decode_image_bytes(upl.getvalue()) if HAS_PYZBAR else None
        elif snap is not None:
            decoded_val = decode_image_bytes(snap.getvalue()) if HAS_PYZBAR else None

        if decoded_val:
            st.session_state.equipment_input = decoded_val
            st.success(f"QR: {decoded_val}")
        elif (upl or snap) and not decoded_val:
            st.warning("Could not detect a QR code. Try closer, steady, good lighting, and higher contrast.")

# Display selected equipment (free text field the user can edit as well)
st.text_input("Selected Equipment:", value=st.session_state.equipment_input)

transaction_type = st.selectbox("Transaction Type", ["Please Select", "Check In", "Check Out"], key="unique_key_3")
situation = st.selectbox("Situation", ["Please Select", "Checked", "Broken Down"], key="unique_key_4")

def clear_warning():
    st.session_state.warning_displayed = False

comments = st.text_area("Comments", key="unique_key_6", on_change=clear_warning)
st.session_state.comments = comments

# Require comments if Broken Down
if situation == "Broken Down":
    if not st.session_state.get("comments", "").strip():
        st.warning(f"Please provide comments for {st.session_state.get('equipment_input','')} breakdown.")
        st.session_state["warning_displayed"] = True
    else:
        st.session_state["warning_displayed"] = False


# =========================
# Media capture & Signature
# =========================
def take_picture():
    if st.button("📸 Enable Camera"):
        st.session_state.enable_camera = True

    if st.session_state.get("enable_camera", False):
        picture = st.camera_input("Take a Photo")
        if picture is not None:
            pic_path = "/tmp/picture.jpg"
            with open(pic_path, "wb") as file:
                file.write(picture.getbuffer())
            st.image(picture, caption="Photo taken with camera")
            st.session_state.picture_path = pic_path

    if st.button("📷 Disable Camera"):
        st.session_state.enable_camera = False

def signature():
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=5,
        stroke_color="rgb(0, 0, 0)",
        background_color="rgba(255, 255, 255, 1)",
        height=150,
        drawing_mode="freedraw",
        key="canvas_tools",
    )
    if canvas_result.image_data is not None:
        st.image(canvas_result.image_data)
        img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
        sig_path = "/tmp/image1.png"
        img.save(sig_path)
        st.session_state.signature_path = sig_path

take_picture()
if st.checkbox("Signature", key="sign"):
    signature()


# =========================
# Submit
# =========================
def reset_form():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v

if st.button("Submit"):
    # Validate basic fields
    if (
        employee_name == "Please Select"
        or transaction_type == "Please Select"
        or situation == "Please Select"
        or not st.session_state.equipment_input
        or (situation == "Broken Down" and not comments.strip())
    ):
        st.warning("Please complete all required fields (and add comments if Broken Down).")
        st.stop()

    # Sheets client & worksheet
    client = get_gspread_client()
    sheet = client.open("Web_App")
    worksheet = sheet.worksheet("Sheet1")  # Tools transactions sheet

    # Current DF (safe if empty)
    try:
        df_existing = gsdf.get_as_dataframe(worksheet).dropna(how="all")
    except Exception:
        df_existing = pd.DataFrame()

    # Block checkout if last was Broken Down
    if not df_existing.empty and "Selected Equipment" in df_existing.columns and "Situation" in df_existing.columns:
        last_record = df_existing[df_existing["Selected Equipment"] == st.session_state.equipment_input].tail(1)
        if (
            not last_record.empty
            and last_record.iloc[0].get("Situation") == "Broken Down"
            and transaction_type == "Check Out"
        ):
            st.error(
                "The last transaction for this equipment was 'Broken Down'. "
                "Please select a different equipment or choose 'Check In' / 'Checked'."
            )
            st.stop()

    # New record
    new_record = pd.DataFrame(
        {
            "DateTime": [date_string],
            "FormDate": [date.isoformat()],
            "Employee Name": [employee_name],
            "Equipment": [equipment],
            "Selected Equipment": [st.session_state.equipment_input],
            "Transaction": [transaction_type],
            "Situation": [situation],
            "Comments": [comments],
        }
    )

    # Append headers if sheet empty; else append rows
    try:
        has_header = bool(worksheet.row_values(1))
    except Exception:
        has_header = False

    if not has_header:
        worksheet.append_rows([new_record.columns.tolist()] + new_record.values.tolist())
    else:
        worksheet.append_rows(new_record.values.tolist())

    # Email alert if Broken Down
    if new_record.iloc[0]["Situation"] == "Broken Down":
        to_addr = st.secrets["email"].get("to_alert", st.secrets["email"]["user"])
        subject = "Equipment Broken Down"
        msg = f"Equipment {st.session_state.equipment_input} is broken down. Last record:\n{new_record.to_string(index=False)}"
        pic = st.session_state.get("picture_path")
        sig = st.session_state.get("signature_path")
        send_email(to=to_addr, subject=subject, message=msg, image_file=pic, image_file_2=sig)

    # Show last transactions table
    try:
        df_all = gsdf.get_as_dataframe(worksheet).dropna(how="all")
    except Exception:
        df_all = new_record.copy()

    if not df_all.empty and {"Selected Equipment", "DateTime"}.issubset(df_all.columns):
        last_transaction_df = (
            df_all.sort_values("DateTime")
                 .groupby("Selected Equipment", as_index=False)
                 .tail(1)
                 .reset_index(drop=True)
        )
        st.subheader("Last transaction per equipment")
        st.dataframe(last_transaction_df, use_container_width=True)

    st.success("Form submitted successfully!")
    st.button("Submit Another Form", on_click=reset_form)

