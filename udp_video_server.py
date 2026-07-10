"""
UDP Video Server - siaran CrowdCast.
Membaca video yang sedang aktif (broadcast.get_now_playing) lalu menyiarkannya
frame-per-frame via UDP ke semua penonton (melalui udp_receiver di Flask).

Perilaku:
  - Video habis  -> loop dari awal (siaran tidak pernah mati).
  - Ada upload baru (now_playing berubah) -> switch ke video baru dari awal.
  - Video lama (hasil upload) dihapus setelah di-switch, supaya disk tidak penuh.
  - Belum ada video sama sekali -> idle (tidak mengirim apa-apa).

Tiap frame dipecah jadi beberapa chunk (header: frame_id, total, index) karena 1
datagram UDP dibatasi ~65 KB. Frame yang hilang = frame drop (perilaku khas UDP).
"""

import socket
import time
import struct
import random
import os

import cv2
import numpy as np

import config
import broadcast

CHUNK_SIZE = 40000
# stream_id (u32), frame_id (u32), total chunk (u16), index chunk (u16), posisi putar ms (u32).
# - pos_ms: dipakai klien untuk menyelaraskan audio (HTTP) dengan video (UDP).
# - stream_id: identitas proses streamer. Kalau ada dua streamer jalan bersamaan, penerima
#   mengunci salah satu dan mengabaikan yang lain (dulu keduanya rebutan -> siaran lompat-lompat).
HEADER = struct.Struct("!IIHHI")
STREAM_ID = random.getrandbits(32)
# 960x540 supaya teks/slide terbaca jelas. Frame ~55 KB -> dipecah jadi 2 chunk UDP.
# (Ini keuntungan punya chunking: resolusi tidak dibatasi ukuran 1 datagram.)
JPEG_QUALITY = 70
FRAME_SIZE = (960, 540)


def _is_uploaded(path: str) -> bool:
    """True kalau path berada di dalam folder upload (bukan channel default)."""
    try:
        up = os.path.abspath(config.UPLOAD_DIR)
        return os.path.commonpath([os.path.abspath(path), up]) == up
    except ValueError:
        return False


def _fit(frame, size):
    """
    Skala frame agar muat di kanvas `size` (fixed) sambil menjaga rasio asli.
    Sisa area diisi hitam -> video portrait tampil dengan bar kiri-kanan (pillarbox),
    tidak ketarik gepeng. Ukuran output tetap konsisten.
    """
    tw, th = size
    h, w = frame.shape[:2]
    scale = min(tw / w, th / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(frame, (nw, nh))
    canvas = np.zeros((th, tw, 3), dtype=np.uint8)
    x, y = (tw - nw) // 2, (th - nh) // 2
    canvas[y:y + nh, x:x + nw] = resized
    return canvas


def _open(path: str):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        cap.release()
        return None, 25.0
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    return cap, fps


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (config.UDP_VIDEO_HOST, config.UDP_VIDEO_PORT)

    print("=" * 50)
    print("  CrowdCast UDP Video Server")
    print(f"  Menyiarkan ke {target[0]}:{target[1]}")
    print(f"  stream_id: {STREAM_ID}")
    print("=" * 50)

    current = None
    cap = None
    fps = 25.0
    delay = 0.04
    frame_id = 0
    next_frame_at = time.perf_counter()   # jadwal frame berikutnya (jaga tempo real-time)

    try:
        while True:
            desired = broadcast.get_now_playing()

            # ── ganti sumber siaran ──
            if desired != current:
                old = current
                if cap is not None:
                    cap.release()
                    cap = None
                # hapus video lama (hanya kalau hasil upload, bukan channel default)
                if old and old != desired and _is_uploaded(old) and os.path.isfile(old):
                    try:
                        os.remove(old)
                        print(f"[UDP] video lama dihapus: {os.path.basename(old)}")
                    except OSError as e:
                        print(f"[UDP] gagal hapus video lama: {e}")
                current = desired
                if desired:
                    cap, fps = _open(desired)
                    delay = 1.0 / (fps or 25.0)
                    next_frame_at = time.perf_counter()
                    if cap:
                        print(f"[UDP] sekarang menyiarkan: {os.path.basename(desired)} ({fps:.0f} fps)")

            # ── belum ada video / gagal buka ──
            if cap is None:
                time.sleep(0.3)
                continue

            ret, frame = cap.read()
            if not ret:                                   # video habis -> loop
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                next_frame_at = time.perf_counter()
                continue

            # posisi putar frame ini (ms) -> dipakai klien untuk menyelaraskan audio
            pos_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC) or 0)
            if pos_ms <= 0:                               # sebagian codec tidak isi POS_MSEC
                pos_ms = int((cap.get(cv2.CAP_PROP_POS_FRAMES) or 0) / (fps or 25.0) * 1000)

            frame = _fit(frame, FRAME_SIZE)
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ok:
                continue

            data = buf.tobytes()
            total = (len(data) + CHUNK_SIZE - 1) // CHUNK_SIZE
            for idx in range(total):
                part = data[idx * CHUNK_SIZE:(idx + 1) * CHUNK_SIZE]
                sock.sendto(HEADER.pack(STREAM_ID, frame_id, total, idx, pos_ms) + part, target)

            frame_id = (frame_id + 1) % (2 ** 32)

            # Jaga tempo real-time: jadwalkan frame berikutnya berdasarkan jam, bukan
            # sleep tetap. Kalau pakai sleep(delay), waktu encode/kirim ikut menambah
            # jeda -> siaran jalan lebih lambat dari 1x, dan audio (yang selalu 1x)
            # jadi menyalip lalu ditarik mundur terus.
            next_frame_at += delay
            lag = next_frame_at - time.perf_counter()
            if lag > 0:
                time.sleep(lag)
            else:
                next_frame_at = time.perf_counter()   # terlambat -> jangan menumpuk utang
    except KeyboardInterrupt:
        print("\n[INFO] UDP server dihentikan.")
    finally:
        if cap is not None:
            cap.release()
        sock.close()


if __name__ == "__main__":
    main()
