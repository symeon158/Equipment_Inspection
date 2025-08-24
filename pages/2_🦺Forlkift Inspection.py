import os
import datetime
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# =========================
# Page config
# =========================
st.set_page_config(page_title="Forklift Daily Inspection", layout="centered")
st.title("🦺 Forklift Daily Inspection")
if os.path.exists("forklift.jpg"):
    st.image(Image.open("forklift.jpg"))

now = datetime.datetime.now()
date_string = now.strftime("%Y-%m-%d %H:%M:%S")


# =========================
# Session defaults
# =========================
DEFAULTS = {
    "enable_camera": False,
    "picture_path": None,
    "signature_path": None,
    "name1": "Please Select",       # employee
    "name2": "Please Select",       # forklift id
    "sign": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =========================
# Secrets-based clients
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
    """Gmail SMTP with TLS (587) and SSL (465) fallback."""
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

    for path, fname in [(image_file, "Forklift_Damage.jpg"), (image_file_2, "signature.png")]:
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
        st.success("Alert email sent via TLS (587)!")
        return
    except Exception as e:
        st.warning(f"TLS failed: {e}")

    # Fallback SSL 465
    try:
        server = smtplib.SMTP_SSL(host, 465)
        server.login(from_address, password)
        server.sendmail(from_address, [to] if isinstance(to, str) else to, msg.as_string())
        server.quit()
        st.success("Alert email sent via SSL (465)!")
    except Exception as e:
        st.error(f"SSL failed: {e}")


# =========================
# UI helpers
# =========================
def take_picture():
    if st.button("📸 Enable Camera"):
        st.session_state.enable_camera = True

    if st.session_state.get("enable_camera", False):
        picture = st.camera_input("Take a Photo")
        if picture is not None:
            pic_path = "/tmp/Forklift_Damage.jpg"
            with open(pic_path, "wb") as f:
                f.write(picture.getbuffer())
            st.image(picture, caption="Photo taken with camera")
            st.session_state.picture_path = pic_path

    if st.button("📷 Disable Camera"):
        st.session_state.enable_camera = False

def signature():
    canvas = st_canvas(
        fill_color="rgba(255,165,0,0.3)",
        stroke_width=5,
        stroke_color="rgb(0,0,0)",
        background_color="rgba(255,255,255,1)",
        height=150,
        drawing_mode="freedraw",
        key="canvas_forklift",
    )
    if canvas.image_data is not None:
        st.image(canvas.image_data)
        img = Image.fromarray(canvas.image_data.astype("uint8"), "RGBA")
        sig_path = "/tmp/signature.png"
        img.save(sig_path)
        st.session_state.signature_path = sig_path

def reset_form():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    # also clear dynamic inspection fields
    for i in range(10):
        st.session_state.pop(f"checked_{i}", None)
        st.session_state.pop(f"broken_{i}", None)
        st.session_state.pop(f"comment_{i}", None)


# =========================
# Form fields
# =========================
date = st.date_input("Date", datetime.date.today())
employee_name = st.selectbox("Employee Name", ["Please Select", "Simeon Papadopoulos", "Alexandridis Christos"], key="name1")
forklift_id   = st.selectbox("Number of Forklifts", ["Please Select", "ME 119135", "ME 125321"], key="name2")
hours = st.number_input("Operation Hours (float)", format="%.1f", step=0.1)
st.write(f"The number you entered is: {hours:.1f}")

# Critical inspection fields
inspection_fields = [
    {"name": "Brake Inspection", "checked": False, "broken": False, "comment": ""},
    {"name": "Engine",           "checked": False, "broken": False, "comment": ""},
    {"name": "Lights",           "checked": False, "broken": False, "comment": ""},
    {"name": "Tires",            "checked": False, "broken": False, "comment": ""},
]

# Render inspection checklist
for i, field in enumerate(inspection_fields):
    st.subheader(field["name"])
    field["checked"] = st.checkbox("Checked", key=f"checked_{i}")
    field["broken"]  = st.checkbox("Broken Down", key=f"broken_{i}")
    # require comment if broken
    comment_val = st.text_area("Comments", max_chars=120, height=60, key=f"comment_{i}")
    field["comment"] = comment_val
    if field["broken"] and not comment_val.strip():
        st.warning(f"Please provide comments for {field['name']} breakdown.")

# Camera + signature
take_picture()
if st.checkbox("Signature", key="sign"):
    signature()


# =========================
# Submit
# =========================
if st.button("Submit_Form"):
    # Validate required fields
    valid_rows = True
    for i, field in enumerate(inspection_fields):
        checked = st.session_state.get(f"checked_{i}", False)
        broken  = st.session_state.get(f"broken_{i}", False)
        comment = st.session_state.get(f"comment_{i}", "").strip()
        if not (checked or (broken and comment)):
            valid_rows = False
            break

    if not valid_rows or employee_name == "Please Select" or forklift_id == "Please Select":
        st.warning("Please complete all required fields (each item must be Checked OR (Broken + Comment)).")
        st.stop()

    # Build row
    data = {
        "DateTime": date_string,
        "FormDate": date.isoformat(),
        "Employee Name": employee_name,
        "Forklift": forklift_id,
        "Operation": hours,
    }
    for i, field in enumerate(inspection_fields):
        mark = f"{'X' if st.session_state.get(f'checked_{i}', False) else ''} {'B' if st.session_state.get(f'broken_{i}', False) else ''}".strip()
        data[field["name"]] = mark
        data[f"{field['name']} Comments"] = st.session_state.get(f"comment_{i}", "")

    df = pd.DataFrame([data])
    st.write(df)

    # Write to Google Sheet
    client = get_gspread_client()
    sheet = client.open("Web_App")
    ws = sheet.worksheet("Forklift")  # ensure this worksheet exists

    try:
        has_header = bool(ws.row_values(1))
    except Exception:
        has_header = False

    if not has_header:
        ws.append_rows([df.columns.tolist()] + df.values.tolist())
    else:
        ws.append_rows(df.values.tolist())

    # Email alert if critical broken
    critical_broken = any(
        st.session_state.get(f"broken_{i}", False) and inspection_fields[i]["name"] in ["Brake Inspection", "Engine"]
        for i in range(len(inspection_fields))
    )
    if critical_broken:
        st.warning("Please stop the forklift and inform the supervisor!")
        to_addr = st.secrets["email"].get("to_alert", st.secrets["email"]["user"])
        subject = "Forklift Broken Down"
        message = f"Forklift {forklift_id} is broken down. Last record:\n{df.to_string(index=False)}"

        send_email(
            to=to_addr,
            subject=subject,
            message=message,
            image_file=st.session_state.get("picture_path"),
            image_file_2=st.session_state.get("signature_path"),
        )

    st.success("Form submitted successfully!")
    st.button("Submit Another Form", on_click=reset_form)
