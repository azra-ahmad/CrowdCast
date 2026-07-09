# CrowdCast

> One stream. Everyone has the remote.

Aplikasi **nonton bareng berbasis web** — pengembangan dari tugas Socket Programming (TCP & UDP).
Satu theater global: siapa pun yang login bisa **upload video (via TCP)** untuk langsung jadi
tontonan yang **disiarkan ke semua penonton (via UDP)**, sambil **chat real-time**.

Repo: https://github.com/azra-ahmad/CrowdCast

> Catatan: ini **video streaming** (menyiarkan file video yang di-upload), **bukan live camera**.
> Video dikirim sebagai frame gambar (MJPEG) lewat UDP, sehingga tetap jalan walau kualitas
> turun / ada frame yang hilang — ciri khas UDP.

## Fitur (ketentuan UAS)

1. Interface (UI) berbasis web — tema streaming (dark).
2. Sistem login + **verifikasi email** (OTP via Gmail SMTP).
3. **Upload file via TCP** (streaming per-chunk, maks 200 MB).
4. **Streaming video via UDP** (frame per-frame, letterbox menjaga rasio).
5. Chat real-time + jumlah penonton online (bonus).
6. Deploy via DNS Cloudflare.

Tanpa database — user disimpan di `users.json`, state siaran & chat in-memory.

## Konsep

- **1 theater global**, 1 video aktif.
- Upload video (TCP) → langsung jadi siaran (video lama otomatis dihapus).
- Server menyiarkan ke semua penonton (UDP) → tersinkron (semua lihat frame yang sama).
- Video habis → loop. **Nonton bebas**; login wajib hanya untuk chat & ganti siaran.

## Arsitektur

```
  Browser (theater)  ──HTTP──►  Flask (app.py)  ──┬── TCP ──►  tcp_file_server  (simpan video)
   nonton · chat · upload                         └── UDP ──►  udp_video_server (siarkan frame)
                                                      (via udp_receiver → /video_feed MJPEG)
```

Browser tidak bisa membuka socket TCP/UDP mentah, jadi Flask jadi **gateway**: kode socket jadi
backend service. TCP & UDP asli tetap dipakai (bisa dibuktikan di Wireshark).

## Struktur File

```text
CrowdCast/
├── app.py                 # Flask: routes, session, chat, orkestrasi
├── auth.py                # register/login/OTP + users.json (hashing)
├── email_sender.py        # kirim OTP via Gmail SMTP
├── broadcast.py           # state "video aktif" (now_playing.txt)
├── config.py              # konfigurasi (baca .env)
├── tcp_file_server.py     # TCP file server (backend upload)
├── tcp_uploader.py        # Flask → TCP client (forward file, chunked)
├── udp_video_server.py    # baca video aktif, kirim frame via UDP (letterbox)
├── udp_receiver.py        # thread penerima UDP + buffer frame (dipakai app.py)
├── templates/             # theater, login, register, verify, base
├── static/css, static/js  # tema + logika chat/upload
├── static/img/CrowdCast.png
├── videos/                # sumber video (now_playing.txt disimpan di sini)
├── storage/uploads/       # video hasil upload (hanya menyimpan ~1 video aktif)
├── requirements.txt
└── .env.example
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # isi kredensial (lihat .env.example)
# taruh sebuah video di videos/sample.mp4 sebagai channel default (opsional)
```

`.env`: `SECRET_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` (App Password 16 digit), dan
alamat socket (`TCP_FILE_HOST/PORT`, `UDP_VIDEO_HOST/PORT` — default `127.0.0.1`).
Kalau kredensial Gmail dikosongkan, OTP di-print ke terminal (mode dev).

## Menjalankan (lokal, 3 proses)

Buka 3 terminal:

```bash
python tcp_file_server.py    # 1) backend upload TCP  (port 9010)
python udp_video_server.py   # 2) streamer video UDP  (port 9020)
python app.py                # 3) web app             (http://localhost:5000)
```

Buka `http://localhost:5000` → nonton langsung; Daftar/Masuk untuk chat & "Ganti tontonan".

> Pastikan **hanya satu** `udp_video_server` berjalan. Kalau ada dua, siaran akan tersendat
> (dua streamer mengirim ke port yang sama).

## Deploy dengan Cloudflare (DNS)

App tetap berjalan di **mesin kamu** (laptop atau VM); Cloudflare Tunnel hanya mengekspos
ke domain publik — bukan tempat hosting/penyimpanan.

```bash
# install cloudflared, lalu:
cloudflared tunnel login
cloudflared tunnel create crowdcast
cloudflared tunnel route dns crowdcast crowdcast.domainmu.com
cloudflared tunnel --url http://localhost:5000 run crowdcast
```

Akses lewat `https://crowdcast.domainmu.com` (via DNS Cloudflare).

## Bukti TCP & UDP (Wireshark)

- Upload video → filter `tcp.port == 9010` → terlihat handshake + transfer byte via TCP.
- Streaming → filter `udp.port == 9020` → terlihat aliran datagram UDP per-frame.

## Catatan

- **Tanpa audio**: video dikirim sebagai frame gambar (MJPEG) via UDP; gambar tidak membawa
  suara. Menambah audio butuh pipeline berbeda (mis. WebRTC), di luar scope tugas.
- Password di-hash (`werkzeug.security`); `.env` & `users.json` tidak di-commit (`.gitignore`).
- Nama file di-sanitasi (`os.path.basename`) + batas ukuran 200 MB.
