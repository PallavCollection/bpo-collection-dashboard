import streamlit as st
import pandas as pd
import plotly.express as px
import io

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
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
else:
    st.set_page_config(page_title="✨ Beautiful Collection Dashboard", layout="wide")
    st.markdown("<h1 style='text-align: center; color: navy;'>📊 Collection BPO Dashboard</h1>", unsafe_allow_html=True)

    is_editor = st.session_state.user_email == "jjagarbattiudyog@gmail.com"

    if is_editor:
        num_processes = st.sidebar.number_input("Number of Processes", min_value=1, max_value=10, value=2)
    else:
        num_processes = 1

    process_data = {}

    for i in range(int(num_processes)):
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"📂 Process {i+1}")
        process_name = st.sidebar.text_input(f"Process {i+1} Name", value=f"Process_{i+1}", disabled=not is_editor)

        alloc_files = st.sidebar.file_uploader(
            f"📁 Allocation Files", type=["xlsx"], accept_multiple_files=True,
            key=f"alloc_{i}", disabled=not is_editor)

        paid_current_files = st.sidebar.file_uploader(
            f"📅 Current Month Paid Files", type=["xlsx"], accept_multiple_files=True,
            key=f"paid_current_{i}", disabled=not is_editor)

        paid_prev_files = st.sidebar.file_uploader(
            f"🗓️ Previous Months Paid Files", type=["xlsx"], accept_multiple_files=True,
            key=f"paid_prev_{i}", disabled=not is_editor)

        if alloc_files and (paid_current_files or paid_prev_files):
            df_alloc = pd.concat([clean_headers(pd.read_excel(f)) for f in alloc_files], ignore_index=True)
            df_paid_current = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_current_files], ignore_index=True) if paid_current_files else pd.DataFrame()
            df_paid_prev = pd.concat([clean_headers(pd.read_excel(f)) for f in paid_prev_files], ignore_index=True) if paid_prev_files else pd.DataFrame()
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
        selected_process = st.selectbox("📍 **Select Process to View Report**", list(process_data.keys()))
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
            if not df_current.empty:
                csv = df_current.to_csv(index=False).encode('utf-8')
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_current.to_excel(writer, index=False)
                st.download_button("⬇️ Download CSV", data=csv, file_name=f"{selected_process}_current.csv", mime='text/csv')
                st.download_button("⬇️ Download Excel", data=excel_buffer.getvalue(), file_name=f"{selected_process}_current.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        if not df_current.empty and 'Payment_Date' in df_current:
            st.markdown("### 📅 Daily Payment Trend (Current Month)")
            trend = df_current.groupby('Payment_Date')['Paid_Amount'].sum().reset_index()
            fig = px.line(trend, x='Payment_Date', y='Paid_Amount', markers=True,
                          title='Daily Payments', color_discrete_sequence=['navy'])
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 View All Time Data"):
            st.dataframe(df_all)
            if not df_all.empty:
                csv_all = df_all.to_csv(index=False).encode('utf-8')
                excel_all_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_all_buffer, engine='xlsxwriter') as writer:
                    df_all.to_excel(writer, index=False)
                st.download_button("⬇️ Download CSV (All)", data=csv_all, file_name=f"{selected_process}_all.csv", mime='text/csv')
                st.download_button("⬇️ Download Excel (All)", data=excel_all_buffer.getvalue(), file_name=f"{selected_process}_all.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

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

    if st.button("🔓 Logout"):
        st.session_state.authenticated = False
        st.rerun()
