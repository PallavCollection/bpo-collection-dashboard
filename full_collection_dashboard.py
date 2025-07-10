import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json

# --- CONFIG ---
ADMIN_EMAIL = "jjagarbattiudyog@gmail.com"
ADMIN_PASSWORD = "Sanu@1998"
VIEW_ONLY_PASSWORD = "login6"
SESSION_FILE = "session_data.json"
DATA_DIR = "uploaded_data"
os.makedirs(DATA_DIR, exist_ok=True)

# --- AUTH FUNCTIONS ---
def save_session(data, **kwargs):
    try:
        with open(SESSION_FILE, 'r') as f:
            all_data = json.load(f)
    except:
        all_data = {}
    all_data[kwargs['user_email']] = data
    with open(SESSION_FILE, 'w') as f:
        json.dump(all_data, f)

def load_session():
    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def authenticate_user(email, password):
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return "editor"
    elif password == VIEW_ONLY_PASSWORD:
        return "viewer"
    else:
        return None

# --- HEADER NORMALIZATION ---
def normalize_headers(df, expected_headers):
    import re
    cleaned_cols = {}
    for col in df.columns:
        key = re.sub(r'\W+', '', col).lower()
        cleaned_cols[key] = col
    header_map = {}
    for expected in expected_headers:
        cleaned_expected = re.sub(r'\W+', '', expected).lower()
        if cleaned_expected in cleaned_cols:
            header_map[cleaned_cols[cleaned_expected]] = expected
        else:
            raise ValueError(f"Missing expected column: {expected}")
    return df.rename(columns=header_map)

# --- UI ---
st.set_page_config(page_title="📊 Beautiful Collection Dashboard", layout="wide")
st.title("📊 Collection BPO Dashboard")

# --- LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = authenticate_user(email, password)
        if role:
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.session_state.role = role
            save_session({'last_login': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'role': role}, user_email=email)
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
    st.stop()

# --- SIDEBAR ---
st.sidebar.button("🔒 Logout", on_click=lambda: st.session_state.clear())
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()
if time.time() - st.session_state['last_refresh'] > 900:
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

st.sidebar.markdown(f"⏰ **Last refresh:** {datetime.fromtimestamp(st.session_state['last_refresh']).strftime('%Y-%m-%d %H:%M:%S')}")
if st.sidebar.button("🔄 Manual Refresh"):
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

# --- PROCESS SELECTION ---
process_list = [f for f in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, f))]
selected_process = st.selectbox("Select Process", options=process_list, index=0 if process_list else None)

# --- FILE UPLOAD ---
if st.session_state.role == "editor":
    with st.sidebar:
        st.markdown("### 📂 Upload Files")
        process_name = st.text_input("Process Name", value="Process_1")
        if st.button("+ Add Process"):
            os.makedirs(os.path.join(DATA_DIR, process_name), exist_ok=True)
            st.rerun()

        upload_types = {
            'alloc': "Allocation Files",
            'current': "Current Month Paid",
            'old': "Previous Months Paid"
        }
        for key, label in upload_types.items():
            st.markdown(f"#### {label}")
            uploaded = st.file_uploader(f"{label}", type=["xlsx"], key=f"{key}_{process_name}")
            if uploaded:
                save_path = os.path.join(DATA_DIR, process_name, f"{key}_{uploaded.name}")
                with open(save_path, "wb") as f:
                    f.write(uploaded.read())
                st.success(f"Saved: {uploaded.name}")
                st.rerun()

        if st.button("🗑️ Delete Data"):
            import shutil
            shutil.rmtree(os.path.join(DATA_DIR, process_name), ignore_errors=True)
            st.success("Deleted process data")
            st.rerun()

# --- LOAD & DISPLAY ---
try:
    if selected_process:
        folder = os.path.join(DATA_DIR, selected_process)
        df_alloc, df_paid, df_old = None, None, None
        for f in os.listdir(folder):
            fpath = os.path.join(folder, f)
            if f.startswith("alloc"):
                df_alloc = pd.read_excel(fpath)
                df_alloc = normalize_headers(df_alloc, ['Loan ID', 'Customer Name', 'Zone', 'Agency Name', 'Allocation Date', 'Allocation Amount'])
            elif f.startswith("current"):
                df_paid = pd.read_excel(fpath)
                df_paid = normalize_headers(df_paid, ['Loan ID', 'Paid Amount', 'Payment Date', 'Mode', 'Agency Name'])
            elif f.startswith("old"):
                df_old = pd.read_excel(fpath)
                df_old = normalize_headers(df_old, ['Loan ID', 'Paid Amount', 'Payment Date', 'Mode', 'Agency Name'])

        if df_alloc is not None and df_paid is not None:
            df_all = pd.merge(df_alloc, df_paid, on='Loan ID', how='left')
            st.subheader("📊 Allocation vs Paid")
            st.dataframe(df_all, use_container_width=True)

except Exception as e:
    st.error(f"❌ Error: {str(e)}")
