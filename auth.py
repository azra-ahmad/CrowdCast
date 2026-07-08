"""
Autentikasi & manajemen user tanpa database.
- User disimpan di file JSON (users.json): { username: {password_hash, email, verified} }
- Password di-hash pakai werkzeug (bukan plaintext).
- OTP verifikasi email disimpan in-memory (hilang saat restart, wajar untuk kode sementara).
"""

import json
import os
import time
import random
import threading

from werkzeug.security import generate_password_hash, check_password_hash

import config

# Lock supaya baca/tulis users.json aman walau ada beberapa request
_users_lock = threading.Lock()

# Penyimpanan OTP sementara: { username: {"code": "123456", "expires": <epoch>} }
_otp_store: dict[str, dict] = {}
OTP_TTL = 300  # kode berlaku 5 menit


# ─── users.json ──────────────────────────────────────────────────────────────
def _load_users() -> dict:
    if not os.path.exists(config.USERS_FILE):
        return {}
    try:
        with open(config.USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict):
    with open(config.USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _resolve_key(users: dict, username: str) -> str | None:
    """Cari key username secara case-insensitive + trim. Return key asli atau None."""
    target = username.strip().lower()
    for key in users:
        if key.lower() == target:
            return key
    return None


def get_user(username: str) -> dict | None:
    with _users_lock:
        users = _load_users()
        key = _resolve_key(users, username)
        return users.get(key) if key else None


# ─── Registrasi & Login ──────────────────────────────────────────────────────
def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    """Daftar user baru (status belum terverifikasi). Return (sukses, pesan)."""
    username = username.strip()
    email = email.strip()

    if not username or not email or not password:
        return False, "Semua field wajib diisi."
    if len(username) > 20 or not username.replace("_", "").isalnum():
        return False, "Username maksimal 20 karakter, hanya huruf/angka/underscore."
    if "@" not in email or "." not in email:
        return False, "Format email tidak valid."
    if len(password) < 4:
        return False, "Password minimal 4 karakter."

    with _users_lock:
        users = _load_users()
        if _resolve_key(users, username):  # cek case-insensitive
            return False, "Username sudah dipakai."
        users[username] = {
            "password_hash": generate_password_hash(password),
            "email": email,
            "verified": False,
        }
        _save_users(users)
    return True, "Registrasi berhasil."


def check_login(username: str, password: str) -> tuple[bool, str]:
    """Cek kredensial login. Return (sukses, pesan)."""
    user = get_user(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return False, "Username atau password salah."
    if not user.get("verified"):
        return False, "Akun belum diverifikasi. Cek email untuk kode OTP."
    return True, "Login berhasil."


def set_verified(username: str):
    """Tandai user sudah verifikasi email."""
    with _users_lock:
        users = _load_users()
        key = _resolve_key(users, username)
        if key:
            users[key]["verified"] = True
            _save_users(users)


# ─── OTP ─────────────────────────────────────────────────────────────────────
def generate_otp(username: str) -> str:
    """Buat kode OTP 6 digit untuk username, simpan sementara."""
    code = f"{random.randint(0, 999999):06d}"
    _otp_store[username] = {"code": code, "expires": time.time() + OTP_TTL}
    return code


def verify_otp(username: str, code: str) -> tuple[bool, str]:
    """Cek OTP yang dimasukkan user."""
    entry = _otp_store.get(username)
    if not entry:
        return False, "Tidak ada kode aktif. Minta kirim ulang."
    if time.time() > entry["expires"]:
        _otp_store.pop(username, None)
        return False, "Kode sudah kadaluarsa. Minta kirim ulang."
    if code.strip() != entry["code"]:
        return False, "Kode OTP salah."
    _otp_store.pop(username, None)  # sekali pakai
    return True, "Verifikasi berhasil."
