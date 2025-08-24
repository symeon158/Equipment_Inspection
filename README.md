# 🦺 Equipment & Forklift Inspection Platform

A **Streamlit-based web application suite** for industrial safety and asset management.  
This project digitalizes inspection processes for **forklifts and tools**, logs inspection data to **Google Sheets**, and provides **interactive dashboards & reports** for management. It also features **email alerts** with attachments for critical issues.

---

## 🚀 Modules

### 1. Forklift Daily Inspection
- Daily forklift inspection checklist
- Capture **photos** via device camera
- Digital **signature** input
- Automatic logging to **Google Sheets**
- 📧 **Email alerts** (with photo & signature) for critical failures (Brake / Engine)

### 2. Tools & Equipment Inspection
- QR code / manual selection of equipment
- Transaction types: Check-In / Check-Out
- Status tracking: Checked / Broken Down
- Photo and digital signature support
- Auto-logging to Google Sheets (`Tools` worksheet)
- Email alerts for equipment breakdowns

### 3. Tables & Reports
- Interactive tables with **filters** (status, transaction type, date range)
- Conditional formatting (e.g., highlight broken equipment)
- 📊 Clear overview of last transactions for each asset
- Export-ready data views

### 4. 📈 Dashboard
- Operation hours tracking per forklift
- Next service reminder (hours + estimated date)
- Gauge charts for usage intensity
- Line & bar charts for usage trends
- User distribution (pie chart)
- Stacked component inspection analysis

---

## 🛠️ Tech Stack

- [Streamlit](https://streamlit.io/) – Web app framework  
- [Pandas](https://pandas.pydata.org/) – Data handling  
- [gspread](https://github.com/burnash/gspread) – Google Sheets API client  
- [oauth2client](https://github.com/google/oauth2client) – Google API auth  
- [Pillow](https://python-pillow.org/) – Image processing  
- [streamlit-drawable-canvas](https://github.com/andfanilo/streamlit-drawable-canvas) – Digital signatures  
- [Plotly](https://plotly.com/python/) – Dashboards & charts  
- [SMTP / email.mime](https://docs.python.org/3/library/email.mime.html) – Email alerts  

---

## 📂 Project Structure

