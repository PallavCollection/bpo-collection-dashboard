import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- Config ---
st.set_page_config(page_title="✨ Collection Dashboard", layout="wide")

# --- Header fixer ---
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

# --- Auth ---
def authenticate_user(email, password):
    return email == "jjagarbattiudyog@gmail.com" and password == "Sanu@1998"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""

if not st.session_state.authenticated:
    st.title("🔐 Secure Access")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.success("✅ Logged in successfully!")
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
    st.stop()

# --- Role ---
is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

# --- Session store ---
if 'processes' not in st.session_state:
    st.session_state.processes = {}

# --- Handle redirect after process creation ---
if st.session_state.get("just_created"):
    selected_process = st.session_state["selected_process"]
    st.session_state["just_created"] = False
else:
    selected_process = st.selectbox("📍 Select or Create Process", ["➕ Add New Process"] + list(st.session_state.processes.keys()))

# --- Add new process form ---
if selected_process == "➕ Add New Process":
    with st.form("create_process"):
        new_process = st.text_input("🆕 Enter new process name")
        if st.form_submit_button("Create") and new_process:
            st.session_state.processes[new_process] = {
                'alloc_files': [],
                'paid_current_files': [],
                'paid_prev_files': []
            }
            st.session_state["selected_process"] = new_process
            st.session_state["just_created"] = True
            st.experimental_rerun()

# --- Existing Process UI ---
elif selected_process in st.session_state.processes:
    st.markdown(f"### 📂 Process: `{selected_process}`")

    # Rename
    new_name = st.text_input("✏️ Rename this process", selected_process)
    if new_name and new_name != selected_process:
        st.session_state.processes[new_name] = st.session_state.processes.pop(selected_process)
        selected_process = new_name
        st.success("✅ Process renamed.")
        st.experimental_rerun()

    # Delete
    if is_editor and st.button("🗑️ Delete This Process"):
        del st.session_state.processes[selected_process]
        st.success("✅ Process deleted.")
        st.experimental_rerun()

    # File uploader w/ delete
    def file_uploader_block(label, key, list_key):
        st.subheader(label)
        uploaded = st.file_uploader(label, type=["xlsx"], accept_multiple_files=True, key=key)
        if uploaded:
            st.session_state.processes[selected_process][list_key].extend(uploaded)
        for i, f in enumerate(st.session_state.processes[selected_process][list_key]):
            st.text(f.name)
            if is_editor and st.button(f"❌ Remove {f.name}", key=f"{key}_del_{i}"):
                del st.session_state.processes[selected_process][list_key][i]
                st.experimental_rerun()

    file_uploader_block("📁 Allocation Files", f"alloc_{selected_process}", "alloc_files")
    file_uploader_block("📅 Current Month Paid Files", f"paid_current_{selected_process}", "paid_current_files")
    file_uploader_block("🗓️ Previous Month Paid Files", f"paid_prev_{selected_process}", "paid_prev_files")

    # Show report
    data = st.session_state.processes[selected_process]
    if data['alloc_files'] and (data['paid_current_files'] or data['paid_prev_files']):
        df_alloc = pd.concat([clean_headers(pd.read_excel(f)) for f in data['alloc_files']], ignore_index=True)
        df_paid_current = pd.concat([clean_headers(pd.read_excel(f)) for f in data['paid_current_files']], ignore_index=True) if data['paid_current_files'] else pd.DataFrame()
        df_paid_prev = pd.concat([clean_headers(pd.read_excel(f)) for f in data['paid_prev_files']], ignore_index=True) if data['paid_prev_files'] else pd.DataFrame()
        df_paid_all = pd.concat([df_paid_current, df_paid_prev], ignore_index=True)

        df_all = pd.merge(df_alloc, df_paid_all, on='Loan_ID', how='left')
        df_all['Paid_Amount'] = df_all['Paid_Amount'].fillna(0)
        df_all['Recovery %'] = (df_all['Paid_Amount'] / df_all['Allocated_Amount']).round(2)
        df_all['Balance'] = df_all['Allocated_Amount'] - df_all['Paid_Amount']

        total_alloc = df_all['Allocated_Amount'].sum()
        total_paid_all = df_all['Paid_Amount'].sum()
        recovery_all = round((total_paid_all / total_alloc)*100, 2) if total_alloc else 0
        total_paid_current = df_paid_current['Paid_Amount'].sum() if not df_paid_current.empty else 0
        recovery_current = round((total_paid_current / total_alloc)*100, 2) if total_alloc else 0

        st.metric("💰 Total Allocated", f"₹{total_alloc:,.0f}")
        st.metric("✅ Paid - All Time", f"₹{total_paid_all:,.0f}")
        st.metric("🟩 Paid - Current Month", f"₹{total_paid_current:,.0f}")
        st.metric("📈 Recovery % (All Time)", f"{recovery_all}%")

        with st.expander("📋 View All-Time Data"):
            st.dataframe(df_all)

        with st.expander("📋 View Current Month Data"):
            st.dataframe(df_paid_current)

        if 'Payment_Date' in df_paid_current.columns:
            st.markdown("### 📅 Daily Payment Trend")
            trend = df_paid_current.groupby('Payment_Date')['Paid_Amount'].sum().reset_index()
            fig = px.line(trend, x='Payment_Date', y='Paid_Amount', markers=True)
            st.plotly_chart(fig, use_container_width=True)

        if 'Bucket' in df_all.columns:
            st.markdown("### 📦 Bucket-wise Recovery")
            summary = df_all.groupby('Bucket').agg({'Allocated_Amount':'sum', 'Paid_Amount':'sum'}).reset_index()
            summary['Recovery %'] = (summary['Paid_Amount'] / summary['Allocated_Amount'] * 100).round(2)
            fig2 = px.bar(summary, x='Bucket', y=['Allocated_Amount','Paid_Amount'], barmode='group')
            st.plotly_chart(fig2, use_container_width=True)

        if 'Agency_Name' in df_paid_current.columns and 'Cure_Rate' in df_paid_current.columns:
            st.markdown("### 🏢 Agency Performance Comparison")
            agency_data = df_paid_current[['Agency_Name', 'Cure_Rate']].dropna()
            perf = agency_data.groupby('Agency_Name').mean().reset_index()
            fig3 = px.bar(perf, x='Agency_Name', y='Cure_Rate', title='Cure Rate by Agency', text='Cure_Rate')
            st.plotly_chart(fig3, use_container_width=True)

    else:
        st.info("👈 Please upload allocation & paid files to generate the report.")

if st.button("🔓 Logout"):
    st.session_state.authenticated = False
    st.experimental_rerun()
