# Your original import section remains unchanged
import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import json
from datetime import datetime, timedelta

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
    "bucket": "Bucket"
}

def clean_headers(df):
    df.columns = [HEADER_MAPPING.get(col.strip().lower().replace(" ", "_"), col.strip()) for col in df.columns]
    return df

# --- Session Handling ---
SESSION_FILE = "session_data.json"
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_session(data):
    with open(SESSION_FILE, 'w') as f:
        json.dump(data, f)

# ---- Auth Section ----
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

    # --- Dynamic process count ---
    if 'num_processes' not in st.session_state:
        st.session_state.num_processes = 2 if is_editor else 1

    num_processes = st.session_state.num_processes

    # ➕ Add Process button in sidebar (only for editor)
    if is_editor:
        if st.sidebar.button("➕ Add Process"):
            st.session_state.num_processes += 1
            st.experimental_rerun()

    process_data = {}

    for i in range(num_processes):
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"📂 Process {i+1}")
        process_name = f"Process_{i+1}"

        if is_editor:
            process_name = st.sidebar.text_input(f"Process {i+1} Name", value=f"Process_{i+1}")

            alloc_files = st.sidebar.file_uploader(
                f"📁 Allocation Files", type=["xlsx"], accept_multiple_files=True,
                key=f"alloc_{i}")

            paid_current_files = st.sidebar.file_uploader(
                f"📅 Current Month Paid Files", type=["xlsx"], accept_multiple_files=True,
                key=f"paid_current_{i}")

            paid_prev_files = st.sidebar.file_uploader(
                f"🗓 Previous Months Paid Files", type=["xlsx"], accept_multiple_files=True,
                key=f"paid_prev_{i}")
        else:
            st.sidebar.info("View-only mode enabled. Upload disabled.")
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
        selected_process = st.selectbox("📍 *Select Process to View Report*", list(process_data.keys()))
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
            if st.button("👁 View Current Month Data"):
                st.dataframe(df_current)

        with st.expander("📋 View All Time Data"):
            if st.button("👁 View All Time Data"):
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
        st.info("👈 Please upload allocation & paid files process-wise to view dashboard.")

    # --- Delete buttons only for admin ---
    if is_editor:
        st.markdown("## 🗑 Delete Uploaded Data")
        file_type = st.radio("Select file type to delete:", 
            ["Allocation Files", "Current Month Paid Files", "Previous Months Paid Files"])
        if st.button("🧹 Delete Selected File Type"):
            prefix_map = {
                "Allocation Files": "alloc_",
                "Current Month Paid Files": "paid_current_",
                "Previous Months Paid Files": "paid_prev_"
            }
            for pname in process_data.keys():
                file_path = os.path.join(CACHE_DIR, f"{prefix_map[file_type]}{pname}.csv")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    st.success(f"✅ Deleted {file_type} for {pname}")
                else:
                    st.info(f"ℹ️ File not found for {pname}")

    if st.button("🔓 Logout"):
        st.session_state.authenticated = False
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        st.rerun()
