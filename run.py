"""
Launcher CrowdCast — jalankan semua proses dari SATU terminal.

    python run.py

Tetap 3 proses terpisah yang saling berkomunikasi lewat socket
(tcp_file_server, udp_video_server, app) — hanya saja dikelola satu induk.
Ctrl+C sekali akan mematikan ketiganya.

Sebelum menyalakan, port dicek dulu supaya tidak ada instance dobel
(dua udp_video_server membuat siaran tersendat).
"""

import os
import sys
import socket
import subprocess
import threading
import time

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_PORT = int(os.getenv("PORT", "5000"))

SERVICES = [
    ("tcp", "tcp_file_server.py"),
    ("udp", "udp_video_server.py"),
    ("web", "app.py"),
]

procs: list[subprocess.Popen] = []


# ─── Pemeriksaan sebelum start ───────────────────────────────────────────────
def _tcp_listening(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def _udp_taken(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind((host, port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def preflight() -> bool:
    masalah = []
    if _tcp_listening(config.TCP_FILE_HOST, config.TCP_FILE_PORT):
        masalah.append(f"TCP {config.TCP_FILE_PORT} sudah dipakai (tcp_file_server masih jalan?)")
    if _udp_taken(config.UDP_VIDEO_HOST, config.UDP_VIDEO_PORT):
        masalah.append(f"UDP {config.UDP_VIDEO_PORT} sudah dipakai (app.py lama masih jalan?)")
    if _tcp_listening("127.0.0.1", WEB_PORT):
        masalah.append(f"TCP {WEB_PORT} sudah dipakai (web app lama masih jalan?)")

    if masalah:
        print("\n[GAGAL] Sepertinya masih ada CrowdCast yang berjalan:")
        for m in masalah:
            print(f"  - {m}")
        print("\nMatikan dulu prosesnya, lalu jalankan ulang:")
        print("  Windows : Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
              "Select-Object ProcessId,CommandLine")
        print("            Stop-Process -Id <PID> -Force")
        print("  Linux   : pkill -f 'tcp_file_server.py|udp_video_server.py|app.py'\n")
        return False
    return True


# ─── Menyalakan & mengawasi ──────────────────────────────────────────────────
def _pump(tag: str, stream):
    """Teruskan output anak ke terminal induk, diberi label supaya jelas asalnya."""
    for line in stream:
        sys.stdout.write(f"[{tag}] {line}")
        sys.stdout.flush()


def spawn(tag: str, script: str) -> subprocess.Popen:
    p = subprocess.Popen(
        [sys.executable, "-u", script],       # -u = jangan buffer, log langsung muncul
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    threading.Thread(target=_pump, args=(tag, p.stdout), daemon=True).start()
    return p


def shutdown():
    for p in procs:
        if p.poll() is None:
            p.terminate()
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def main():
    if not preflight():
        sys.exit(1)

    print("=" * 56)
    print("  CrowdCast — menyalakan semua proses")
    print(f"  TCP file server : port {config.TCP_FILE_PORT}")
    print(f"  UDP video server: port {config.UDP_VIDEO_PORT}")
    print(f"  Web app         : http://localhost:{WEB_PORT}")
    print("  Tekan Ctrl+C untuk menghentikan semuanya.")
    print("=" * 56)

    try:
        for tag, script in SERVICES:
            procs.append(spawn(tag, script))
            time.sleep(0.6)                   # beri jeda supaya urutan start rapi

        while True:                           # awasi: kalau satu mati, matikan semua
            for (tag, _), p in zip(SERVICES, procs):
                code = p.poll()
                if code is not None:
                    print(f"\n[{tag}] berhenti (exit {code}). Mematikan proses lain...")
                    return
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Ctrl+C — menghentikan semua proses...")
    finally:
        shutdown()
        print("[INFO] Semua proses berhenti.")


if __name__ == "__main__":
    main()
