
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

df = pd.read_excel("daily_paid_today.xlsx")
df.columns = df.columns.str.lower()
total_alloc = df['allocated_amount'].sum()
total_paid = df['paid_amount'].sum()
rate = (total_paid / total_alloc * 100) if total_alloc else 0

target = 80
if rate < target:
    msg = f"Alert 🚨\nToday's Recovery Rate is {rate:.2f}% (Target: {target}%)"
    sender = "your_email@gmail.com"
    receiver = "your_email@gmail.com"
    password = "your_app_password"

    mime = MIMEText(msg)
    mime['Subject'] = "Daily Recovery Alert"
    mime['From'] = sender
    mime['To'] = receiver

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(mime)

    print("Email sent!")
else:
    print("Target achieved. No email.")
