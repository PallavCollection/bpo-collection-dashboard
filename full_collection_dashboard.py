import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import tempfile

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
    login_btn = st.button("Login")

    if login_btn:
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            session_data = {'last_login': now.strftime("%Y-%m-%d %H:%M:%S"), 'user_email': email}
            save_session(session_data)
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
else:
    st.set_page_config(page_title="✨ Beautiful Collection Dashboard", layout="wide")
    st.markdown("<h1 style='text-align: center; color: navy;'>📊 Collection BPO Dashboard</h1>", unsafe_allow_html=True)

    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    selected_process = st.selectbox("🔽 Select Process", [config["process_names"].get(f"process_{i+1}", f"Process_{i+1}") for i in range(config['process_count'])])

    if is_editor:
        with st.sidebar:
            if st.button("➕ Add Process"):
                config['process_count'] += 1
                save_config(config)
            if config['process_count'] > 1 and st.button("➖ Remove Process"):
                config['process_count'] -= 1
                save_config(config)

    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 Upload Agent Performance")
    agent_file = st.sidebar.file_uploader("Upload Agent Performance Excel", type=["xlsx"])
    if agent_file:
        agent_df = pd.read_excel(agent_file)
        agent_df = clean_headers(agent_df)

    process_data = {}

    for i in range(config['process_count']):
        process_key = f"process_{i+1}"
        default_name = config["process_names"].get(process_key, f"Process_{i+1}")

        if default_name != selected_process:
            continue

        st.sidebar.markdown("---")
        st.sidebar.subheader(f"📂 {default_name}")

        if is_editor:
            new_name = st.sidebar.text_input(f"Name for {default_name}", value=default_name, key=f"name_input_{i}")
            config["process_names"][process_key] = new_name
            save_config(config)
        else:
            st.sidebar.text(f"Name: {default_name}")

        process_name = config["process_names"].get(process_key, f"Process_{i+1}")

        alloc_path = f"{CACHE_DIR}/alloc_{process_name}.csv"
        paid_current_path = f"{CACHE_DIR}/paid_current_{process_name}.csv"
        paid_prev_path = f"{CACHE_DIR}/paid_prev_{process_name}.csv"

        if is_editor:
            alloc_files = st.sidebar.file_uploader("📁 Allocation Files", type=["xlsx"], accept_multiple_files=True, key=f"alloc_{i}")
            paid_current_files = st.sidebar.file_uploader("📅 Current Month Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_curr_{i}")
            paid_prev_files = st.sidebar.file_uploader("🗓 Previous Months Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_prev_{i}")

        if is_editor and alloc_files:
            df_alloc = pd.concat([clean_headers(pd.read_excel(f)) for f in alloc_files], ignore_index=True)
            df_alloc.to_csv(alloc_path, index=False)
        elif os.path.exists(alloc_path):
            df_alloc = pd.read_csv(alloc_path)
        else:
            df_alloc = pd.DataFrame()

        if is_editor and paid_current_files:
            df_paid_current = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_current_files], ignore_index=True)
            df_paid_current.to_csv(paid_current_path, index=False)
        elif os.path.exists(paid_current_path):
            df_paid_current = pd.read_csv(paid_current_path)
        else:
            df_paid_current = pd.DataFrame()

        if is_editor and paid_prev_files:
            df_paid_prev = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_prev_files], ignore_index=True)
            df_paid_prev.to_csv(paid_prev_path, index=False)
        elif os.path.exists(paid_prev_path):
            df_paid_prev = pd.read_csv(paid_prev_path)
        else:
            df_paid_prev = pd.DataFrame()

        if not df_alloc.empty and (not df_paid_current.empty or not df_paid_prev.empty):
            df_paid_all = pd.concat([df_paid_current, df_paid_prev], ignore_index=True)
            df_all = pd.merge(df_alloc, df_paid_all, on='Loan_ID', how='left')
            df_all['Paid_Amount'] = df_all['Paid_Amount'].fillna(0)
            df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount'] * 100).round(2)
            df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

            if not df_paid_current.empty:
                df_current = pd.merge(df_alloc, df_paid_current, on='Loan_ID', how='left')
                df_current['Paid_Amount'] = df_current['Paid_Amount'].fillna(0)
                df_current['Recovery %'] = (df_current['Paid_Amount'] / df_current['Allocated_Amount'] * 100).round(2)
                df_current['Balance'] = df_current['Allocated_Amount'] - df_current['Paid_Amount']
            else:
                df_current = pd.DataFrame()

            process_data[process_name] = {'all': df_all, 'current': df_current}

            st.markdown(f"### 📊 Summary for {process_name}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Allocated", f"₹{df_all['Allocated_Amount'].sum():,.0f}")
                st.metric("Total Paid", f"₹{df_all['Paid_Amount'].sum():,.0f}")
            with col2:
                st.metric("Recovery %", f"{df_all['Recovery %'].mean():.2f}%")
                st.metric("Total Balance", f"₹{df_all['Balance'].sum():,.0f}")

            st.markdown("### 🔎 Filter Data")
            if 'Agency' in df_all.columns:
                selected_agency = st.selectbox("Select Agency", options=["All"] + sorted(df_all['Agency'].dropna().unique().tolist()))
                if selected_agency != "All":
                    df_all = df_all[df_all['Agency'] == selected_agency]

            if 'Zone' in df_all.columns:
                selected_zone = st.selectbox("Select Zone", options=["All"] + sorted(df_all['Zone'].dropna().unique().tolist()))
                if selected_zone != "All":
                    df_all = df_all[df_all['Zone'] == selected_zone]

            if 'Bucket' in df_all.columns:
                selected_bucket = st.selectbox("Select Bucket", options=["All"] + sorted(df_all['Bucket'].dropna().unique().tolist()))
                if selected_bucket != "All":
                    df_all = df_all[df_all['Bucket'] == selected_bucket]

            if 'Payment_Date' in df_all.columns:
                df_all['Payment_Date'] = pd.to_datetime(df_all['Payment_Date'], errors='coerce')
                min_date = df_all['Payment_Date'].min()
                max_date = df_all['Payment_Date'].max()
                start_date, end_date = st.date_input("Select Date Range", value=(min_date, max_date))
                df_all = df_all[(df_all['Payment_Date'] >= pd.to_datetime(start_date)) & (df_all['Payment_Date'] <= pd.to_datetime(end_date))]

            st.markdown("### 📥 Export to Excel")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_all.to_excel(writer, sheet_name='Data', index=False)
            st.download_button(label="📤 Download Excel", data=output.getvalue(), file_name=f"{process_name}_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.markdown("### 🖨 Export to PDF (with Chart)")
            chart_buf = io.BytesIO()
            fig_pdf = px.bar(df_all.groupby('Bucket')[['Allocated_Amount', 'Paid_Amount']].sum().reset_index(), x='Bucket', y=['Allocated_Amount', 'Paid_Amount'], barmode='group')
            fig_pdf.write_image(chart_buf, format='png')
            chart_buf.seek(0)

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Summary Report: {process_name}", ln=True, align='C')
            pdf.cell(200, 10, txt=f"Total Allocated: ₹{df_all['Allocated_Amount'].sum():,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Total Paid: ₹{df_all['Paid_Amount'].sum():,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Recovery %: {df_all['Recovery %'].mean():.2f}%", ln=True)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_chart:
                tmp_chart.write(chart_buf.read())
                tmp_chart.flush()
                pdf.image(tmp_chart.name, x=10, y=60, w=180)

            pdf_output = io.BytesIO()
            pdf.output(pdf_output)
            st.download_button("📄 Download PDF", data=pdf_output.getvalue(), file_name=f"{process_name}_summary.pdf", mime="application/pdf")

            st.markdown("### 📊 Recovery % by Bucket")
            if 'Bucket' in df_all.columns:
                bucket_df = df_all.groupby('Bucket').agg({
                    'Allocated_Amount': 'sum',
                    'Paid_Amount': 'sum'
                }).reset_index()
                bucket_df['Recovery %'] = (bucket_df['Paid_Amount'] / bucket_df['Allocated_Amount'] * 100).round(2)
                fig = px.bar(bucket_df, x='Bucket', y='Recovery %', color='Bucket', text='Recovery %')
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 🧾 Current Paid vs Previous Best Performance")
            if not df_current.empty and not df_paid_prev.empty:
                current_perf = df_current['Paid_Amount'].sum()
                prev_perf = df_paid_prev.groupby('Loan_ID')['Paid_Amount'].sum().sum()
                comparison_df = pd.DataFrame({
                    'Period': ['Current Month', 'Previous Months'],
                    'Paid_Amount': [current_perf, prev_perf]
                })
                fig = px.bar(comparison_df, x='Period', y='Paid_Amount', text='Paid_Amount', color='Period')
                st.plotly_chart(fig, use_container_width=True)

            with st.expander("📌 Preview Uploaded Data"):
                st.subheader("Allocation File")
                st.dataframe(df_alloc.sort_values(by='Paid_Amount', ascending=False))
                st.subheader("Paid Files Combined")
                st.dataframe(df_paid_all.sort_values(by='Paid_Amount', ascending=False))

    if not process_data:
        st.warning("⚠ No valid data found. Please upload required files for at least one process.")
