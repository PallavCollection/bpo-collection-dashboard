import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine

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
    "agency": "Agency"
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

    if is_editor:
        with st.sidebar:
            if st.button("➕ Add Process"):
                config['process_count'] += 1
                save_config(config)
            if config['process_count'] > 1 and st.button("➖ Remove Process"):
                config['process_count'] -= 1
                save_config(config)

    process_data = {}

    for i in range(config['process_count']):
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"📂 Process {i+1}")

        process_key = f"process_{i+1}"
        default_name = config["process_names"].get(process_key, f"Process_{i+1}")

        if is_editor:
            new_name = st.sidebar.text_input(f"Name for Process {i+1}", value=default_name, key=f"name_input_{i}")
            config["process_names"][process_key] = new_name
            save_config(config)
        else:
            st.sidebar.text(f"Name: {default_name}")

        process_name = config["process_names"][process_key]

        if is_editor:
            alloc_files = st.sidebar.file_uploader("📁 Allocation Files", type=["xlsx"], accept_multiple_files=True, key=f"alloc_{i}")
            paid_current_files = st.sidebar.file_uploader("📅 Current Month Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_curr_{i}")
            paid_prev_files = st.sidebar.file_uploader("🗓️ Previous Months Paid", type=["xlsx"], accept_multiple_files=True, key=f"paid_prev_{i}")
        else:
            st.sidebar.info("View-only mode. Upload disabled.")
            alloc_files = paid_current_files = paid_prev_files = None

        alloc_path = f"{CACHE_DIR}/alloc_{process_name}.csv"
        paid_current_path = f"{CACHE_DIR}/paid_current_{process_name}.csv"
        paid_prev_path = f"{CACHE_DIR}/paid_prev_{process_name}.csv"

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
            df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount']).round(2)
            df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

            if not df_paid_current.empty:
                df_current = pd.merge(df_alloc, df_paid_current, on='Loan_ID', how='left')
                df_current['Paid_Amount'] = df_current['Paid_Amount'].fillna(0)
                df_current['Recovery %'] = (df_current['Paid_Amount'] / df_current['Allocated_Amount']).round(2)
                df_current['Balance'] = df_current['Allocated_Amount'] - df_current['Paid_Amount']
            else:
                df_current = pd.DataFrame()

            process_data[process_name] = {'all': df_all, 'current': df_current}

    if process_data:
        selected_process = st.selectbox("📍 Select Process", list(process_data.keys()))
        data = process_data[selected_process]
        df_all = data['all']
        df_current = data['current']

        st.markdown(f"<h2 style='color: teal;'>📌 Dashboard: {selected_process}</h2>", unsafe_allow_html=True)

        total_alloc = df_all['Allocated_Amount'].sum()
        total_paid_all = df_all['Paid_Amount'].sum()
        recovery_all = round((total_paid_all / total_alloc)*100, 2) if total_alloc else 0

        total_paid_current = df_current['Paid_Amount'].sum() if not df_current.empty else 0
        recovery_current = round((total_paid_current / total_alloc)*100, 2) if total_alloc else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Allocated", f"₹{total_alloc:,.0f}")
        col2.metric("✅ Paid - All Time", f"₹{total_paid_all:,.0f}")
        col3.metric("🟩 Paid - Current Month", f"₹{total_paid_current:,.0f}")
        col4.metric("📈 Recovery % (All Time)", f"{recovery_all}%")

        with st.expander("📋 View Current Month Data"):
            st.dataframe(df_current)

        with st.expander("📋 View All Time Data"):
            st.dataframe(df_all)

        st.markdown("### 📦 Bucket-wise Recovery (All Time)")
        if 'Bucket' in df_all.columns:
            bucket_summary = df_all.groupby('Bucket').agg({
                'Allocated_Amount': 'sum', 'Paid_Amount': 'sum'
            }).reset_index()
            bucket_summary['Recovery %'] = (bucket_summary['Paid_Amount'] / bucket_summary['Allocated_Amount'] * 100).round(2)
            fig2 = px.bar(bucket_summary, x='Bucket', y=['Allocated_Amount', 'Paid_Amount'],
                         barmode='group', title='Allocated vs Paid by Bucket',
                         color_discrete_sequence=['#1f77b4', '#2ca02c'])
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("👈 Please upload data for at least one process to view dashboard.")

    if st.button("🔓 Logout"):
        st.session_state.authenticated = False
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        st.rerun()
