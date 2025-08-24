import os
import time
import datetime
import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# -------------------------
# Google Sheets (via Secrets)
# -------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Use the JSON dict stored in Streamlit Secrets (no local file needed)
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
client = gspread.authorize(creds)

# -------------------------
# Helpers
# -------------------------
def take_picture():
    # Toggle camera on/off
    if st.button("📸 Enable Camera"):
        st.session_state.enable_camera = True
    if st.session_state.get("enable_camera", False):
        picture = st.camera_input("Take a Photo")
        if picture is not None:
            # Save to tmp so it works on Streamlit Cloud
            damage_path = "/tmp/Forklift_Damage.jpg"
            with open(damage_path, "wb") as f:
                f.write(picture.getbuffer())
            st.image(picture, caption="Photo taken with camera")
            st.session_state.damage_image_path = damage_path
    if st.button("📷 Disable Camera"):
        st.session_state.enable_camera = False


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

    # Attach images if present
    for path, fname in [(image_file, "Forklift_Damage.jpg"), (image_file_2, "signature.png")]:
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


def signature():
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=5,
        stroke_color="rgb(0, 0, 0)",
        background_color="rgba(255, 255, 255, 1)",
        height=150,
        drawing_mode="freedraw",
        key="canvas",
    )
    if canvas_result.image_data is not None:
        st.image(canvas_result.image_data)
        img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
        sig_path = "/tmp/signature.png"
        img.save(sig_path)
        st.session_state.signature_path = sig_path


def reset_button():
    st.session_state["p"] = False
    st.session_state.sign = False
    st.session_state.name1 = "Please Select"
    st.session_state.name2 = "Please Select"
    st.session_state.enable_camera = False
    st.session_state.damage_image_path = None
    st.session_state.signature_path = None
    for i, _ in enumerate(inspection_fields):
        st.session_state[f"checked_{i}"] = False
        st.session_state[f"broken_{i}"] = False
        st.session_state[f"comment_{i}"] = ""


# -------------------------
# UI
# -------------------------
st.title("🦺 Forklift Daily Inspection")

# Optional: display a local image if present
if os.path.exists("forklift.jpg"):
    st.image(Image.open("forklift.jpg"))

if st.button("Forklift Inspection Video"):
    video_url = "https://www.youtube.com/watch?v=BZ6RHAkR7PU"
    DEFAULT_WIDTH = 80
    width = st.sidebar.slider("Width", min_value=0, max_value=100, value=DEFAULT_WIDTH, format="%d%%")
    width = max(width, 0.01)
    side = max((100 - width) / 2, 0.01)
    _, container, _ = st.columns([side, width, side])
    container.video(video_url)

date = st.date_input("Date", datetime.date.today())
employee_name = st.selectbox("Employee Name", ["Please Select", "Simeon Papadopoulos", "Alexandridis Christos"], key="name1")
num_forklifts = st.selectbox("Number of Forklifts", ["Please Select", "ME 119135", "ME 125321"], key="name2")
number = st.number_input("Operation Hours ('Enter a float number')", format="%.1f", step=0.1)
st.write("The number you entered is: {:.1f}".format(number))

inspection_fields = [
    {"name": "Brake Inspection", "checked": False, "broken": False, "comment": ""},
    {"name": "Engine",           "checked": False, "broken": False, "comment": ""},
    {"name": "Lights",           "checked": False, "broken": False, "comment": ""},
    {"name": "Tires",            "checked": False, "broken": False, "comment": ""},
]

for i, field in enumerate(inspection_fields):
    st.subheader(field["name"])
    field["checked"] = st.checkbox("Checked", key=f"checked_{i}")
    field["broken"] = st.checkbox("Breakdown", key=f"broken_{i}")
    if field["broken"] and not st.session_state.get(f"comment_{i}", ""):
        st.warning(f"Please provide comments for {field['name']} breakdown.")
    field["comment"] = st.text_area("Comments", max_chars=50, height=10, key=f"comment_{i}")

take_picture()

if st.checkbox("Sign", key="sign"):
    signature()

# -------------------------
# Submit
# -------------------------
if st.button("Submit_Form"):
    # Validate: each item must be either checked OR (broken AND comment provided)
    all_ok = True
    for i, field in enumerate(inspection_fields):
        checked = st.session_state.get(f"checked_{i}", False)
        broken = st.session_state.get(f"broken_{i}", False)
        comment = st.session_state.get(f"comment_{i}", "").strip()
        if not (checked or (broken and comment)):
            all_ok = False
            break

    if not all_ok or employee_name == "Please Select" or num_forklifts == "Please Select":
        st.warning("Please fill out all required fields and selections.")
    else:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "DateTime": now_str,
            "FormDate": date.isoformat(),
            "Employee Name": employee_name,
            "Forklift": num_forklifts,
            "Working_Hours": number,
        }
        for i, field in enumerate(inspection_fields):
            checked = "X" if st.session_state.get(f"checked_{i}", False) else ""
            broken  = "B" if st.session_state.get(f"broken_{i}", False) else ""
            data[field["name"]] = f"{checked} {broken}".strip()
            data[f"{field['name']} Comments"] = st.session_state.get(f"comment_{i}", "")

        df = pd.DataFrame([data])
        st.write(df)

        # Append to Google Sheet
        sheet = client.open("Web_App")
        ws = sheet.worksheet("Forklift")
        if not ws.row_values(1):
            ws.append_rows([df.columns.tolist()] + df.values.tolist())
        else:
            ws.append_rows(df.values.tolist())

        # Email alert if critical fields broken
        critical_broken = any(
            st.session_state.get(f"broken_{i}", False) and inspection_fields[i]["name"] in ["Brake Inspection", "Engine"]
            for i in range(len(inspection_fields))
        )
        if critical_broken:
            st.warning("Please stop the forklift and inform the supervisor!")
            to_addr = st.secrets["email"].get("to_alert", st.secrets["email"]["user"])
            subject = "Forklift Broken Down"
            message = f"Equipment {num_forklifts} is broken down. Last record:\n{df.to_string(index=False)}"

            damage_path = st.session_state.get("damage_image_path")
            signature_path = st.session_state.get("signature_path")

            send_email(
                to=to_addr,
                subject=subject,
                message=message,
                image_file=damage_path,
                image_file_2=signature_path
            )

        st.success("Form submitted successfully!")
        st.button("Submit Another Form", on_click=reset_button)
