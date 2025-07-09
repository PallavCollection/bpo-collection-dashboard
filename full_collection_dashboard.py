# Updated script with safe Excel file reading (with try-except blocks)
# Prevents crash on corrupt/invalid files

import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from st_aggrid import AgGrid, GridOptionsBuilder

# --- Configs ---
SESSION_FILE = "session_data.json"
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
engine = create_engine("sqlite:///collection_dashboard.db")

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

def save_df_to_db(df, table_name):
    df.to_sql(table_name, engine, if_exists='replace', index=False)

# --- Session Handling ---
def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_session(data):
    with open(SESSION_FILE, 'w') as f:
        json.dump(data, f)

def authenticate_user(email, password):
    return email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998"

# --- Auth ---
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
            session_data = {'last_login': now.strftime("%Y-%m-%d %H:%M:%S"), 'user_email': email}
            save_session(session_data)
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials.")
else:
    st.set_page_config(page_title="✨ Collection Dashboard", layout="wide")
    st.markdown("<h1 style='text-align: center; color: navy;'>📊 Collection BPO Dashboard</h1>", unsafe_allow_html=True)

    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    if 'num_processes' not in st.session_state:
        st.session_state.num_processes = 1
    if 'process_names' not in st.session_state:
        st.session_state.process_names = [f"Process_{i+1}" for i in range(st.session_state.num_processes)]

    if is_editor:
        with st.sidebar:
            st.markdown("### 🔧 Process Manager")
            col1, col2 = st.columns(2)
            if col1.button("➕ Add Process"):
                st.session_state.num_processes += 1
                st.session_state.process_names.append(f"Process_{st.session_state.num_processes}")
            if col2.button("➖ Remove Last Process"):
                if st.session_state.num_processes > 1:
                    st.session_state.num_processes -= 1
                    st.session_state.process_names.pop()

    process_data = {}

    for i in range(st.session_state.num_processes):
        pname = st.session_state.process_names[i]
        with st.sidebar:
            st.markdown(f"---\n📂 **{pname}**")
            if is_editor:
                new_name = st.text_input(f"Rename {pname}", value=pname, key=f"rename_{i}")
                st.session_state.process_names[i] = new_name
                pname = new_name
                alloc_files = st.file_uploader(f"📁 Allocation Files", type=["xlsx"], accept_multiple_files=True, key=f"alloc_{i}")
                paid_curr = st.file_uploader(f"📅 Current Paid Files", type=["xlsx"], accept_multiple_files=True, key=f"paid_curr_{i}")
                paid_prev = st.file_uploader(f"🗓 Previous Paid Files", type=["xlsx"], accept_multiple_files=True, key=f"paid_prev_{i}")
            else:
                alloc_files = paid_curr = paid_prev = None

        alloc_path = f"{CACHE_DIR}/alloc_{pname}.csv"
        paid_curr_path = f"{CACHE_DIR}/paid_curr_{pname}.csv"
        paid_prev_path = f"{CACHE_DIR}/paid_prev_{pname}.csv"

        # Safe reading for allocation files
        if is_editor and alloc_files:
            valid_alloc = []
            for f in alloc_files:
                try:
                    df = pd.read_excel(f)
                    valid_alloc.append(clean_headers(df))
                except Exception as e:
                    st.warning(f"⚠️ Skipping allocation file `{f.name}` due to error: {e}")
            df_alloc = pd.concat(valid_alloc, ignore_index=True) if valid_alloc else pd.DataFrame()
            if not df_alloc.empty:
                df_alloc.to_csv(alloc_path, index=False)
                save_df_to_db(df_alloc, f"{pname}_alloc")
        elif os.path.exists(alloc_path):
            df_alloc = pd.read_csv(alloc_path)
        else:
            df_alloc = pd.DataFrame()

        # Safe reading for current month paid files
        if is_editor and paid_curr:
            valid_curr = []
            for f in paid_curr:
                try:
                    df = pd.read_excel(f)
                    valid_curr.append(clean_headers(df))
                except Exception as e:
                    st.warning(f"⚠️ Skipping current paid file `{f.name}` due to error: {e}")
            df_curr = pd.concat(valid_curr, ignore_index=True) if valid_curr else pd.DataFrame()
            if not df_curr.empty:
                df_curr.to_csv(paid_curr_path, index=False)
                save_df_to_db(df_curr, f"{pname}_paid_curr")
        elif os.path.exists(paid_curr_path):
            df_curr = pd.read_csv(paid_curr_path)
        else:
            df_curr = pd.DataFrame()

        # Safe reading for previous month paid files
        if is_editor and paid_prev:
            valid_prev = []
            for f in paid_prev:
                try:
                    df = pd.read_excel(f)
                    valid_prev.append(clean_headers(df))
                except Exception as e:
                    st.warning(f"⚠️ Skipping previous paid file `{f.name}` due to error: {e}")
            df_prev = pd.concat(valid_prev, ignore_index=True) if valid_prev else pd.DataFrame()
            if not df_prev.empty:
                df_prev.to_csv(paid_prev_path, index=False)
                save_df_to_db(df_prev, f"{pname}_paid_prev")
        elif os.path.exists(paid_prev_path):
            df_prev = pd.read_csv(paid_prev_path)
        else:
            df_prev = pd.DataFrame()

        if not df_alloc.empty:
            df_all_paid = pd.concat([df_curr, df_prev], ignore_index=True)
            df_all = pd.merge(df_alloc, df_all_paid, on='Loan_ID', how='left')
            df_all['Paid_Amount'] = df_all['Paid_Amount'].fillna(0)
            df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount']).round(2)
            df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

            process_data[pname] = {'all': df_all, 'current': df_curr}

    # Rest of the code remains unchanged (charts, view, export, etc.) ...
