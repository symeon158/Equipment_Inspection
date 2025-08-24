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
worksheet3 = sheet.worksheet('Forklift')
# get the values in the worksheet as a list of lists
values = worksheet.get_all_values()
values2 = worksheet2.get_all_values()
values3 = worksheet3.get_all_values()
# create a Pandas DataFrame from the values
df = pd.DataFrame(values[1:], columns=values[0]).apply(pd.to_numeric, errors='ignore')
df2 = pd.DataFrame(values2[1:], columns=values2[0]).apply(pd.to_numeric, errors='ignore')
df3 = pd.DataFrame(values3[1:], columns=values3[0]).apply(pd.to_numeric, errors='ignore')
# drop rows and columns with all NaN values
df.dropna(axis=0, how='all', inplace=True)
df.dropna(axis=1, how='all', inplace=True)
df2.dropna(axis=0, how='all', inplace=True)
df2.dropna(axis=1, how='all', inplace=True)
df3.dropna(axis=0, how='all', inplace=True)
#df3.dropna(axis=1, how='all', inplace=True)

st.title("📚Tables Report")
# Define the trace for the table
# Convert Date column to datetime

import streamlit as st
import plotly.graph_objs as go

# Load the data


# Convert date column to datetime
df2['Date'] = pd.to_datetime(df2['Date'])

# Get user-selected filters and sorting options
status_filter = st.sidebar.selectbox('Filter by Status', ['All', 'Checked', 'Broken Down'])
transaction_filter = st.sidebar.selectbox('Filter by Transaction', ['All', 'Check In', 'Check Out'])
sort_col = 'Date'
sort_order = st.sidebar.selectbox('Sort order', ['Ascending', 'Descending'])

# Filter data based on user-selected filters
if status_filter == 'All' and transaction_filter == 'All':
    filtered_df = df2
elif status_filter == 'All':
    filtered_df = df2[df2['Transaction'] == transaction_filter]
elif transaction_filter == 'All':
    filtered_df = df2[df2['Status'] == status_filter]
else:
    filtered_df = df2[(df2['Status'] == status_filter) & (df2['Transaction'] == transaction_filter)]

# Sort data based on user-selected sorting option
if sort_order == 'Ascending':
    filtered_df = filtered_df.sort_values(by=sort_col, ascending=True)
else:
    filtered_df = filtered_df.sort_values(by=sort_col, ascending=False)

# Create the Plotly table
table = go.Table(
    header=dict(values=list(filtered_df.columns),
                fill_color='grey',
                font=dict(color='white',size=18),
                align='left'),
    cells=dict(values=[filtered_df[col] for col in filtered_df.columns],
               fill_color=[[ 'white' if val != 'Broken Down' else 'red' for val in filtered_df['Status'] ]],
               font=dict(color=[['white' if val == 'Broken Down' else 'Black' for val in filtered_df['Status'] ]]),
               align='left')
)

# Create a figure and add table trace
fig = go.Figure(data=table)

# Update table layout
fig.update_layout(
    title='⚒️Tools Inspection Last Transaction',
    height=400,
    autosize=True
)

# Display table
st.plotly_chart(fig)



# Load the data

df['Date'] = pd.to_datetime(df['Date'])

def filter_data(df, sort_col=None, sort_order='asc'):
    filtered_df = df[df.apply(lambda x: 'B' in x.values, axis=1)]
    if sort_col:
        filtered_df = filtered_df.sort_values(by=sort_col, ascending=(sort_order=='asc'))
    return filtered_df

# Get the user-selected sort column and order (if any)
sort_col = st.sidebar.selectbox('Sort by', ['', 'Date'])
sort_order = st.sidebar.selectbox('Sort order', ['asc', 'desc'])

# Filter and sort the data
filtered_df = filter_data(df, sort_col=sort_col, sort_order=sort_order)

# Create the Plotly table
fig = go.Figure(data=[go.Table(
    header=dict(values=list(filtered_df.columns),
                fill_color='grey',
                font=dict(color='white',size=14),
                align='left'),
    cells=dict(values=[filtered_df[col] for col in filtered_df.columns],
               fill_color='white',
               font=dict(color='Black',size=12),
               align='left'))
])

# Customize the table
fig.update_layout(
    title='🏎️Forklift Breakdown Report',
    height=400,
    autosize=True
)

# Display the table on Streamlit
st.plotly_chart(fig)



# Load the data into a Pandas DataFrame



