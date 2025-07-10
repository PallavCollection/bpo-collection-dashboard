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

    # Place your old processing and merging logic here (files: df_paid_prev, df_paid_current, df_alloc, etc.)
    # Make sure the data is populated before the below block.

    # --- Daily Comparison: Current vs Previous Month ---
    if (
        'df_paid_prev' in locals() and isinstance(df_paid_prev, pd.DataFrame) and not df_paid_prev.empty and 'Payment_Date' in df_paid_prev.columns and
        'df_paid_current' in locals() and isinstance(df_paid_current, pd.DataFrame) and not df_paid_current.empty and 'Payment_Date' in df_paid_current.columns
    ):
        st.markdown("### 🏆 Daily Best Performers: Current vs Previous Month")

        df_prev_daily = df_paid_prev.copy()
        df_prev_daily['Payment_Date'] = pd.to_datetime(df_prev_daily['Payment_Date'], errors='coerce')

        df_curr_daily = df_paid_current.copy()
        df_curr_daily['Payment_Date'] = pd.to_datetime(df_curr_daily['Payment_Date'], errors='coerce')

        curr_group = df_curr_daily.groupby('Payment_Date')['Paid_Amount'].sum().reset_index(name='Current_Month')
        prev_group = df_prev_daily.groupby('Payment_Date')['Paid_Amount'].sum().reset_index(name='Previous_Month')

        daily_compare = pd.merge(curr_group, prev_group, on='Payment_Date', how='outer').fillna(0)
        daily_compare['Payment_Date'] = daily_compare['Payment_Date'].dt.date

        st.dataframe(daily_compare.sort_values('Payment_Date', ascending=False))

        st.markdown("### 📊 Daily Performance Comparison Chart")
        fig = px.bar(daily_compare.sort_values('Payment_Date'),
                     x='Payment_Date',
                     y=['Current_Month', 'Previous_Month'],
                     barmode='group',
                     title="Daily Recovery: Current vs Previous Month",
                     labels={'value': 'Paid Amount', 'Payment_Date': 'Date'},
                     color_discrete_sequence=['#1f77b4', '#ff7f0e'])
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.line(daily_compare.sort_values('Payment_Date'),
                       x='Payment_Date',
                       y=['Current_Month', 'Previous_Month'],
                       title="Line Trend: Current vs Previous",
                       markers=True,
                       labels={'value': 'Paid Amount', 'Payment_Date': 'Date'},
                       color_discrete_sequence=['#1f77b4', '#ff7f0e'])
        st.plotly_chart(fig2, use_container_width=True)
