import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gspread_dataframe as gsdf
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
import plotly.express as px


scope = ['https://www.googleapis.com/auth/spreadsheets',
          "https://www.googleapis.com/auth/drive"]

 
credentials = ServiceAccountCredentials.from_json_keyfile_name("gs_credentials.json", scope)
client = gspread.authorize(credentials)

# specify the sheet and worksheet
sheet = client.open('Web_App')
#worksheet = sheet.add_worksheet(title="Dashboard", rows=1000, cols=13)
worksheet = sheet.worksheet('Dashboard')
worksheet2 = sheet.worksheet('Sheet1')
# get the values in the worksheet as a list of lists
values = worksheet.get_all_values()
values2 = worksheet2.get_all_values()
# create a Pandas DataFrame from the values
df = pd.DataFrame(values[1:], columns=values[0]).apply(pd.to_numeric, errors='ignore')
df2 = pd.DataFrame(values2[1:], columns=values2[0]).apply(pd.to_numeric, errors='ignore')
# drop rows and columns with all NaN values
df.dropna(axis=0, how='all', inplace=True)
df.dropna(axis=1, how='all', inplace=True)
df2.dropna(axis=0, how='all', inplace=True)
df2.dropna(axis=1, how='all', inplace=True)
# do something with the DataFrame
# Get max Operation value for each Forklift
print(df2)
st.set_page_config(page_title="Dashboard", layout="centered")
st.title("📊Dashboard")

forklift_options = df['Forklift'].unique().tolist()
selected_forklift = st.sidebar.radio("Select a forklift", forklift_options)

max_operation = df[df['Forklift'] == selected_forklift]['Operation'].max()
import datetime
import streamlit as st
if selected_forklift == 'Forklift 1':
    next_service = 1000
    
else:
    next_service = 500
# Calculate the remaining hours
remaining_hours = next_service - max_operation

# Calculate the date of the next service
now = datetime.datetime.now()
days_to_next_service = remaining_hours / 24
next_service_date = now + datetime.timedelta(days=days_to_next_service)

# Create the reminder card
left_column, middle_column, right_column = st.columns(3)
with left_column:
    st.subheader("Next Service:")
    st.subheader(f"Hours {next_service:,}")
with middle_column:
    st.subheader("Remaining Hours:")
    st.subheader(f"{remaining_hours}")
with right_column:
    st.subheader("Service Progress:")
    st.progress(max_operation/next_service)

st.markdown("""---""")


# create bullet gauge figure
fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = max_operation,
    title = {'text': "Operation Hours"},
    gauge = {
        'axis': {'range': [None, df['Operation'].max()]},
        'bar': {'color': "darkblue"},
        'steps' : [
            {'range': [0, df['Operation'].max() / 3], 'color': "red"},
            {'range': [df['Operation'].max() / 3, df['Operation'].max() * 2 / 3], 'color': "orange"},
            {'range': [df['Operation'].max() * 2 / 3, df['Operation'].max()], 'color': "green"}],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': df['Operation'].max()}}))

# display bullet gauge figure
st.plotly_chart(fig)



# Filter data by the selected forklift
df_filtered = df[df['Forklift'] == selected_forklift]

# Create a line chart of forklift hours over time
fig1 = go.Figure(data=go.Scatter(x=df_filtered['Date'], y=df_filtered['hours'], mode='lines'))

# Set the plot title and axis labels
fig1.update_layout(title='Forklift Hours over Time', xaxis_title='Date', yaxis_title='Hours')

# Display the plot


# Create a bar chart of total hours and a line chart of average daily hours by year-month
df_filtered['Date'] = pd.to_datetime(df_filtered['Date'])
df_filtered['Year-Month'] = df_filtered['Date'].dt.strftime('%Y-%m')

# Group by Year-Month and calculate the sum of hours
df_sum = df_filtered.groupby('Year-Month')['hours'].sum().reset_index()

# Group by Year-Month and calculate the mean of hours
df_mean = df_filtered.groupby('Year-Month')['hours'].mean().reset_index()

fig2 = go.Figure()

# Add the bar chart for sum of hours
fig2.add_trace(go.Bar(x=df_sum['Year-Month'], y=df_sum['hours'], name='Sum of Hours'))

# Add the line chart for average daily hours
fig2.add_trace(go.Scatter(x=df_mean['Year-Month'], y=df_mean['hours'], mode='lines', name='Avg Daily Hours'))

fig2.update_layout(title='Hours by Year-Month', xaxis_title='Year-Month', yaxis_title='Hours')

# Display the plot


view_type = st.radio("Select a view", ("Year-Month", "Daily Hours"),horizontal=True)
if view_type == "Year-Month":
    st.plotly_chart(fig2)
else:
    st.plotly_chart(fig1)  

# calculate the count and percentage of each user
user_count = df['User'].value_counts()
user_percent = user_count / user_count.sum() * 100

# create the pie chart using Plotly
fig = px.pie(names=user_count.index, values=user_count.values, title='User Distribution')

# add the percentage labels to the chart
fig.update_traces(textinfo='percent+label')

# display the chart in Streamlit
st.plotly_chart(fig)



# Create a stacked bar plot of inspections by component and user
fig = go.Figure(data=[
    go.Bar(name='Brake Inspection', x=df['User'], y=df['Brake Inspection']),
    go.Bar(name='Engine', x=df['User'], y=df['Engine']),
    go.Bar(name='Lights', x=df['User'], y=df['Lights']),
    go.Bar(name='Tires', x=df['User'], y=df['Tires'])
])

# Set the plot title and axis labels
fig.update_layout(title='Inspections by Component and User', xaxis_title='User', yaxis_title='Number of Inspections', barmode='stack')

# Display the plot
st.plotly_chart(fig)




 

    








