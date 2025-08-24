import streamlit as st
import pandas as pd
import datetime
from PIL import Image
import os
import uuid
import cv2
from pyzbar import pyzbar
import numpy as np
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer
from streamlit_qrcode_scanner import qrcode_scanner
from pyzbar.pyzbar import decode
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gspread_dataframe as gsdf
from streamlit import session_state as ss
from streamlit_drawable_canvas import st_canvas
from email.mime.multipart import MIMEMultipart

scope = ['https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive"]

 
credentials = ServiceAccountCredentials.from_json_keyfile_name("gs_credentials.json", scope)
client = gspread.authorize(credentials)

# Open the existing "forklift_inspection" sheet
#sheet = client.open('forklift_inspection')

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
        img.save('image1.png')


def reset_form():
    st.session_state.unique_key_1 = "Please Select"
    st.session_state.unique_key_2 = ""
    st.session_state.unique_key_3 = "Please Select"
    st.session_state.unique_key_4 = "Please Select"
    st.session_state.equipment_input = ""
    st.session_state.unique_key_6 = ""
    st.session_state.enable_camera = False
    st.session_state.sign = False
    return   

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
        img.add_header('Content-Disposition', 'attachment', filename="picture.jpg")
        msg.attach(img)
    with open(image_file_2, 'rb') as fp:
        img = MIMEImage(fp.read())
        img.add_header('Content-Disposition', 'attachment', filename="image1.png")
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

now = datetime.datetime.now()
date_string = now.strftime("%Y-%m-%d %H:%M:%S")
image = Image.open("Tools.png")
st.title("⚙️Tools Inspection")
st.image(image)

def scan_qr_code():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Add a frame for scanning to the camera feed
        height, width = frame.shape[:2]
        x1 = int(width / 3)
        x2 = int(2 * width / 3)
        y1 = int(height / 3)
        y2 = int(2 * height / 3)
        frame = cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

        cv2.imshow('QR Code Scanner', frame)
        values = decode(frame)
        if len(values) > 0:
            cap.release()
            cv2.destroyAllWindows()
            result = []
            for code in values:
                result.append(code.data.decode('utf-8'))
            return result[0]
        if cv2.waitKey(1) == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    return None

# Define a function to take a picture and save it to a file
def take_picture():
    # Create a button to enable the camera
    if st.button("📸Enable Camera"):
        st.session_state.enable_camera = True

    # Check if the camera is enabled
    if st.session_state.get("enable_camera", False):
        picture = st.camera_input("Take a Photo")
        if picture is not None:
            with open("picture.jpg", "wb") as file:
                file.write(picture.getbuffer())
            st.image(picture, caption="Photo taken with camera")

    # Create a button to disable the camera
    if st.button("📷Disable Camera"):
        st.session_state.enable_camera = False
        
equipments = ["", "Welding_Inverter", "Angle_Grinder_F180", "Angle_Grinder_F125", "POINT_4-KILL", "Hammer_Drills", "Rotary_Hammer_Drill", "Makita_Drill", "BLOWER", "Water_Pump", "Jigsaw", "Roter_Trypio", "MPALANTEZA", "WORLD_HEATING_AIR_DW_IT_2000W", "Circular_Saw", "Power_Strip" ]
employee_names = ["Please Select", "Alexandridis Christos", "Ntamaris Nikolaos", "Papadopoulos Symeon"]

# Define the fields for the form
date = st.date_input("Date")
employee_name = st.selectbox("Employee Name", employee_names, key='unique_key_1')
col1, col2 = st.columns([1, 2])
equipment = col1.selectbox("Equipment", equipments, key='unique_key_2')
equipment_input = ""
if "equipment_input" not in st.session_state:
    st.session_state.equipment_input=""

col2.write("🕵️Click the button to scan a QR code.")
if equipment != "":
    st.session_state.equipment_input = equipment
if col2.button('Scan'):
    scanned_value = scan_qr_code()
    # If a value is scanned, set it as the equipment value
    if scanned_value:
        st.session_state.equipment_input = scanned_value
    else:
        st.session_state.equipment_input = equipment


def delete_warning():
    st.session_state.warning_displayed = False
    
equipment_input = st.session_state.equipment_input
if "warning_displayed" not in st.session_state:
    st.session_state.warning_displayed = False
# Display the selected equipment
st.text_input("Selected Equipment:", value=st.session_state.equipment_input)
transaction_type = st.selectbox("Transaction Type", ["Please Select", "Check In", "Check Out"], key='unique_key_3')
situation = st.selectbox("Situation", ["Please Select", "Checked", "Broken Down"], key='unique_key_4')
# Check if the comments field is empty
if situation == "Broken Down" :
    # Check if the comments field is empty
    if st.session_state.warning_displayed or not st.session_state.get("comments", ""):
        st.warning(f"Please provide comments for {equipment_input} breakdown.")
    else:
        # Set the flag variable to indicate that the warning message should not be displayed
        st.session_state.warning_displayed = True
comments = st.text_area("Comments", key="unique_key_6",on_change=delete_warning)
# Store the comments field value in the session state
st.session_state.comments = comments


take_picture()
if st.checkbox("Signature",key="sign"):  
    signature()

submit_button = st.button("Submit")

if submit_button:
    # Select the worksheet to read data from
    sheet = client.open('Web_App') 
    #worksheet = sheet.add_worksheet(title="Tools", rows=100, cols=7)
    worksheet = sheet.worksheet("Tools")

# Convert the worksheet to a Pandas DataFrame
    df = gsdf.get_as_dataframe(worksheet)
    

# Check if the last transaction for the selected equipment was broken down
    last_record = df[df["Selected Equipment"] == equipment_input].tail(1)
    if not last_record.empty and last_record.iloc[0]["Situation"] == "Broken Down" and transaction_type == "Check Out":
        st.error("The last transaction for this equipment was broken down. Please select a different equipment or choose 'Check In' or 'Checked' for the transaction type.")
    else:
        # Save the form data to a Pandas DataFrame
        data = {
            "Date": [date_string],
            "Employee Name": [employee_name],
            "Equipment": [equipment],
            "Selected Equipment": [equipment_input],
            "Transaction Type": [transaction_type],
            "Situation": [situation],
            "Comments": [comments]
        }
        new_record = pd.DataFrame(data)
        
        
        if not worksheet.row_values(1):
             # Write the headers
             worksheet.append_rows([new_record.columns.values.tolist()] + new_record.values.tolist())
        else:
        # # Append the data
             worksheet.append_rows(new_record.values.tolist())   
        df = gsdf.get_as_dataframe(worksheet)
        last_record = df[df["Equipment"] == equipment].tail(1)
        if not new_record.empty and new_record.iloc[0]["Situation"] == "Broken Down":
            # Send an email with the last record and the picture
            email_to = "simeon.papadopoulos@lafarge.com"
            email_subject = "Equipment Broken Down"
            email_message = f"Equipment {equipment_input} is broken down. Last record:\n{new_record.to_string()}"
            image_file = "C:\\Users\\sisma\\First Web App\\picture.jpg"
            image_file_2 = "C:\\Users\\sisma\\First Web App\\image1.png"
            send_email(email_to, email_subject, email_message, image_file)

        # Create a new DataFrame to store the last transaction of each equipment
        last_transaction_df = pd.DataFrame(
            columns=["Selected Equipment", "Date", "Employee Name", "Transaction Type", "Situation", "Comments"])
        
        # Loop through each equipment
        for equipment in df["Selected Equipment"].unique():
            # Get the last transaction for the current equipment
            last_transaction = df[df["Selected Equipment"] == equipment].tail(1)
            if not last_transaction.empty:
                # Add the last transaction to the new DataFrame
                last_transaction_df = last_transaction_df.append(last_transaction, ignore_index=True)

        # Display the new DataFrame as a table
        st.write(last_transaction_df)

        # Show a success message
        st.success("Form submitted successfully!")
        
        st.button("Submit Another Form",on_click=reset_form)
        st.session_state.warning_displayed = False   
           
        #st.experimental_set_query_params(employee_name="", equipment="", transaction_type="", situation="",
                                            #comments="")
        