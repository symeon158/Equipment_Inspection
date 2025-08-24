import streamlit as st
from PIL import Image


st.set_page_config(page_title="Equipment Inspection App", layout="centered")
#st.sidebar.title("Equipment Inspection App")
image = Image.open("Critical-Control-Management-CCM-1200x565.png")
st.image(image)
st.write(st.write("Welcome to our Equipment Inspection app, powered by Streamlit! This app allows you to easily inspect and track the status of various equipment used by your team. By monitoring the equipment regularly, you can ensure that they are in good working condition and prevent any accidents or downtimes. The app also implements critical controls management principles to help you identify and manage the critical controls associated with each equipment. Critical controls management is a risk management approach that focuses on identifying and implementing the critical controls that are necessary to manage the risks associated with a particular activity or process. With this app, you can streamline your equipment inspection process and ensure that your team is working safely and efficiently. "))
