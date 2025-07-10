# full_collection_dashboard.py

import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import plotly.express as px
from io import BytesIO

# Constants
ADMIN_EMAIL = "jjagarbattiudyog@gmail.com"
ADMIN_PASSWORD = "Sanu@1998"
VIEW_ONLY_PASSWORD = "login6"
DATA_DIR = "uploaded_data"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Utility functions for session
@st.cache_data

def load_data(path):
    return pd.read_excel(path)

def save_session(data, user_email):
    session_file = os.path.join(DATA_DIR, f"session_{user_email}.json")
    with open(session_file, "w") as f:
        f.write(str(data))

def load_session():
    session_files = os.listdir(DATA_DIR)
    for file in session_files:
        if file.startswith("session_"):
            with open(os.path.join(DATA_DIR, file)) as f:
                return eval(f.read())
    return {}

# Authentication
def authenticate_user(email, password):
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return "editor"
    elif password == VIEW_ONLY_PASSWORD:
        return "viewer"
    else:
        return None

# UI: Login
if "authenticated" not in st.session_state:
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
            save_session({"last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "user_email": email, "role": role}, email)
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
    st.stop()

# UI Config
st.set_page_config(page_title="📊 Collection BPO Dashboard", layout="wide")
st.title("📊 Collection BPO Dashboard")

# Role check
is_editor = st.session_state.role == "editor"

# Sidebar refresh and logout
if st.sidebar.button("🔒 Logout"):
    st.session_state.clear()
    st.rerun()

if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()

if time.time() - st.session_state['last_refresh'] > 900:
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

st.sidebar.markdown(f"🔄 **Last refresh:** {datetime.fromtimestamp(st.session_state['last_refresh']).strftime('%Y-%m-%d %H:%M:%S')}")
if st.sidebar.button("🔁 Manual Refresh"):
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

# Process management
if 'processes' not in st.session_state:
    st.session_state['processes'] = ["Process_1"]

processes = st.session_state.get("processes", ["Process_1"])
selected_process = st.selectbox("Select Process", processes)

if is_editor:
    new_process = st.sidebar.text_input("➕ Add Process")
    if st.sidebar.button("Add Process") and new_process:
        if new_process not in st.session_state.processes:
            st.session_state.processes.append(new_process)
            st.experimental_rerun()

# Upload Section per process
process_path = os.path.join(DATA_DIR, selected_process)
os.makedirs(process_path, exist_ok=True)

st.sidebar.markdown(f"### 📁 {selected_process}")

# Helper to save files

def save_uploaded_file(uploaded_file, folder):
    save_path = os.path.join(process_path, folder)
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# Upload widgets
folders = {
    "Allocation Files": "alloc",
    "Current Month Paid": "paid",
    "Previous Months Paid": "prev_paid",
    "Agent Performance": "agent"
}

uploaded_data = {}

for label, key in folders.items():
    st.sidebar.markdown(f"### {label}")
    file = st.sidebar.file_uploader(f"Upload {label}", type=["xlsx"], key=f"{selected_process}_{key}")
    if file:
        path = save_uploaded_file(file, key)
        uploaded_data[key] = path

# Delete button for data
if is_editor:
    if st.sidebar.button("🗑 Delete Data"):
        import shutil
        shutil.rmtree(process_path)
        st.session_state.processes.remove(selected_process)
        st.success("Deleted data.")
        st.experimental_rerun()

# Load and process data

try:
    alloc_file = uploaded_data.get("alloc")
    paid_file = uploaded_data.get("paid")
    agent_file = uploaded_data.get("agent")

    if alloc_file and paid_file:
        df_alloc = load_data(alloc_file)
        df_paid = load_data(paid_file)

        # Auto correct headers (example: convert to title and strip)
        df_alloc.columns = [col.strip().title() for col in df_alloc.columns]
        df_paid.columns = [col.strip().title() for col in df_paid.columns]

        merged = pd.merge(df_alloc, df_paid, on="Loan Id", how="inner")
        st.subheader("📌 Merged Allocation & Paid Data")
        st.dataframe(merged)

        # Export merged
        output = BytesIO()
        merged.to_excel(output, index=False)
        st.download_button("📥 Download Merged Report", output.getvalue(), file_name="merged_report.xlsx")

    if agent_file:
        df_agent = load_data(agent_file)
        df_agent.columns = [col.strip().title() for col in df_agent.columns]
        st.subheader("🧑‍💼 Agent Performance")
        st.dataframe(df_agent, use_container_width=True)

        # Filter & Sort
        agent_week = st.selectbox("Filter by Week", options=df_agent['Week'].unique())
        df_filtered = df_agent[df_agent['Week'] == agent_week]

        sort_by = st.selectbox("Sort by Column", options=df_filtered.columns)
        df_sorted = df_filtered.sort_values(by=sort_by, ascending=False)
        st.dataframe(df_sorted, use_container_width=True)

        # Charts
        st.subheader("📊 Agent Performance Chart")
        fig = px.bar(df_sorted, x="Agent Name", y="Total Ca", color="Ranking", title="Total Calls per Agent")
        st.plotly_chart(fig, use_container_width=True)

        # Export Agent
        buffer = BytesIO()
        df_sorted.to_excel(buffer, index=False)
        st.download_button("📥 Download Agent Report", buffer.getvalue(), file_name="agent_report.xlsx")

except Exception as e:
    st.error(f"⚠️ Error: {e}")
