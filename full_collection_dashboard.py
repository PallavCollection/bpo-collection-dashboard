
import streamlit as st
import pandas as pd
import io
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="📊 Full Collection Dashboard", layout="wide")
st.title("📊 BPO Collection Dashboard (Multi-Process + Same-Date Comparison)")

st_autorefresh(interval=60 * 1000, key="refresh")

# --- Upload Files ---
st.sidebar.header("📂 Upload Allocation & Paid Files (Multiple Processes)")
alloc_files = st.sidebar.file_uploader("Upload Allocation Files", type="xlsx", accept_multiple_files=True)
paid_files = st.sidebar.file_uploader("Upload Paid Files", type="xlsx", accept_multiple_files=True)
target_rate = st.sidebar.number_input("🎯 Target Recovery %", 0.0, 100.0, 80.0)

# === Process Allocation + Paid ===
process_data = {}
if alloc_files and paid_files:
    paid_dict = {}
    for pf in paid_files:
        key = pf.name.split("_")[0].strip().upper()
        paid_dict[key] = pd.read_excel(pf)

    for af in alloc_files:
        pname = af.name.split("_")[0].strip().upper()
        if pname not in paid_dict:
            continue

        alloc_df = pd.read_excel(af)
        paid_df = paid_dict[pname]

        for df in [alloc_df, paid_df]:
            df.columns = df.columns.str.strip().str.lower()
            df['date'] = pd.to_datetime(df['date'])

        alloc_df.rename(columns={'amount': 'allocated_amount'}, inplace=True)
        paid_df.rename(columns={'amount': 'paid_amount'}, inplace=True)

        df = pd.merge(alloc_df, paid_df, on=['account_no', 'date'], how='outer')
        df.fillna(0, inplace=True)
        df['week'] = df['date'].dt.to_period('W').apply(lambda r: r.start_time)
        df['month'] = df['date'].dt.to_period('M').astype(str)
        df['process'] = pname
        process_data[pname] = df

# === Process View ===
if process_data:
    selected_process = st.selectbox("🔍 Select Process", list(process_data.keys()))
    df = process_data[selected_process]

    with st.sidebar.expander("🔎 Filters"):
        agents = df['agent_alloc'].dropna().unique().tolist() if 'agent_alloc' in df else []
        buckets = df['bucket'].dropna().unique().tolist() if 'bucket' in df else []
        selected_agents = st.multiselect("Agent(s)", agents, default=agents)
        selected_buckets = st.multiselect("Bucket(s)", buckets, default=buckets)
        if selected_agents:
            df = df[df['agent_alloc'].isin(selected_agents)]
        if selected_buckets:
            df = df[df['bucket'].isin(selected_buckets)]

    total_alloc = df['allocated_amount'].sum()
    total_paid = df['paid_amount'].sum()
    recovery_rate = (total_paid / total_alloc * 100) if total_alloc else 0
    delta = recovery_rate - target_rate

    st.metric("💰 Allocated", f"₹{total_alloc:,.0f}")
    st.metric("✅ Paid", f"₹{total_paid:,.0f}")
    st.metric("📈 Recovery %", f"{recovery_rate:.2f}%")
    st.metric("🎯 Target vs Actual", f"{recovery_rate:.2f}% vs {target_rate:.2f}%", delta=f"{delta:.2f}%")

    if 'agent_alloc' in df:
        ag = df.groupby('agent_alloc').agg({'allocated_amount':'sum','paid_amount':'sum'}).reset_index()
        ag['recovery%'] = ag['paid_amount'] / ag['allocated_amount'] * 100
        st.subheader("👤 Agent-wise Summary")
        st.dataframe(ag.style.format({'allocated_amount': '₹{:.0f}', 'paid_amount': '₹{:.0f}', 'recovery%': '{:.2f}%'}))

    if 'bucket' in df:
        bg = df.groupby('bucket').agg({'allocated_amount':'sum','paid_amount':'sum'}).reset_index()
        bg['recovery%'] = bg['paid_amount'] / bg['allocated_amount'] * 100
        st.subheader("🗂️ Bucket-wise Summary")
        st.dataframe(bg.style.format({'allocated_amount': '₹{:.0f}', 'paid_amount': '₹{:.0f}', 'recovery%': '{:.2f}%'}))

    wk = df.groupby('week').agg({'allocated_amount':'sum','paid_amount':'sum'}).reset_index()
    wk['recovery%'] = wk['paid_amount'] / wk['allocated_amount'] * 100
    st.subheader("📆 Weekly Trend")
    st.line_chart(wk.set_index('week')[['allocated_amount', 'paid_amount']])

    mo = df.groupby('month').agg({'allocated_amount':'sum','paid_amount':'sum'}).reset_index()
    mo['recovery%'] = mo['paid_amount'] / mo['allocated_amount'] * 100
    st.subheader("🗓️ Monthly Summary")
    st.dataframe(mo.style.format({'allocated_amount': '₹{:.0f}', 'paid_amount': '₹{:.0f}', 'recovery%': '{:.2f}%'}))

    def to_excel(download_df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            download_df.to_excel(writer, index=False, sheet_name="Data")
        output.seek(0)
        return output

    st.download_button("📥 Download This Process Report", data=to_excel(df), file_name=f"{selected_process}_report.xlsx")

# === SAME-DATE COMPARISON ===
st.header("📅 Same-Date Recovery Comparison")
same_date_files = st.file_uploader("Upload Paid Files from Previous Months", type="xlsx", accept_multiple_files=True, key="same_date")

if same_date_files:
    dfs = []
    for file in same_date_files:
        d = pd.read_excel(file)
        d['file'] = file.name
        d['date'] = pd.to_datetime(d['date'])
        d['day'] = d['date'].dt.day
        dfs.append(d)

    merged = pd.concat(dfs)
    grouped = merged.groupby(['day', 'file']).agg({'amount': 'sum'}).reset_index()
    summary = grouped.groupby('day')['amount'].agg(['max', 'mean', 'min']).reset_index()
    summary.rename(columns={'max': '💰 Best ₹', 'mean': '📊 Avg ₹', 'min': '🔻 Low ₹'}, inplace=True)

    st.subheader("📊 Same-Day Summary Across Months")
    st.dataframe(summary.style.format({'💰 Best ₹': '₹{:.0f}', '📊 Avg ₹': '₹{:.0f}', '🔻 Low ₹': '₹{:.0f}'}))
else:
    st.info("Upload multiple paid files from past months to enable same-date recovery analysis.")
