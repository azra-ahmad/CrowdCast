"""
TCP File Server - backend upload NetVault.
Dikembangkan dari pola pre-uts/ftp_server.py (handle_upload).

Protokol:
  Client kirim header 1 baris:  <filename>|<filesize>\n
  Server balas:                 READY\n
  Client kirim:                 <raw bytes sejumlah filesize>
  Server balas:                 OK\n   atau   FAIL:<alasan>\n

Server ini menyimpan file ke storage/uploads/. Flask bertindak sebagai TCP client
(lihat tcp_uploader.py) untuk meneruskan file dari browser ke sini via TCP asli.
"""

import socket
import threading
import os

import config

HOST = "0.0.0.0"
PORT = config.TCP_FILE_PORT
BUFFER = 4096


def _recv_line(conn: socket.socket) -> str:
    """Baca satu baris (sampai newline) dari socket."""
    data = b""
    while not data.endswith(b"\n"):
        chunk = conn.recv(1)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="ignore").strip()


def handle_client(conn: socket.socket, addr: tuple):
    try:
        header = _recv_line(conn)
        if "|" not in header:
            conn.sendall(b"FAIL:format header salah\n")
            return

        raw_name, raw_size = header.rsplit("|", 1)
        filename = os.path.basename(raw_name)  # sanitasi path traversal
        try:
            file_size = int(raw_size)
        except ValueError:
            conn.sendall(b"FAIL:ukuran tidak valid\n")
            return

        if file_size <= 0 or file_size > config.MAX_FILE_SIZE:
            conn.sendall(b"FAIL:ukuran file di luar batas (maks 10 MB)\n")
            return

        os.makedirs(config.UPLOAD_DIR, exist_ok=True)
        save_path = os.path.join(config.UPLOAD_DIR, filename)

        conn.sendall(b"READY\n")

        received = 0
        with open(save_path, "wb") as f:
            while received < file_size:
                chunk = conn.recv(min(BUFFER, file_size - received))
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)

        if received == file_size:
            print(f"[TCP] {addr} upload OK: {filename} ({file_size} bytes)")
            conn.sendall(b"OK\n")
        else:
            conn.sendall(b"FAIL:data tidak lengkap\n")
            if os.path.exists(save_path):
                os.remove(save_path)
    except Exception as e:
        print(f"[TCP] Error dari {addr}: {e}")
    finally:
        conn.close()


def main():
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(10)

    print("=" * 50)
    print("  CrowdCast TCP File Server")
    print(f"  Listening di {HOST}:{PORT}")
    print(f"  Simpan ke: {config.UPLOAD_DIR}")
    print("=" * 50)

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[INFO] TCP server dihentikan.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
