# 📊 BPO Collection Dashboard

This is a secure and interactive Streamlit dashboard designed for BPO collection analysis. It compares allocation vs. recovery and includes a daily current vs. previous month performance tracker.

## 🚀 Features

- Secure login with session control
- Upload allocation and paid files (Current & Previous Month)
- Auto-clean column headers
- Daily performance comparison (current vs. previous)
- Charts: Bar + Line trends
- Download reports (CSV & Excel)
- Auto-refresh support
- Admin file delete option

## 🗂 File Uploads

Upload the following:
- `alloc_file.xlsx` – Allocation data
- `paid_curr_file.xlsx` – Paid file (current month)
- `paid_prev_file.xlsx` – Paid file (previous month)

> Ensure column headers like `loan_id`, `allocated_amount`, `paid_amount`, `payment_date`, `bucket`, `agency` are properly mapped.

## 🔒 Login

Use the following credentials:

- **Email:** `jjagarbattiudyog@gmail.com`
- **Password:** `Sanu@1998`

## 🛠 Run the App

```bash
pip install -r requirements.txt
streamlit run full_collection_dashboard.py
