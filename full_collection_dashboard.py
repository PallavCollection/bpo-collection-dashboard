# Enhanced Streamlit Collection Dashboard
import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime

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
    "agencyname": "Agency_Name",
    "curerate": "Cure_Rate"
}

def clean_headers(df):
    df.columns = [HEADER_MAPPING.get(col.strip().lower().replace(" ", "_"), col.strip()) for col in df.columns]
    return df

# ---- Auth Section ----
def authenticate_user(email, password):
    return email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""

if not st.session_state.authenticated:
    st.title("🔐 Secure Access")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")

    if login_btn:
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.success("✅ Logged in successfully!")
            st.experimental_rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
else:
    st.set_page_config(page_title="✨ Beautiful Collection Dashboard", layout="wide")
    st.markdown("<h1 style='text-align: center; color: navy;'>📊 Collection BPO Dashboard</h1>", unsafe_allow_html=True)

    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    # Initialize session state for persistent process storage
    if 'processes' not in st.session_state:
        st.session_state.processes = {}

    # --- Process Selector (top) ---
# Handle redirect to newly created process
if st.session_state.get("just_created"):
    selected_process = st.session_state["selected_process"]
    st.session_state["just_created"] = False
    selected_process = st.selectbox("📍 Select or Create Process", ["➕ Add New Process"] + list(st.session_state.processes.keys()))

    if selected_process == "➕ Add New Process":
        with st.form("new_process_form"):
            new_process_name = st.text_input("🔤 Enter new process name")
            submitted = st.form_submit_button("➕ Create")
            if submitted and new_process_name:
    st.session_state.processes[new_process_name] = {
        'alloc_files': [],
        'paid_current_files': [],
        'paid_prev_files': []
    }
    st.session_state["selected_process"] = new_process_name
    st.session_state["just_created"] = True
    else:
        process_data = st.session_state.processes[selected_process]

        # Editable name
        new_name = st.text_input("✏️ Rename Process", selected_process)
        if new_name and new_name != selected_process:
            st.session_state.processes[new_name] = st.session_state.processes.pop(selected_process)
            selected_process = new_name
            st.experimental_rerun()

        st.sidebar.markdown("---")
        st.sidebar.subheader(f"📂 Upload Files for: {selected_process}")

        # Upload file sections with delete option
        def file_uploader_with_delete(label, key, file_list_key):
            uploaded = st.sidebar.file_uploader(label, type=["xlsx"], accept_multiple_files=True, key=key)
            if uploaded:
                process_data[file_list_key].extend(uploaded)
            for i, f in enumerate(process_data[file_list_key]):
                st.sidebar.markdown(f"- {f.name}")
                if is_editor and st.sidebar.button(f"❌ Remove {f.name}", key=f"del_{key}_{i}"):
                    process_data[file_list_key].pop(i)
                    st.experimental_rerun()

        file_uploader_with_delete("📁 Allocation Files", f"alloc_{selected_process}", "alloc_files")
        file_uploader_with_delete("📅 Current Month Paid Files", f"paid_current_{selected_process}", "paid_current_files")
        file_uploader_with_delete("🗓️ Previous Months Paid Files", f"paid_prev_{selected_process}", "paid_prev_files")

        # Delete process button
        if is_editor and st.button("🗑️ Delete This Process"):
            del st.session_state.processes[selected_process]
            st.experimental_rerun()

        if process_data['alloc_files'] and (process_data['paid_current_files'] or process_data['paid_prev_files']):
            df_alloc = pd.concat([clean_headers(pd.read_excel(f)) for f in process_data['alloc_files']], ignore_index=True)
            df_paid_current = pd.concat([clean_headers(pd.read_excel(f)) for f in process_data['paid_current_files']], ignore_index=True) if process_data['paid_current_files'] else pd.DataFrame()
            df_paid_prev = pd.concat([clean_headers(pd.read_excel(f)) for f in process_data['paid_prev_files']], ignore_index=True) if process_data['paid_prev_files'] else pd.DataFrame()
            df_paid_all = pd.concat([df_paid_current, df_paid_prev], ignore_index=True)

            df_all = pd.merge(df_alloc, df_paid_all, on='Loan_ID', how='left')
            df_all['Paid_Amount'] = df_all['Paid_Amount'].fillna(0)
            df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount']).round(2)
            df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

            st.markdown(f"<h2 style='color: teal;'>📌 Dashboard: {selected_process}</h2>", unsafe_allow_html=True)

            total_alloc = df_all['Allocated_Amount'].sum()
            total_paid_all = df_all['Paid_Amount'].sum()
            recovery_all = round((total_paid_all / total_alloc)*100, 2) if total_alloc else 0

            total_paid_current = df_paid_current['Paid_Amount'].sum() if not df_paid_current.empty else 0
            recovery_current = round((total_paid_current / total_alloc)*100, 2) if total_alloc else 0

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Total Allocated", f"₹{total_alloc:,.0f}")
            col2.metric("✅ Paid - All Time", f"₹{total_paid_all:,.0f}")
            col3.metric("🟩 Paid - Current Month", f"₹{total_paid_current:,.0f}")
            col4.metric("📈 Recovery % (All Time)", f"{recovery_all}%")

            with st.expander("📋 View Current Month Data"):
                st.dataframe(df_paid_current)

            if not df_paid_current.empty and 'Payment_Date' in df_paid_current:
                st.markdown("### 📅 Daily Payment Trend (Current Month)")
                trend = df_paid_current.groupby('Payment_Date')['Paid_Amount'].sum().reset_index()
                fig = px.line(trend, x='Payment_Date', y='Paid_Amount', markers=True, title='Daily Payments', color_discrete_sequence=['navy'])
                st.plotly_chart(fig, use_container_width=True)

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

            # 🆕 Agency Performance Chart if data present
            if 'Agency_Name' in df_paid_current.columns and 'Cure_Rate' in df_paid_current.columns:
                st.markdown("### 🏢 Agency Performance Comparison - Current Month")
                perf_df = df_paid_current[['Agency_Name', 'Cure_Rate']].dropna()
                avg_perf = perf_df.groupby('Agency_Name').mean().reset_index()
                fig3 = px.bar(avg_perf, x='Agency_Name', y='Cure_Rate', title='Cure Rate by Agency (Current Month)', text='Cure_Rate')
                st.plotly_chart(fig3, use_container_width=True)

        else:
            st.info("👈 Please upload allocation & paid files to view the report.")

    if st.button("🔓 Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()
