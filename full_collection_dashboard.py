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
import time

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
    st.set_page_config(page_title="✨ Collection Dashboard", layout="wide")
    st.title("📊 Collection BPO Dashboard")

    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    # Add Logout Button
    if st.sidebar.button("🔓 Logout"):
        st.session_state.clear()
        st.rerun()

    # Auto Refresh Only Dashboard Section
    if 'last_refresh' not in st.session_state:
        st.session_state['last_refresh'] = time.time()
    if time.time() - st.session_state['last_refresh'] > 900:  # 15 min
        st.session_state['last_refresh'] = time.time()
        st.experimental_rerun()

    st.sidebar.markdown(f"🕒 Last refresh: {datetime.fromtimestamp(st.session_state['last_refresh']).strftime('%Y-%m-%d %H:%M:%S')}")
    if st.sidebar.button("🔄 Manual Refresh"):
        st.session_state['last_refresh'] = time.time()
        st.experimental_rerun()

    selected_process = st.selectbox("🔽 Select Process", [config['process_names'].get(f"process_{i+1}", f"Process_{i+1}") for i in range(config['process_count'])])

    # The rest of your dashboard section follows...
