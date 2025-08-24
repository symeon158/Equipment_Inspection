import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# scope = ['https://www.googleapis.com/auth/spreadsheets',
#           "https://www.googleapis.com/auth/drive"]

 
# credentials = ServiceAccountCredentials.from_json_keyfile_name("gs_credentials.json", scope)
# client = gspread.authorize(credentials)

# sheet = client.create("forklift_inspection")
# sheet.share('pappasym153@gmail.com', perm_type='user', role='writer')
# # Open the existing "forklift_inspection" sheet
# sheet = client.open('forklift_inspection')

# # Create a new sheet named "Tools Inspection"
# worksheet = sheet.add_worksheet("Tools_Inspection",rows = 1000, cols=6)

st.title("📝About")
st.header("Web App for Critical Control Management")
st.subheader("Forklift Inspection")
st.write("Web application for conducting and submitting forklift daily inspections. The application allows the user to watch an official forklift inspection video and enter the date, employee name, the license plate of forklifts to be inspected and the working hours. It also includes checkboxes to mark the completion status of different forklift inspection items. The user can provide comments for each item and it is required whenever there is a breakdown field. The app includes several additional features, such as the ability to take a picture with the computer's camera, draw a signature on a canvas, and reset all inspection fields to their default values. The app also uses the Google Sheets API to log the results of each inspection in a Google Sheet. This enables the user to easily track the results of multiple inspections over time. The script generates a success message after form submission and a warning message if any of the essential forklift inspection items are marked as broken.Finally, the app includes a feature to send an email with the inspection results and a picture of the forklift to a specified recipient. This could be useful for sending the inspection results to a manager or maintenance team. Overall, this app provides a user-friendly interface for conducting daily inspections of forklifts, and includes useful features for tracking and sharing inspection results.")
st.markdown("""---""")

st.subheader("Tools Inspection")
st.write("This is a Streamlit app for conducting inspections on tools and equipment. The app allows the user to select an employee name and a piece of equipment to inspect. The user can also scan a QR code to identify the equipment automatically. The app then guides the user through a series of inspection questions related to the selected equipment. The app also includes a camera feature that enables the user to take a photo of the inspected equipment. The app saves the photo and attaches it to an email that is sent to the user's supervisor. The email includes a summary of the inspection results. The app integrates with Google Sheets to save the inspection results, and the user can view the results in a Google Sheets document. The app also includes a reset button that clears the inspection form and allows the user to start a new inspection. Overall, this app provides a convenient and streamlined way for employees to conduct equipment inspections, ensuring that tools and equipment are safe to use and in good condition. The app's integration with Google Sheets and email features also make it easy for supervisors to track inspection results and take any necessary corrective action.")
st.markdown("""---""")