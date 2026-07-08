"""
State siaran CrowdCast (tanpa DB).
Menyimpan "video mana yang sedang disiarkan" di 1 file penunjuk: videos/now_playing.txt.
Dipakai bersama oleh Flask (menulis saat ada upload baru) dan udp_video_server (membaca).
"""

import os
import threading

import config

_lock = threading.Lock()


def get_now_playing() -> str | None:
    """
    Path video yang sedang disiarkan. Kalau belum ada yang di-upload,
    fallback ke channel default (videos/sample.mp4) bila tersedia; else None.
    """
    try:
        with open(config.NOW_PLAYING_FILE, "r", encoding="utf-8") as f:
            path = f.read().strip()
        if path and os.path.isfile(path):
            return path
    except OSError:
        pass
    if os.path.isfile(config.VIDEO_FILE):
        return config.VIDEO_FILE
    return None


def set_now_playing(path: str):
    """Set video aktif (tulis atomik supaya tidak terbaca setengah oleh streamer)."""
    os.makedirs(config.VIDEOS_DIR, exist_ok=True)
    tmp = config.NOW_PLAYING_FILE + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(path)
        os.replace(tmp, config.NOW_PLAYING_FILE)
