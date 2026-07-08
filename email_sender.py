"""
Kirim email via Gmail SMTP (smtplib bawaan Python).
Butuh GMAIL_ADDRESS + GMAIL_APP_PASSWORD di .env.
Kalau kredensial kosong, kode OTP di-print ke terminal (mode dev) supaya tetap bisa dites.
"""

import smtplib
import ssl
from email.message import EmailMessage

import config


def _send(to_email: str, subject: str, body: str) -> bool:
    # Mode dev: tanpa kredensial, cukup print ke terminal
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        print("\n" + "=" * 50, flush=True)
        print("[EMAIL DEV MODE] Kredensial Gmail kosong, email tidak dikirim.", flush=True)
        print(f"  To     : {to_email}", flush=True)
        print(f"  Subject: {subject}", flush=True)
        print(f"  Body   :\n{body}", flush=True)
        print("=" * 50 + "\n", flush=True)
        return True

    msg = EmailMessage()
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Gagal kirim ke {to_email}: {e}")
        return False


def send_otp_email(to_email: str, username: str, code: str) -> bool:
    subject = "Kode Verifikasi NetVault"
    body = (
        f"Halo {username},\n\n"
        f"Kode verifikasi (OTP) kamu adalah: {code}\n\n"
        f"Kode berlaku 5 menit. Jangan bagikan ke siapa pun.\n\n"
        f"— NetVault"
    )
    return _send(to_email, subject, body)


def send_login_alert(to_email: str, username: str) -> bool:
    subject = "Login Berhasil - NetVault"
    body = (
        f"Halo {username},\n\n"
        f"Akun kamu baru saja login ke NetVault.\n"
        f"Kalau ini bukan kamu, segera ganti password.\n\n"
        f"— NetVault"
    )
    return _send(to_email, subject, body)
