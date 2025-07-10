# ✅ Full Enhanced Streamlit Dashboard with Login Option 6 and All Features

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import io
import tempfile
from datetime import datetime, timedelta
from fpdf import FPDF
import plotly.io as pio

# --- HEADER MAPPING FIXER ---
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

# --- SESSION & CONFIG FILE PATHS ---
SESSION_FILE = "session_data.json"
CACHE_DIR = "cache"
CONFIG_FILE = os.path.join(CACHE_DIR, "config.json")
os.makedirs(CACHE_DIR, exist_ok=True)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"process_count": 1, "process_names": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_session(data):
    with open(SESSION_FILE, 'w') as f:
        json.dump(data, f)

# --- AUTHENTICATION ---
def authenticate_user(email, password):
    if (email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998") or password == "login6":
        return True
    return False

# --- LOAD SESSION ---
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

# --- LOGIN UI ---
if not st.session_state.authenticated:
    st.title("🔐 Login to Collection Dashboard")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            save_session({"last_login": now.strftime("%Y-%m-%d %H:%M:%S"), "user_email": email})
            st.success("✅ Login Successful!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")
else:
    st.set_page_config(page_title="📊 Collection Dashboard", layout="wide")
    st.title("📊 Collection BPO Dashboard")

    config = load_config()
    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    if is_editor:
        with st.sidebar:
            if st.button("➕ Add Process"):
                config['process_count'] += 1
                save_config(config)
            if config['process_count'] > 1 and st.button("➖ Remove Process"):
                config['process_count'] -= 1
                save_config(config)

    # --- PROCESS SELECTOR ---
    selected_process = st.selectbox("🔽 Select Process", [config['process_names'].get(f"process_{i+1}", f"Process_{i+1}") for i in range(config['process_count'])])

    for i in range(config['process_count']):
        process_key = f"process_{i+1}"
        process_name = config["process_names"].get(process_key, f"Process_{i+1}")

        if process_name != selected_process:
            continue

        with st.sidebar:
            st.markdown(f"### 📁 Process {i+1}")
            if is_editor:
                new_name = st.text_input(f"Name for Process {i+1}", value=process_name, key=f"name_input_{i}")
                config["process_names"][process_key] = new_name
                save_config(config)
                process_name = new_name
            else:
                st.text(f"Name: {process_name}")

            alloc_path = f"{CACHE_DIR}/alloc_{process_name}.csv"
            paid_current_path = f"{CACHE_DIR}/paid_current_{process_name}.csv"
            paid_prev_path = f"{CACHE_DIR}/paid_prev_{process_name}.csv"

            alloc_files = st.file_uploader("📁 Allocation Files", type=["xlsx"], accept_multiple_files=True, key=f"alloc_{i}")
            if alloc_files and is_editor:
                df_alloc = pd.concat([clean_headers(pd.read_excel(f)) for f in alloc_files], ignore_index=True)
                df_alloc.to_csv(alloc_path, index=False)
            elif os.path.exists(alloc_path):
                df_alloc = pd.read_csv(alloc_path)
            else:
                df_alloc = pd.DataFrame()

            paid_current_files = st.file_uploader("📅 Current Month Paid", type=["xlsx"], accept_multiple_files=True, key=f"curr_{i}")
            if paid_current_files and is_editor:
                df_paid_current = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_current_files], ignore_index=True)
                df_paid_current.to_csv(paid_current_path, index=False)
            elif os.path.exists(paid_current_path):
                df_paid_current = pd.read_csv(paid_current_path)
            else:
                df_paid_current = pd.DataFrame()

            paid_prev_files = st.file_uploader("🗓 Previous Months Paid", type=["xlsx"], accept_multiple_files=True, key=f"prev_{i}")
            if paid_prev_files and is_editor:
                df_paid_prev = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_prev_files], ignore_index=True)
                df_paid_prev.to_csv(paid_prev_path, index=False)
            elif os.path.exists(paid_prev_path):
                df_paid_prev = pd.read_csv(paid_prev_path)
            else:
                df_paid_prev = pd.DataFrame()

        # --- MERGED ANALYSIS ---
        if not df_alloc.empty and (not df_paid_current.empty or not df_paid_prev.empty):
            df_paid_all = pd.concat([df_paid_current, df_paid_prev], ignore_index=True)
            df_all = pd.merge(df_alloc, df_paid_all, on="Loan_ID", how="left")
            df_all['Paid_Amount'] = df_all['Paid_Amount'].fillna(0)
            df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount'] * 100).round(2)
            df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

            st.markdown("### 🔍 Filter Options")
            with st.expander("🔎 Filters"):
                if 'Agency' in df_all:
                    agency = st.selectbox("Agency", ["All"] + sorted(df_all['Agency'].dropna().unique().tolist()))
                    if agency != "All":
                        df_all = df_all[df_all['Agency'] == agency]
                if 'Zone' in df_all:
                    zone = st.selectbox("Zone", ["All"] + sorted(df_all['Zone'].dropna().unique().tolist()))
                    if zone != "All":
                        df_all = df_all[df_all['Zone'] == zone]
                if 'Bucket' in df_all:
                    bucket = st.selectbox("Bucket", ["All"] + sorted(df_all['Bucket'].dropna().unique().tolist()))
                    if bucket != "All":
                        df_all = df_all[df_all['Bucket'] == bucket]
                if 'Payment_Date' in df_all:
                    df_all['Payment_Date'] = pd.to_datetime(df_all['Payment_Date'], errors='coerce')
                    min_date, max_date = df_all['Payment_Date'].min(), df_all['Payment_Date'].max()
                    date_range = st.date_input("Date Range", [min_date, max_date])
                    df_all = df_all[(df_all['Payment_Date'] >= pd.to_datetime(date_range[0])) & (df_all['Payment_Date'] <= pd.to_datetime(date_range[1]))]

            st.dataframe(df_all.sort_values(by="Paid_Amount", ascending=False))

            st.markdown("### 📊 Summary Metrics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Allocated", f"₹{df_all['Allocated_Amount'].sum():,.0f}")
                st.metric("Total Paid", f"₹{df_all['Paid_Amount'].sum():,.0f}")
            with col2:
                st.metric("Recovery %", f"{df_all['Recovery %'].mean():.2f}%")
                st.metric("Total Balance", f"₹{df_all['Balance'].sum():,.0f}")

            fig = px.bar(df_all.groupby('Bucket')[['Allocated_Amount', 'Paid_Amount']].sum().reset_index(),
                         x='Bucket', y=['Allocated_Amount', 'Paid_Amount'], barmode='group')
            st.plotly_chart(fig, use_container_width=True)

            # --- EXPORT ---
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as writer:
                df_all.to_excel(writer, index=False, sheet_name="Data")
            st.download_button("📥 Download Excel", data=excel_buf.getvalue(), file_name=f"{process_name}_report.xlsx")

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
            st.download_button("📄 Download PDF", data=pdf_buf.getvalue(), file_name=f"{process_name}_summary.pdf")

    if not os.path.exists(f"{CACHE_DIR}/alloc_{selected_process}.csv"):
        st.warning("⚠ Please upload Allocation File for the selected process.")
