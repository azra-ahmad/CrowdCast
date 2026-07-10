"""
UDP Video Receiver - dijalankan di dalam Flask (thread background).
Terima chunk UDP -> susun ulang jadi frame JPEG -> simpan sebagai `latest_frame`.
Flask route /video_feed membaca latest_frame dan me-relay ke browser sebagai MJPEG.
"""

import socket
import threading
import struct

import config

HEADER = struct.Struct("!IHHI")  # samakan dengan udp_video_server.py

_latest_frame: bytes | None = None
_latest_pos_ms: int = 0          # posisi putar frame terakhir (untuk sinkronisasi audio)
_lock = threading.Lock()
_started = False


def _listen():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((config.UDP_VIDEO_HOST, config.UDP_VIDEO_PORT))
    print(f"[UDP-RX] Mendengarkan frame di {config.UDP_VIDEO_HOST}:{config.UDP_VIDEO_PORT}")

    global _latest_frame, _latest_pos_ms
    buffers: dict[int, dict] = {}  # frame_id -> {index: payload}
    positions: dict[int, int] = {}  # frame_id -> posisi putar (ms)
    last_id = -1                   # frame terakhir yang ditampilkan (anti mundur)

    while True:
        try:
            packet, _addr = sock.recvfrom(65536)
        except OSError:
            continue
        if len(packet) < HEADER.size:
            continue

        frame_id, total, idx, pos_ms = HEADER.unpack(packet[:HEADER.size])
        payload = packet[HEADER.size:]

        entry = buffers.setdefault(frame_id, {})
        entry[idx] = payload
        positions[frame_id] = pos_ms

        if len(entry) == total:
            try:
                frame = b"".join(entry[i] for i in range(total))
            except KeyError:
                frame = None  # ada chunk hilang, skip frame ini
            # hanya tampilkan frame yang lebih baru (cegah loncat mundur);
            # id jauh lebih kecil = streamer restart -> terima sebagai awal baru
            if frame is not None and (frame_id > last_id or last_id - frame_id > 300):
                with _lock:
                    _latest_frame = frame
                    _latest_pos_ms = pos_ms
                last_id = frame_id
            buffers.pop(frame_id, None)
            positions.pop(frame_id, None)

        # Batasi memori: buang frame lama yang belum lengkap
        if len(buffers) > 30:
            for fid in sorted(buffers.keys())[:-10]:
                buffers.pop(fid, None)
                positions.pop(fid, None)


def start():
    """Mulai thread penerima sekali saja."""
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_listen, daemon=True).start()


def get_latest_frame() -> bytes | None:
    with _lock:
        return _latest_frame


def get_latest_pos_ms() -> int:
    """Posisi putar (ms) dari frame terakhir — jam acuan untuk sinkronisasi audio."""
    with _lock:
        return _latest_pos_ms
