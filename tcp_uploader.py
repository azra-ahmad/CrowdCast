"""
Helper: Flask sebagai TCP client untuk meneruskan file ke tcp_file_server.
Streaming per-chunk (tidak menahan seluruh file di RAM) supaya video besar aman.
"""

import socket

import config

BUFFER = 64 * 1024


def _recv_line(conn: socket.socket) -> str:
    data = b""
    while not data.endswith(b"\n"):
        chunk = conn.recv(1)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="ignore").strip()


def upload_via_tcp(filename: str, stream, size: int) -> tuple[bool, str]:
    """
    Kirim isi `stream` (file-like) sebesar `size` byte ke TCP file server.
    Return (sukses, pesan). Dipanggil oleh route /upload di app.py.
    """
    if size <= 0:
        return False, "File kosong."
    if size > config.MAX_FILE_SIZE:
        return False, "Video terlalu besar (maks 200 MB)."

    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(60)
        conn.connect((config.TCP_FILE_HOST, config.TCP_FILE_PORT))
    except Exception as e:
        return False, f"Tidak bisa terhubung ke file server: {e}"

    try:
        conn.sendall(f"{filename}|{size}\n".encode("utf-8"))

        resp = _recv_line(conn)
        if not resp.startswith("READY"):
            return False, resp or "Server tidak siap."

        sent = 0
        while sent < size:
            chunk = stream.read(min(BUFFER, size - sent))
            if not chunk:
                break
            conn.sendall(chunk)
            sent += len(chunk)

        result = _recv_line(conn)
        if result.startswith("OK"):
            return True, f"'{filename}' disiarkan via TCP ({size} bytes)."
        return False, result or "Upload gagal."
    except Exception as e:
        return False, f"Error saat upload: {e}"
    finally:
        conn.close()
