"""
UDP Video Server - backend streaming NetVault.
Baca file video (OpenCV) -> encode tiap frame jadi JPEG -> kirim via UDP (sendto).

Karena 1 datagram UDP dibatasi ~65 KB, tiap frame dipecah jadi beberapa chunk
dengan header kecil (frame_id, total_chunk, index) supaya bisa disusun ulang
di sisi penerima (udp_receiver.py). Frame yang hilang = frame drop (perilaku khas UDP).
"""

import socket
import time
import struct

import cv2

import config

CHUNK_SIZE = 40000               # payload per datagram (aman < 65 KB)
HEADER = struct.Struct("!IHH")   # frame_id (uint32), total (uint16), index (uint16)
JPEG_QUALITY = 60
FRAME_SIZE = (640, 360)


def main():
    cap = cv2.VideoCapture(config.VIDEO_FILE)
    if not cap.isOpened():
        print(f"[UDP] Gagal buka video: {config.VIDEO_FILE}")
        print("      Taruh file video di videos/sample.mp4")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (config.UDP_VIDEO_HOST, config.UDP_VIDEO_PORT)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    delay = 1.0 / fps

    print("=" * 50)
    print("  NetVault UDP Video Server")
    print(f"  Streaming {config.VIDEO_FILE} -> {target[0]}:{target[1]}")
    print(f"  {fps:.0f} FPS, resize {FRAME_SIZE}, JPEG q{JPEG_QUALITY}")
    print("=" * 50)

    frame_id = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # ulang dari awal (loop)
                continue

            frame = cv2.resize(frame, FRAME_SIZE)
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
        cap.release()
        sock.close()


if __name__ == "__main__":
    main()
