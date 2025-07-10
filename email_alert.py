import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# --- Load today's paid data ---
try:
    df = pd.read_excel("daily_paid_today.xlsx")
    df.columns = df.columns.str.lower()
except Exception as e:
    print(f"❌ Failed to read data: {e}")
    exit()

# --- Calculate recovery ---
total_alloc = df['allocated_amount'].sum()
total_paid = df['paid_amount'].sum()
rate = (total_paid / total_alloc * 100) if total_alloc else 0

# --- Email Settings ---
target = 80  # Daily target %
sender = "your_email@gmail.com"
receiver = "your_email@gmail.com"
password = "your_app_password"  # Use Gmail App Password

# --- Compose and Send Email ---
if rate < target:
    msg = f"""
🚨 Daily Recovery Alert 🚨

Today's Recovery Rate: {rate:.2f}%
Target Recovery Rate: {target}%

Please take necessary action.

Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """
    mime = MIMEText(msg)
    mime['Subject'] = "⚠️ Recovery Alert: Target Not Met"
    mime['From'] = sender
    mime['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(mime)
        print("✅ Alert email sent.")
    except Exception as e:
        print(f"❌ Email send failed: {e}")
else:
    print(f"✅ Recovery met ({rate:.2f}%). No email sent.")
