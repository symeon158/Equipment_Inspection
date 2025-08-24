import os
import datetime
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Optional QR scanning libs (browser first, then OpenCV/pyzbar fallback)
try:
    from streamlit_qrcode_scanner import qrcode_scanner
    HAS_QR_SCANNER = True
except Exception:
    HAS_QR_SCANNER = False

try:
    import cv2
    from pyzbar.pyzbar import decode as pyzbar_decode
    HAS_OPENCV = True
except Exception:
    HAS_OPENCV = False

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
# CONFIG (from Secrets)
# =========================
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Expect st.secrets sections:
# [gcp_service_account] ... (full service account JSON fields)
# [email]
# user = "your_gmail@gmail.com"
# app_password = "16-char-app-password"
# smtp_host = "smtp.gmail.com"
# smtp_port = 587
# to_alert = "recipient@example.com"
def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    return gspread.authorize(creds)

def send_email(to, subject, message, image_file=None, image_file_2=None):
    cfg = st.secrets["email"]
    from_address = cfg["user"]
    password = cfg["app_password"]
    smtp_host = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 587))

    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    # Attach images if available
    for path, fname in [(image_file, "picture.jpg"), (image_file_2, "image1.png")]:
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
                img.add_header("Content-Disposition", "attachment", filename=fname)
                msg.attach(img)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(from_address, password)
        server.sendmail(from_address, [to], msg.as_string())
        server.quit()
        st.success("Email sent successfully!")
    except Exception as e:
        st.error(f"Error sending email: {e}")


# =========================
# Helpers
# =========================
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


def reset_form():
    st.session_state.unique_key_1 = "Please Select"
    st.session_state.unique_key_2 = ""
    st.session_state.unique_key_3 = "Please Select"
    st.session_state.unique_key_4 = "Please Select"
    st.session_state.equipment_input = ""
    st.session_state.unique_key_6 = ""
    st.session_state.enable_camera = False
    st.session_state.sign = False
    st.session_state.warning_displayed = False
    st.session_state.picture_path = None
    st.session_state.signature_path = None


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


def scan_qr_code_opencv():
    """Fallback scanner using OpenCV (may not work on Streamlit Cloud)."""
    if not HAS_OPENCV:
        st.error("OpenCV/pyzbar not available in this environment.")
        return None

    cap = cv2.VideoCapture(0)
    result = None
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            values = pyzbar_decode(frame)
            if values:
                result = values[0].data.decode("utf-8")
                break

            # No cv2.imshow in Streamlit Cloud — skip UI window.
            # Break via timeout or add a stop button in real usage.
    finally:
        cap.release()
    return result


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

if "equipment_input" not in st.session_state:
    st.session_state.equipment_input = ""

col2.write("🕵️ Click to scan a QR code.")
if equipment:
    st.session_state.equipment_input = equipment

if col2.button("Scan"):
    scanned_value = None
    if HAS_QR_SCANNER:
        # Browser-based QR scanning
        scanned_value = qrcode_scanner(key="qr_tools")
    elif HAS_OPENCV:
        scanned_value = scan_qr_code_opencv()
    else:
        st.warning("QR scanning not available; please type or choose from the list.")

    if scanned_value:
        st.session_state.equipment_input = scanned_value
    elif equipment:
        st.session_state.equipment_input = equipment

# Display selected equipment
st.text_input("Selected Equipment:", value=st.session_state.equipment_input)

transaction_type = st.selectbox("Transaction Type", ["Please Select", "Check In", "Check Out"], key="unique_key_3")
situation = st.selectbox("Situation", ["Please Select", "Checked", "Broken Down"], key="unique_key_4")

def clear_warning():
    st.session_state.warning_displayed = False

# Show warning if Broken Down without comments
if situation == "Broken Down":
    if st.session_state.warning_displayed or not st.session_state.get("comments", ""):
        st.warning(f"Please provide comments for {st.session_state.equipment_input} breakdown.")
    else:
        st.session_state.warning_displayed = True

comments = st.text_area("Comments", key="unique_key_6", on_change=clear_warning)
st.session_state.comments = comments

# Media capture
take_picture()
if st.checkbox("Signature", key="sign"):
    signature()

# =========================
# Submit
# =========================
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

    # GSpread client (via Secrets)
    client = get_gspread_client()
    sheet = client.open("Web_App")
    worksheet = sheet.worksheet("Tools")  # ensure the worksheet exists

    # Current sheet as DF (may be empty)
    try:
        df_existing = gsdf.get_as_dataframe(worksheet).dropna(how="all")
    except Exception:
        df_existing = pd.DataFrame()

    # Block checkout if last was Broken Down
    if not df_existing.empty:
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
            "Transaction Type": [transaction_type],
            "Situation": [situation],
            "Comments": [comments],
        }
    )

    # Append headers if sheet is empty; otherwise append rows
    try:
        first_row = worksheet.row_values(1)
    except Exception:
        first_row = []

    if not first_row:
        worksheet.append_rows([new_record.columns.tolist()] + new_record.values.tolist())
    else:
        worksheet.append_rows(new_record.values.tolist())

    # Refresh DF to compute last transactions per equipment
    try:
        df_all = gsdf.get_as_dataframe(worksheet).dropna(how="all")
    except Exception:
        df_all = new_record.copy()

    # Email alert if Broken Down
    if new_record.iloc[0]["Situation"] == "Broken Down":
        to_addr = st.secrets["email"].get("to_alert", st.secrets["email"]["user"])
        subject = "Equipment Broken Down"
        msg = f"Equipment {st.session_state.equipment_input} is broken down. Last record:\n{new_record.to_string(index=False)}"
        pic = st.session_state.get("picture_path")
        sig = st.session_state.get("signature_path")
        send_email(to=to_addr, subject=subject, message=msg, image_file=pic, image_file_2=sig)

    # Last transaction per equipment
    last_transaction_df = (
        df_all.sort_values("DateTime")
             .groupby("Selected Equipment", as_index=False)
             .tail(1)  # keep last per equipment
             .reset_index(drop=True)
    )
    st.write(last_transaction_df)

    st.success("Form submitted successfully!")
    st.button("Submit Another Form", on_click=reset_form)
