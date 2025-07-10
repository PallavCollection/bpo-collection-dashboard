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
from PIL import Image

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
        elif password == "login6":
            st.session_state.authenticated = True
            st.session_state.user_email = "viewer"
            st.success("🔓 Logged in as view-only user")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
else:
    st.set_page_config(page_title="✨ Beautiful Collection Dashboard", layout="wide")
    st.markdown("<h1 style='text-align: center; color: navy;'>📊 Collection BPO Dashboard</h1>", unsafe_allow_html=True)
    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    if is_editor:
        with st.sidebar:
            if st.button("➕ Add Process"):
                config['process_count'] += 1
                save_config(config)
            if config['process_count'] > 1 and st.button("➖ Remove Process"):
                config['process_count'] -= 1
                save_config(config)

    selected_process = st.selectbox("🔽 Select Process", [config['process_names'].get(f"process_{i+1}", f"Process_{i+1}") for i in range(config['process_count'])])

    for i in range(config['process_count']):
        process_key = f"process_{i+1}"
        default_name = config["process_names"].get(process_key, f"Process_{i+1}")

        if is_editor:
            new_name = st.sidebar.text_input(f"Name for Process {i+1}", value=default_name, key=f"name_input_{i}")
            config["process_names"][process_key] = new_name
            save_config(config)
        else:
            st.sidebar.text(f"Name: {default_name}")

        process_name = config["process_names"][process_key]
        if process_name != selected_process:
            continue

        alloc_path = f"{CACHE_DIR}/alloc_{process_name}.csv"
        paid_current_path = f"{CACHE_DIR}/paid_current_{process_name}.csv"
        paid_prev_path = f"{CACHE_DIR}/paid_prev_{process_name}.csv"

        if is_editor:
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"📂 Process {i+1}")
            alloc_files = st.sidebar.file_uploader("📁 Allocation Files", type=["xlsx"], accept_multiple_files=True, key=f"alloc_{i}")
            with st.sidebar.expander("⚙ Manage Allocation File"):
                if os.path.exists(alloc_path):
                    if st.radio(f"Delete Allocation File?", ["No", "Yes"], key=f"confirm_del_alloc_{i}") == "Yes":
                        os.remove(alloc_path)
                        st.success("✅ Allocation file deleted.")
                        st.rerun()

            paid_current_files = st.sidebar.file_uploader("📅 Current Month Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_curr_{i}")
            with st.sidebar.expander("⚙ Manage Paid Current File"):
                if os.path.exists(paid_current_path):
                    if st.radio(f"Delete Paid Current File?", ["No", "Yes"], key=f"confirm_del_paidcurr_{i}") == "Yes":
                        os.remove(paid_current_path)
                        st.success("✅ Paid Current file deleted.")
                        st.rerun()

            paid_prev_files = st.sidebar.file_uploader("🗓 Previous Months Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_prev_{i}")
            with st.sidebar.expander("⚙ Manage Paid Previous File"):
                if os.path.exists(paid_prev_path):
                    if st.radio(f"Delete Paid Previous File?", ["No", "Yes"], key=f"confirm_del_paidprev_{i}") == "Yes":
                        os.remove(paid_prev_path)
                        st.success("✅ Paid Previous file deleted.")
                        st.rerun()

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

            with st.expander("📌 Preview Uploaded Data"):
                st.subheader("Allocation File")
                st.dataframe(df_alloc)
                st.subheader("Paid Files Combined")
                st.dataframe(df_paid_all)

            st.markdown(f"### 📊 Summary for {process_name}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Allocated", f"₹{df_all['Allocated_Amount'].sum():,.0f}")
                st.metric("Total Paid", f"₹{df_all['Paid_Amount'].sum():,.0f}")
            with col2:
                st.metric("Recovery %", f"{df_all['Recovery %'].mean():.2f}%")
                st.metric("Total Balance", f"₹{df_all['Balance'].sum():,.0f}")

            st.markdown("### 📊 Recovery % by Bucket")
            if 'Bucket' in df_all.columns:
                bucket_df = df_all.groupby('Bucket').agg({
                    'Allocated_Amount': 'sum',
                    'Paid_Amount': 'sum'
                }).reset_index()
                bucket_df['Recovery %'] = (bucket_df['Paid_Amount'] / bucket_df['Allocated_Amount'] * 100).round(2)
                fig = px.bar(bucket_df, x='Bucket', y='Recovery %', color='Bucket', text='Recovery %')
                st.plotly_chart(fig, use_container_width=True)

    if not any(os.path.exists(f"{CACHE_DIR}/alloc_{config['process_names'].get(f'process_{i+1}', f'Process_{i+1}')}.csv") for i in range(config['process_count'])):
        st.warning("⚠ No valid data found. Please upload required files for at least one process.")
