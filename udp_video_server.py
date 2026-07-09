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
import os

import cv2
import numpy as np

import config
import broadcast

CHUNK_SIZE = 40000
HEADER = struct.Struct("!IHH")   # frame_id (uint32), total (uint16), index (uint16)
JPEG_QUALITY = 60
FRAME_SIZE = (640, 360)


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
    print("=" * 50)

    current = None
    cap = None
    delay = 0.04
    frame_id = 0

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
                    if cap:
                        print(f"[UDP] sekarang menyiarkan: {os.path.basename(desired)} ({fps:.0f} fps)")

            # ── belum ada video / gagal buka ──
            if cap is None:
                time.sleep(0.3)
                continue

            ret, frame = cap.read()
            if not ret:                                   # video habis -> loop
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = _fit(frame, FRAME_SIZE)
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ok:
                continue

            data = buf.tobytes()
            total = (len(data) + CHUNK_SIZE - 1) // CHUNK_SIZE
            for idx in range(total):
                part = data[idx * CHUNK_SIZE:(idx + 1) * CHUNK_SIZE]
                sock.sendto(HEADER.pack(frame_id, total, idx) + part, target)

            frame_id = (frame_id + 1) % (2 ** 32)
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\n[INFO] UDP server dihentikan.")
    finally:
        if cap is not None:
            cap.release()
        sock.close()


if __name__ == "__main__":
    main()
