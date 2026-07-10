"""
Konfigurasi terpusat NetVault.
Semua nilai sensitif dibaca dari file .env (lihat .env.example).
"""

import os
from dotenv import load_dotenv

load_dotenv()  # baca file .env kalau ada

# Flask
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-ganti-di-produksi")

# Email (Gmail SMTP)
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Backend socket TCP (file upload)
TCP_FILE_HOST = os.getenv("TCP_FILE_HOST", "127.0.0.1")
TCP_FILE_PORT = int(os.getenv("TCP_FILE_PORT", "9010"))

# Backend socket UDP (video streaming)
UDP_VIDEO_HOST = os.getenv("UDP_VIDEO_HOST", "127.0.0.1")
UDP_VIDEO_PORT = int(os.getenv("UDP_VIDEO_PORT", "9020"))

# Batas ukuran video upload: 95 MB.
# Cloudflare (plan gratis) menolak request body > 100 MB, dan yang dihitung adalah
# seluruh body (file + overhead multipart), jadi disisakan margin.
MAX_FILE_SIZE = 95 * 1024 * 1024

# Ekstensi video yang boleh di-upload
ALLOWED_VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm"}

# Lokasi penyimpanan
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "storage", "uploads")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
VIDEOS_DIR = os.path.join(os.path.dirname(__file__), "videos")
VIDEO_FILE = os.path.join(VIDEOS_DIR, "sample.mp4")           # channel default (fallback)
NOW_PLAYING_FILE = os.path.join(VIDEOS_DIR, "now_playing.txt")  # penunjuk video aktif
