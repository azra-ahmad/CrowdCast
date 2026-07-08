"""
Helper: Flask bertindak sebagai TCP client untuk meneruskan file ke tcp_file_server.
Dikembangkan dari pola pre-uts/ftp_client.py (upload_file).
"""

import socket

import config

BUFFER = 4096


def _recv_line(conn: socket.socket) -> str:
    data = b""
    while not data.endswith(b"\n"):
        chunk = conn.recv(1)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="ignore").strip()


def upload_via_tcp(filename: str, data: bytes) -> tuple[bool, str]:
    """
    Kirim file (bytes) ke TCP file server. Return (sukses, pesan).
    Dipanggil oleh route /upload di app.py.
    """
    file_size = len(data)
    if file_size == 0:
        return False, "File kosong."
    if file_size > config.MAX_FILE_SIZE:
        return False, "File terlalu besar (maks 10 MB)."

    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(10)
        conn.connect((config.TCP_FILE_HOST, config.TCP_FILE_PORT))
    except Exception as e:
        return False, f"Tidak bisa terhubung ke file server: {e}"

    try:
        # Kirim header: filename|size
        conn.sendall(f"{filename}|{file_size}\n".encode("utf-8"))

        resp = _recv_line(conn)
        if not resp.startswith("READY"):
            return False, resp or "Server tidak siap."

        # Kirim isi file
        conn.sendall(data)

        result = _recv_line(conn)
        if result.startswith("OK"):
            return True, f"File '{filename}' berhasil diupload via TCP ({file_size} bytes)."
        return False, result or "Upload gagal."
    except Exception as e:
        return False, f"Error saat upload: {e}"
    finally:
        conn.close()
