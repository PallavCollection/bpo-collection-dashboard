import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from fpdf import FPDF
import tempfile
import plotly.io as pio

# --- Auto Header Fixer ---
HEADER_MAPPING = {
    "loanid": "Loan_ID",
    "loan_id": "Loan_ID",
    "allocatedamount": "Allocated_Amount",
    "allocated_amount": "Allocated_Amount",
    "paidamount": "Paid_Amount",
    "paid_amount": "Paid_Amount",
    "paymentdate": "Payment_Date",
    "payment_date": "Payment_Date",
    "bucket": "Bucket",
    "agency": "Agency",
    "zone": "Zone"
}

def clean_headers(df):
    df.columns = [HEADER_MAPPING.get(col.strip().lower().replace(" ", "_"), col.strip()) for col in df.columns]
    return df

# --- Paths and Files ---
SESSION_FILE = "session_data.json"
CACHE_DIR = "cache"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)

# --- Persistent Config ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"process_count": 1, "process_names": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = load_config()

# --- Session Handling ---
def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_session(data):
    with open(SESSION_FILE, 'w') as f:
        json.dump(data, f)

# --- Auth ---
def authenticate_user(email, password):
    return email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998"

session_data = load_session()
now = datetime.now()

if 'authenticated' not in st.session_state:
    last_login_str = session_data.get('last_login')
    if last_login_str:
        last_login = datetime.strptime(last_login_str, "%Y-%m-%d %H:%M:%S")
        if now - last_login < timedelta(hours=24):
            st.session_state.authenticated = True
            st.session_state.user_email = session_data.get('user_email', '')
        else:
            st.session_state.authenticated = False
    else:
        st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Secure Access")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            save_session({'last_login': now.strftime("%Y-%m-%d %H:%M:%S"), 'user_email': email})
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
else:
    st.set_page_config(page_title="✨ Beautiful Collection Dashboard", layout="wide")
    st.title("📊 Collection BPO Dashboard")
    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    selected_process = st.selectbox("🔽 Select Process", [config['process_names'].get(f"process_{i+1}", f"Process_{i+1}") for i in range(config['process_count'])])

    for i in range(config['process_count']):
        process_key = f"process_{i+1}"
        process_name = config["process_names"].get(process_key, f"Process_{i+1}")

        if process_name != selected_process:
            continue

        alloc_path = f"{CACHE_DIR}/alloc_{process_name}.csv"
        paid_current_path = f"{CACHE_DIR}/paid_current_{process_name}.csv"
        paid_prev_path = f"{CACHE_DIR}/paid_prev_{process_name}.csv"

        if os.path.exists(alloc_path):
            df_alloc = pd.read_csv(alloc_path)
        else:
            continue

        df_paid_current = pd.read_csv(paid_current_path) if os.path.exists(paid_current_path) else pd.DataFrame()
        df_paid_prev = pd.read_csv(paid_prev_path) if os.path.exists(paid_prev_path) else pd.DataFrame()

        if not df_alloc.empty and (not df_paid_current.empty or not df_paid_prev.empty):
            df_paid_all = pd.concat([df_paid_current, df_paid_prev], ignore_index=True)
            df_all = pd.merge(df_alloc, df_paid_all, on='Loan_ID', how='left')
            df_all['Paid_Amount'] = df_all['Paid_Amount'].fillna(0)
            df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount'] * 100).round(2)
            df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

            # Filters
            with st.expander("🔎 Filter Data"):
                agencies = ["All"] + sorted(df_all['Agency'].dropna().unique().tolist()) if 'Agency' in df_all else []
                zones = ["All"] + sorted(df_all['Zone'].dropna().unique().tolist()) if 'Zone' in df_all else []
                buckets = ["All"] + sorted(df_all['Bucket'].dropna().unique().tolist()) if 'Bucket' in df_all else []
                
                agency_filter = st.selectbox("Agency", agencies)
                zone_filter = st.selectbox("Zone", zones)
                bucket_filter = st.selectbox("Bucket", buckets)

                if agency_filter != "All":
                    df_all = df_all[df_all['Agency'] == agency_filter]
                if zone_filter != "All":
                    df_all = df_all[df_all['Zone'] == zone_filter]
                if bucket_filter != "All":
                    df_all = df_all[df_all['Bucket'] == bucket_filter]

                if 'Payment_Date' in df_all.columns:
                    df_all['Payment_Date'] = pd.to_datetime(df_all['Payment_Date'], errors='coerce')
                    min_date, max_date = df_all['Payment_Date'].min(), df_all['Payment_Date'].max()
                    start_date, end_date = st.date_input("Payment Date Range", [min_date, max_date])
                    df_all = df_all[(df_all['Payment_Date'] >= pd.to_datetime(start_date)) & (df_all['Payment_Date'] <= pd.to_datetime(end_date))]

            st.dataframe(df_all.sort_values(by="Paid_Amount", ascending=False))

            # PDF Export
            fig = px.bar(df_all.groupby('Bucket')[['Allocated_Amount', 'Paid_Amount']].sum().reset_index(),
                         x='Bucket', y=['Allocated_Amount', 'Paid_Amount'], barmode='group')
            chart_buf = io.BytesIO()
            pio.write_image(fig, chart_buf, format="png")

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Summary Report: {process_name}", ln=True, align='C')
            pdf.cell(200, 10, txt=f"Total Allocated: ₹{df_all['Allocated_Amount'].sum():,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Total Paid: ₹{df_all['Paid_Amount'].sum():,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Recovery %: {df_all['Recovery %'].mean():.2f}%", ln=True)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_chart:
                tmp_chart.write(chart_buf.getvalue())
                tmp_chart.flush()
                pdf.image(tmp_chart.name, x=10, y=60, w=180)

            pdf_buf = io.BytesIO()
            pdf.output(pdf_buf)
            st.download_button("📄 Download PDF", data=pdf_buf.getvalue(), file_name=f"{process_name}_summary.pdf", mime="application/pdf")

            # Excel Export
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as writer:
                df_all.to_excel(writer, index=False, sheet_name="Data")
            st.download_button("📥 Download Excel", data=excel_buf.getvalue(), file_name=f"{process_name}_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
