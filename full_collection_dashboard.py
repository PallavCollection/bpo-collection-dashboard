import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime, timedelta
import json
import io

st.set_page_config(page_title="📊 Collection BPO Dashboard", layout="wide")
st.title("📊 Collection BPO Dashboard")

ADMIN_EMAIL = "jjagarbattiudyog@gmail.com"
ADMIN_PASSWORD = "Sanu@1998"
VIEW_ONLY_PASSWORD = "login6"

def save_session(data):
    with open("session.json", "w") as f:
        json.dump(data, f)

def load_session():
    if os.path.exists("session.json"):
        with open("session.json", "r") as f:
            return json.load(f)
    return {}

def authenticate_user(email, password):
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return "editor"
    elif password == VIEW_ONLY_PASSWORD:
        return "viewer"
    else:
        return None

session_data = load_session()
now = datetime.now()
if 'last_login' in session_data:
    last_login = datetime.strptime(session_data['last_login'], "%Y-%m-%d %H:%M:%S")
    if now - last_login < timedelta(hours=24):
        st.session_state.authenticated = True
        st.session_state.user_email = session_data.get('user_email', '')
        st.session_state.role = session_data.get('role', 'viewer')
    else:
        st.session_state.authenticated = False
else:
    st.session_state.authenticated = False

if not st.session_state.get("authenticated"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = authenticate_user(email, password)
        if role:
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.session_state.role = role
            save_session({'last_login': now.strftime("%Y-%m-%d %H:%M:%S"), 'user_email': email, 'role': role})
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. View-only mode enabled.")
    st.stop()

is_editor = st.session_state.role == "editor"

if st.sidebar.button("🔐 Logout"):
    st.session_state.clear()
    st.rerun()

if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()

if time.time() - st.session_state['last_refresh'] > 900:
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

st.sidebar.markdown(f"⏰ Last refresh: {datetime.fromtimestamp(st.session_state['last_refresh']).strftime('%Y-%m-%d %H:%M:%S')}")
if st.sidebar.button("🔄 Manual Refresh"):
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

EXPECTED_HEADERS = {
    'alloc': ['Loan ID', 'Customer Name', 'Amount'],
    'paid': ['Loan ID', 'Paid Amount'],
    'prev_paid': ['Loan ID', 'Previous Paid Amount'],
    'agent_perf': ['Ranking', 'Week', 'Agent Name', 'Total ca', 'Duration', 'PTP']
}

HEADER_MAPPING = {
    'loanid': 'Loan ID',
    'custname': 'Customer Name',
    'amt': 'Amount',
    'paidamt': 'Paid Amount',
    'ranking': 'Ranking',
    'week': 'Week',
    'agentname': 'Agent Name',
    'duration': 'Duration'
}

def auto_correct_headers(df):
    df.columns = [col.strip().lower().replace(" ", "") for col in df.columns]
    rename_map = {}
    for col in df.columns:
        for key, val in HEADER_MAPPING.items():
            if key in col:
                rename_map[col] = val
                break
    df.rename(columns=rename_map, inplace=True)
    return df

processes = st.sidebar.session_state.get("processes", ["Process_1"])
selected_process = st.selectbox("🔽 Select Process", processes)

if is_editor and st.sidebar.button("➕ Add Process"):
    new_process = f"Process_{len(processes)+1}"
    processes.append(new_process)
    st.sidebar.session_state["processes"] = processes
    st.experimental_rerun()

st.sidebar.subheader(selected_process)

uploaded_files = {}
file_labels = ['Allocation Files', 'Current Month Paid', 'Previous Months Paid', 'Agent Performance']
file_keys = ['alloc', 'paid', 'prev_paid', 'agent_perf']

for label, key in zip(file_labels, file_keys):
    st.sidebar.markdown(f"📁 {label}")
    uploaded_file = st.sidebar.file_uploader(f"Upload {label}", type=["xlsx"], key=f"{selected_process}_{key}")
    if uploaded_file:
        save_path = f"data/{selected_process}_{key}.xlsx"
        os.makedirs("data", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())

    uploaded_files[key] = f"data/{selected_process}_{key}.xlsx"

if st.sidebar.button("🗑️ Delete Data"):
    for f in uploaded_files.values():
        if os.path.exists(f):
            os.remove(f)
    st.success("🧹 Data deleted.")
    st.experimental_rerun()

try:
    df_alloc = pd.read_excel(uploaded_files['alloc'])
    df_paid = pd.read_excel(uploaded_files['paid'])
    df_prev = pd.read_excel(uploaded_files['prev_paid'])
    df_agent = pd.read_excel(uploaded_files['agent_perf'])

    df_alloc = auto_correct_headers(df_alloc)
    df_paid = auto_correct_headers(df_paid)
    df_prev = auto_correct_headers(df_prev)
    df_agent = auto_correct_headers(df_agent)

    df_all = pd.merge(df_alloc, df_paid, on="Loan ID", how="left")
    df_all = pd.merge(df_all, df_prev, on="Loan ID", how="left")

    st.subheader("📊 Dashboard")
    st.dataframe(df_all)

    st.download_button(
        label="📥 Download Merged Report (Excel)",
        data=df_all.to_excel(index=False, engine='xlsxwriter'),
        file_name=f"{selected_process}_merged_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.subheader("📋 Agent Performance")
    selected_week = st.selectbox("Filter by Week", options=["All"] + sorted(df_agent['Week'].unique().tolist()))
    if selected_week != "All":
        df_agent = df_agent[df_agent['Week'] == selected_week]

    st.dataframe(df_agent.sort_values(by='Ranking'))

    st.markdown("### 📈 Agent Performance Charts")
    col1, col2 = st.columns(2)
    with col1:
        if 'Total ca' in df_agent.columns:
            fig1 = px.bar(df_agent, x='Agent Name', y='Total ca', title='Total Calls by Agent')
            st.plotly_chart(fig1)
    with col2:
        if 'PTP' in df_agent.columns:
            fig2 = px.bar(df_agent, x='Agent Name', y='PTP', title='PTP by Agent')
            st.plotly_chart(fig2)

    # KPIs
    st.markdown("### 📊 Key Performance Indicators")
    avg_duration = df_agent['Duration'].mean() if 'Duration' in df_agent.columns else 0
    conversion_rate = (df_agent['PTP'].sum() / df_agent['Total ca'].sum()) * 100 if 'PTP' in df_agent.columns and 'Total ca' in df_agent.columns else 0
    st.metric("Average Duration", f"{avg_duration:.2f} min")
    st.metric("Conversion Rate (PTP/Total Calls)", f"{conversion_rate:.2f}%")

    # Week-over-week comparison
    st.markdown("### 📉 Week-over-Week Trends")
    if 'Week' in df_agent.columns and 'PTP' in df_agent.columns:
        week_summary = df_agent.groupby('Week').agg({'PTP': 'sum', 'Total ca': 'sum'}).reset_index()
        week_summary['Conversion Rate'] = (week_summary['PTP'] / week_summary['Total ca']) * 100
        fig_line = px.line(week_summary, x='Week', y=['PTP', 'Total ca', 'Conversion Rate'], markers=True, title='PTP, Total Calls & Conversion Rate Over Weeks')
        st.plotly_chart(fig_line)

except Exception as e:
    st.warning(f"⚠️ Unable to render dashboard. Ensure files are uploaded with correct structure.\nError: {e}")
