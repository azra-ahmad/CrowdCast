<p align="center">
  <img src="static/img/CrowdCast.png" alt="CrowdCast" width="150">
</p>

# Pemrograman Jaringan - UAS

Aplikasi **nonton bareng berbasis web** yang diberi nama **CrowdCast** pengembangan dari tugas Socket Programming (TCP & UDP).
Satu theater global: siapa pun yang login bisa **upload video (via TCP)** untuk langsung jadi
tontonan yang **disiarkan ke semua penonton (via UDP)**, sambil **chat real-time**.

Repo: https://github.com/azra-ahmad/CrowdCast

## Catatan: 
- ini **video streaming** (menyiarkan file video yang di-upload), **bukan live camera**.
- Video dikirim sebagai frame gambar (MJPEG) lewat UDP, sehingga tetap jalan walau kualitas
turun / ada frame yang hilang — ciri khas UDP.

## Fitur (ketentuan UAS)

1. Interface (UI) berbasis web — tema streaming (dark).
2. Sistem login + **verifikasi email** (OTP via Gmail SMTP).
3. **Upload file via TCP** (streaming per-chunk, maks 95 MB).
4. **Streaming video via UDP** (frame per-frame, letterbox menjaga rasio).
5. **Audio via HTTP**, diselaraskan ke posisi siaran dari server.
6. Chat real-time + jumlah penonton online (bonus).
7. Deploy via DNS Cloudflare.

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

  Audio:  Browser ──HTTP /audio──► Flask  (berkas video yang sedang disiarkan)
          Diselaraskan memakai `pos` (posisi putar) yang dititipkan di header paket UDP.
```

**Tiga protokol, tiga kebutuhan berbeda:** TCP untuk upload (file harus utuh), UDP untuk siaran
video (cepat, frame boleh hilang), HTTP untuk audio & antarmuka (harus utuh, bisa di-seek).

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

## Menjalankan (lokal)

### Cara mudah — satu terminal

```bash
python run.py
```

`run.py` menyalakan ketiga proses (tetap **proses terpisah** yang berkomunikasi lewat socket),
menggabungkan log-nya dengan label `[tcp] [udp] [web]`, dan **Ctrl+C sekali mematikan semuanya**.
Sebelum start, port diperiksa dulu supaya tidak ada instance dobel.

### Cara manual — tiga terminal

```bash
python tcp_file_server.py    # 1) backend upload TCP  (port 9010)
python udp_video_server.py   # 2) streamer video UDP  (port 9020)
python app.py                # 3) web app             (http://localhost:5000)
```

Buka `http://localhost:5000` → nonton langsung; Daftar/Masuk untuk chat & "Ganti tontonan".

> **Jalankan tiap program sekali saja.** Kalau `udp_video_server.py` tidak sengaja jalan dua
> kali (mis. terminal lama ditutup tanpa `Ctrl+C`, jadi prosesnya masih hidup), penerima akan
> mengunci salah satu streamer dan mengabaikan yang lain — siaran tetap jalan, tapi ada proses
> mubazir. `run.py` sudah menolak start bila mendeteksi instance lama.
>
> Ini **tidak berhubungan dengan jumlah video yang di-upload** — upload video sebanyak apa pun
> aman, karena hanya ada 1 video aktif pada satu waktu.
>
> Cek & matikan proses yang nyangkut:
> ```bash
> # Windows (PowerShell)
> Get-CimInstance Win32_Process -Filter "name='python.exe'" | Select-Object ProcessId,CommandLine
> Stop-Process -Id <PID> -Force
>
> # Linux / macOS
> pgrep -af udp_video_server.py
> pkill -f udp_video_server.py
> ```

## Deploy dengan Cloudflare (DNS)

App tetap berjalan di laptop atau VM. Cloudflare Tunnel hanya mengekspos
ke domain publik, bukan tempat hosting/penyimpanan.

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

- **Audio & sinkronisasi**: video dikirim sebagai frame gambar (MJPEG) via UDP — gambar tidak
  membawa suara. Audio diambil terpisah lewat HTTP (`/audio`) dari berkas video yang sama, lalu
  diselaraskan ke `pos` (posisi putar) yang dikirim server di header paket UDP. Karena semua
  penonton mengacu ke jam yang sama, mereka mendengar momen yang sama.
  Sinkronisasinya **perkiraan** (toleransi ~0,75 detik), bukan frame-accurate. Untuk presisi
  penuh diperlukan protokol media seperti RTP/WebRTC.
- Audio hanya berbunyi bila codec berkas didukung browser (mp4/webm aman; mkv/avi sering tidak).
- Audio harus dinyalakan lewat tombol di player — browser melarang audio berbunyi otomatis.
- Password di-hash (`werkzeug.security`); `.env` & `users.json` tidak di-commit (`.gitignore`).
- Nama file di-sanitasi (`os.path.basename`) + batas ukuran 95 MB (validasi di client & server;
  Cloudflare plan gratis menolak request body > 100 MB).
