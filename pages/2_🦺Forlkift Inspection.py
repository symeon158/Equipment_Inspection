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
from email.mime.image import MIMEImage   # ✅ correct import

# =========================
# Page config
# =========================
st.set_page_config(page_title="Forklift Daily Inspection", layout="centered")
st.title("🦺 Forklift Daily Inspection")

if os.path.exists("forklift.jpg"):
    st.image(Image.open("forklift.jpg"))

# --- YouTube video ---
if st.button("Forklift Inspection Video"):
    video_url = "https://www.youtube.com/watch?v=BZ6RHAkR7PU"
    DEFAULT_WIDTH = 80
    width_pct = st.sidebar.slider("Video width", min_value=40, max_value=100,
                                   value=DEFAULT_WIDTH, format="%d%%")
    side = max((100 - width_pct) / 2, 0.01)
    _, container, _ = st.columns([side, width_pct, side])
    container.video(video_url)

now = datetime.datetime.now()
date_string = now.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# Session defaults
# =========================
DEFAULTS = {
    "enable_camera": False,
    "picture_path": None,
    "signature_path": None,
    "sign": False,
    "can_reset": False,
    "_do_reset": False,   # <-- internal reset flag
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =========================
# Pre-widget reset
# =========================
if st.session_state.get("_do_reset", False):
    # wipe widget state before widgets are created
    for key in list(st.session_state.keys()):
        if key.startswith(("checked_", "broken_", "comment_")):
            st.session_state.pop(key, None)
    for k in ["name1", "name2", "sign", "canvas_forklift"]:
        st.session_state.pop(k, None)
    st.session_state["enable_camera"] = False
    st.session_state["picture_path"] = None
    st.session_state["signature_path"] = None
    st.session_state["can_reset"] = False
    st.session_state["_do_reset"] = False

# =========================
# Secrets-based clients
# =========================
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    return gspread.authorize(creds)

def send_email(to, subject, message, image_file=None, image_file_2=None):
    cfg = st.secrets["email"]
    from_address = cfg["user"]
    password = cfg["app_password"]
    host = cfg.get("smtp_host", "smtp.gmail.com")
    port_tls = int(cfg.get("smtp_port", 587))

    msg = MIMEMultipart()
    msg["From"] = from_address
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    for path, fname in [(image_file, "Forklift_Damage.jpg"),
                        (image_file_2, "signature.png")]:
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
                img.add_header("Content-Disposition", "attachment",
                               filename=fname)
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

# =========================
# Form fields
# =========================
date = st.date_input("Date", datetime.date.today())
employee_name = st.selectbox(
    "Employee Name",
    ["Please Select", "Simeon Papadopoulos", "Alexandridis Christos"],
    key="name1"
)
forklift_id = st.selectbox(
    "Number of Forklifts",
    ["Please Select", "ME 119135", "ME 125321"],
    key="name2"
)
hours = st.number_input("Operation Hours (float)", format="%.1f", step=0.1)

inspection_fields = [
    {"name": "Brake Inspection"},
    {"name": "Engine"},
    {"name": "Lights"},
    {"name": "Tires"},
]

for i, field in enumerate(inspection_fields):
    st.subheader(field["name"])
    st.checkbox("Checked", key=f"checked_{i}")
    st.checkbox("Broken Down", key=f"broken_{i}")
    st.text_area("Comments", max_chars=120, height=60, key=f"comment_{i}")
    if st.session_state.get(f"broken_{i}", False) and not st.session_state.get(f"comment_{i}", "").strip():
        st.warning(f"Please provide comments for {field['name']} breakdown.")

take_picture()
if st.checkbox("Signature", key="sign"):
    signature()

# =========================
# Submit
# =========================
if st.button("Submit_Form"):
    valid = all(
        st.session_state.get(f"checked_{i}", False) or
        (st.session_state.get(f"broken_{i}", False)
         and st.session_state.get(f"comment_{i}", "").strip())
        for i in range(len(inspection_fields))
    )
    if not valid or employee_name == "Please Select" or forklift_id == "Please Select":
        st.warning("Please complete all required fields.")
        st.stop()

    data = {
        "DateTime": date_string,
        "FormDate": date.isoformat(),
        "Employee Name": employee_name,
        "Forklift": forklift_id,
        "Operation": hours,
    }
    for i, field in enumerate(inspection_fields):
        mark = f"{'X' if st.session_state.get(f'checked_{i}', False) else ''} " \
               f"{'B' if st.session_state.get(f'broken_{i}', False) else ''}".strip()
        data[field["name"]] = mark
        data[f"{field['name']} Comments"] = st.session_state.get(f"comment_{i}", "")

    df = pd.DataFrame([data])
    st.write(df)

    client = get_gspread_client()
    sheet = client.open("Web_App")
    ws = sheet.worksheet("Forklift")
    if not ws.row_values(1):
        ws.append_rows([df.columns.tolist()] + df.values.tolist())
    else:
        ws.append_rows(df.values.tolist())

    critical_broken = any(
        st.session_state.get(f"broken_{i}", False)
        and inspection_fields[i]["name"] in ["Brake Inspection", "Engine"]
        for i in range(len(inspection_fields))
    )
    if critical_broken:
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
    st.session_state["can_reset"] = True

# =========================
# Reset button
# =========================
if st.session_state.get("can_reset", False):
    if st.button("Submit Another Form"):
        st.session_state["_do_reset"] = True
        st.rerun()
