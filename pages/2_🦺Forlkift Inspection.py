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

# Optional banner image
if os.path.exists("forklift.jpg"):
    st.image(Image.open("forklift.jpg"))

# --- YouTube video (outside the form) ---
if st.button("Forklift Inspection Video"):
    video_url = "https://www.youtube.com/watch?v=BZ6RHAkR7PU"
    DEFAULT_WIDTH = 80
    width_pct = st.sidebar.slider("Video width", min_value=40, max_value=100, value=DEFAULT_WIDTH, format="%d%%")
    side = max((100 - width_pct) / 2, 0.01)
    _, container, _ = st.columns([side, width_pct, side])
    container.video(video_url)

now = datetime.datetime.now()
date_string = now.strftime("%Y-%m-%d %H:%M:%S")


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
    """Send Gmail alert with attachments using App Passwords."""
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

    # Try STARTTLS (587), fallback SSL (465)
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
# Form (clears automatically on submit)
# =========================
with st.form(key="forklift_form", clear_on_submit=True):
    # --- Top fields ---
    date = st.date_input("Date", datetime.date.today())
    employee_name = st.selectbox(
        "Employee Name",
        ["Please Select", "Simeon Papadopoulos", "Alexandridis Christos"],
    )
    forklift_id = st.selectbox(
        "Number of Forklifts",
        ["Please Select", "ME 119135", "ME 125321"],
    )
    hours = st.number_input("Operation Hours (float)", format="%.1f", step=0.1)

    st.markdown("---")

    # --- Inspection items ---
    inspection_fields = [
        {"name": "Brake Inspection"},
        {"name": "Engine"},
        {"name": "Lights"},
        {"name": "Tires"},
    ]

    checked = []
    broken = []
    comments = []

    for i, field in enumerate(inspection_fields):
        st.subheader(field["name"])
        c1, c2 = st.columns(2)
        with c1:
            chk = st.checkbox("Checked", key=f"checked_{i}")
        with c2:
            brk = st.checkbox("Broken Down", key=f"broken_{i}")
        com = st.text_area("Comments", max_chars=120, height=60, key=f"comment_{i}")
        if brk and not com.strip():
            st.warning(f"Please provide comments for {field['name']} breakdown.")
        checked.append(chk)
        broken.append(brk)
        comments.append(com)

    st.markdown("---")

    # --- Optional media (simplified) ---
    picture = st.camera_input("Take a Photo (optional)")
    # Save to /tmp only on submit to avoid stale files
    signature_canvas = st_canvas(
        fill_color="rgba(255,165,0,0.3)",
        stroke_width=5,
        stroke_color="rgb(0,0,0)",
        background_color="rgba(255,255,255,1)",
        height=150,
        drawing_mode="freedraw",
        key="canvas_forklift",
    )

    submitted = st.form_submit_button("Submit_Form")

# =========================
# Handle submission
# =========================
if submitted:
    # Validation
    valid_rows = all(
        checked[i] or (broken[i] and comments[i].strip())
        for i in range(len(inspection_fields))
    )
    if not valid_rows or employee_name == "Please Select" or forklift_id == "Please Select":
        st.warning("Please complete all required fields.")
        st.stop()

    # Save media to /tmp now
    picture_path = None
    if picture is not None:
        picture_path = "/tmp/Forklift_Damage.jpg"
        with open(picture_path, "wb") as f:
            f.write(picture.getbuffer())

    signature_path = None
    if signature_canvas.image_data is not None:
        img = Image.fromarray(signature_canvas.image_data.astype("uint8"), "RGBA")
        signature_path = "/tmp/signature.png"
        img.save(signature_path)

    # Build row
    data = {
        "DateTime": date_string,
        "FormDate": date.isoformat(),
        "Employee Name": employee_name,
        "Forklift": forklift_id,
        "Operation": hours,
    }
    for i, field in enumerate(inspection_fields):
        mark = f"{'X' if checked[i] else ''} {'B' if broken[i] else ''}".strip()
        data[field["name"]] = mark
        data[f"{field['name']} Comments"] = comments[i]

    df = pd.DataFrame([data])
    st.write(df)

    # Write to Google Sheet
    client = get_gspread_client()
    sheet = client.open("Web_App")
    ws = sheet.worksheet("Forklift")
    if not ws.row_values(1):
        ws.append_rows([df.columns.tolist()] + df.values.tolist())
    else:
        ws.append_rows(df.values.tolist())

    # Alert email if critical broken
    critical_names = {"Brake Inspection", "Engine"}
    critical_broken = any(broken[i] and inspection_fields[i]["name"] in critical_names for i in range(len(inspection_fields)))
    if critical_broken:
        to_addr = st.secrets["email"].get("to_alert", st.secrets["email"]["user"])
        subject = "Forklift Broken Down"
        message = f"Forklift {forklift_id} is broken down. Last record:\n{df.to_string(index=False)}"
        send_email(
            to=to_addr,
            subject=subject,
            message=message,
            image_file=picture_path,
            image_file_2=signature_path,
        )

    st.success("Form submitted successfully! The form has been cleared and is ready for a new entry.")
