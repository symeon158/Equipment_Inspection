import streamlit as st
import pandas as pd
import datetime
from PIL import Image
import os
import uuid
import numpy as np
import uuid
import time
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit import session_state as ss
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
from email.mime.multipart import MIMEMultipart

scope = ['https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive"]

 
credentials = ServiceAccountCredentials.from_json_keyfile_name("gs_credentials.json", scope)
client = gspread.authorize(credentials)

# sheet = client.create("Web_App")
# sheet.share('pappasym153@gmail.com', perm_type='user', role='writer')

def take_picture():
    # Create a button to enable the camera
    if st.button("📸Enable Camera"):
        st.session_state.enable_camera = True

    # Check if the camera is enabled
    if st.session_state.get("enable_camera", False):
        picture = st.camera_input("Take a Photo")
        if picture is not None:
            with open("Forklift_Damage.jpg", "wb") as file:
                file.write(picture.getbuffer())
            st.image(picture, caption="Photo taken with camera")

    # Create a button to disable the camera
    if st.button("📷Disable Camera"):
        st.session_state.enable_camera = False

def send_email(to, subject, message, image_file):
    from_address = "pappasym153@gmail.com"
    password = "sctyefjfgqvvspga"
    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['To'] = to
    msg['Subject'] = subject
    body = MIMEText(message)
    msg.attach(body)
    with open(image_file, 'rb') as f:
        img = MIMEImage(f.read())
        img.add_header('Content-Disposition', 'attachment', filename="Forklift_Damage.jpg")
        msg.attach(img)
    with open(image_file_2, 'rb') as fp:
        img = MIMEImage(fp.read())
        img.add_header('Content-Disposition', 'attachment', filename="picture.jpg")
        msg.attach(img)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_address, password)
        text = msg.as_string()
        server.sendmail(from_address, to, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)

def signature():
# Define the canvas widget
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",  # Orange with opacity 0.3
        stroke_width=5,
        stroke_color="rgb(0, 0, 0)",
        background_color="rgba(255, 255, 255, 1)",
        height=150,
        drawing_mode="freedraw",
        key="canvas",
    )

    # Check if the canvas has been drawn on
    if canvas_result.image_data is not None:
        # Display the image
        st.image(canvas_result.image_data)

        # Save the image
        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
        img.save('image.png')

def reset_button():
    st.session_state["p"] = False
    st.session_state.sign = False
    st.session_state.name1 = "Please Select"
    st.session_state.name2 = "Please Select"
    st.session_state.enable_camera = False
    for i, field in enumerate(inspection_fields):
        st.session_state[f"checked_{i}"] = False
        st.session_state[f"broken_{i}"] = False
        st.session_state[f"comment_{i}"] = ""
        
    return

     

now = datetime.datetime.now()
date_string = now.strftime("%Y-%m-%d %H:%M:%S")

st.title("🦺Forklift Daily Inspection")
image = Image.open("forklift.jpg")
st.image(image)

if st.button("Forklift Inspection Video"):

    video_url = "https://www.youtube.com/watch?v=BZ6RHAkR7PU"
    DEFAULT_WIDTH = 80
    width = st.sidebar.slider(
            label="Width", min_value=0, max_value=100, value=DEFAULT_WIDTH, format="%d%%"
        )

    width = max(width, 0.01)
    side = max((100 - width) / 2, 0.01)

    _, container, _ = st.columns([side, width, side])
    container.video(data=video_url)

# Date, employee name, and number of forklifts
date = st.date_input("Date")
employee_name = st.selectbox("Employee Name", ["Please Select","Simeon Papadopoulos", "Alexandridis Christos"],key="name1")
num_forklifts = st.selectbox("Number of Forklifts", ["Please Select","ME 119135", "ME 125321"],key="name2")
number = st.number_input("Operation Hours ('Enter a float number')", format="%.1f", step=0.1)
st.write("The number you entered is: {:.1f}".format(number))

# Inspection fields
inspection_fields = [
    {"name": "Brake Inspection", "checked": False, "broken": False, "comment": ""},
    {"name": "Engine", "checked": False, "broken": False, "comment": ""},
    {"name": "Lights", "checked": False, "broken": False, "comment": ""},
    {"name": "Tires", "checked": False, "broken": False, "comment": ""},
]

# Loop through the inspection fields
for i, field in enumerate(inspection_fields):
    st.subheader(field["name"])
    field["checked"] = st.checkbox("Checked", key=f"checked_{i}")
    field["broken"] = st.checkbox("Breakdown", key=f"broken_{i}")
    if field["broken"] and not field["comment"]:
        st.warning(f"Please provide comments for {field['name']} breakdown.")
    field["comment"] = st.text_area("Comments", max_chars=50, height=10, key=f"comment_{i}")
    
take_picture()
 
if st.checkbox("Sign",key="sign"):  
    signature()

# Submit button
if st.button("Submit_Form"):
    # Check if all required fields are filled out
    if not all(field["checked"] or field["broken"] and field["comment"] for field in inspection_fields):
        st.warning("Please fill out all required fields.")
    else:
        # Create a pandas DataFrame from the form data
        data = {"Date": date_string, "Employee Name": employee_name, "Number of Forklifts": num_forklifts, "Working_Hours": number}
        for i, field in enumerate(inspection_fields):
            data[field["name"]] = f"{'X' if field['checked'] else ''} {'B' if field['broken'] else ''}"
            data[f"{field['name']} Comments"] = field["comment"]

        df = pd.DataFrame(data, index=[0])
        st.write(df)

        
        sheet = client.open("Web_App")
        #worksheet = sheet.add_worksheet(title="Forklift", rows=10, cols=5)
        worksheet = sheet.worksheet("Forklift") 
        if not worksheet.row_values(1):
            # Write the headers
            worksheet.append_rows([df.columns.values.tolist()] + df.values.tolist())
        else:
        # Append the data
            worksheet.append_rows(df.values.tolist())
        
    
        # Show a success message and a button to submit another form
        
        if any(field["broken"] for field in inspection_fields if field["name"] in ["Brake Inspection", "Engine"]):
            st.warning("Please stop the forklift and inform the supervisor!")
            email_to = "simeon.papadopoulos@lafarge.com"
            email_subject = "Forklift Broken Down"
            email_message = f"Equipment {num_forklifts} is broken down. Last record:\n{df.to_string()}"
            image_file = "C:\\Users\\sisma\\First Web App\\Forklift_Damage.jpg"
            image_file_2 = "C:\\Users\\sisma\\First Web App\\image.png"
            
            send_email(email_to, email_subject, email_message, image_file)
        st.success("Form submitted successfully!")
        #button to control reset
        reset=st.button('Submit_Another_Form', on_click=reset_button)
        