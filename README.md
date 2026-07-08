# NetVault — Web App Socket Programming (UAS Pemrograman Jaringan)

Pengembangan dari tugas Socket Programming (UDP & TCP) menjadi **aplikasi web**:
login + verifikasi email, **upload file via TCP**, dan **streaming video via UDP**,
dengan UI clean bergaya editorial.

Link repository: https://github.com/azra-ahmad/pjar-matkul/

## Fitur (sesuai ketentuan UAS)

1. **Interface (UI)** — web bersih, responsif, animasi halus (GSAP).
2. **Sistem login** — registrasi + login, password di-hash (werkzeug).
3. **Integrasi email** — kode OTP verifikasi dikirim ke email saat registrasi (Gmail SMTP), plus notifikasi saat login.
4. **Upload file via TCP** — file diteruskan ke file server lewat koneksi TCP asli, dengan progress bar.
5. **Streaming video via UDP** — video dikirim per-frame via UDP, ditampilkan sebagai MJPEG di browser.
6. **Berbasis web** — Flask (Python).

Tanpa database — user disimpan di `users.json`, OTP disimpan in-memory.

## Arsitektur

```
                     ┌──────────────────────────────┐
   Browser  ◄──HTTP──►│      Flask (app.py)          │
  (UI, upload,        │  UI · login · email · session│
   nonton video)      └───┬───────────────┬──────────┘
                          │ TCP socket     │ UDP socket
                  ┌───────▼────────┐   ┌───▼─────────────────┐
                  │ tcp_file_server│   │ udp_video_server    │
                  │  (simpan file) │   │ (video → sendto)    │
                  └────────────────┘   └─────────────────────┘
```

Browser tidak bisa buka socket TCP/UDP mentah, jadi **Flask jadi gateway**:
kode socket berperan sebagai backend service. TCP & UDP asli tetap dipakai
(bisa dibuktikan di Wireshark).

## Struktur File

```text
uas/
├── app.py                 # Flask: routes, session, orkestrasi
├── auth.py                # register/login/OTP + users.json (hashing)
├── email_sender.py        # kirim OTP & notifikasi via Gmail SMTP
├── config.py              # konfigurasi (baca .env)
├── tcp_file_server.py     # TCP file server (backend upload)
├── tcp_uploader.py        # Flask → TCP client (forward file)
├── udp_video_server.py    # baca video, kirim frame via UDP
├── udp_receiver.py        # thread penerima UDP + buffer frame (dipakai app.py)
├── templates/             # index, login, register, verify, dashboard
├── static/css/style.css   # tema clean/editorial
├── static/js/main.js      # GSAP, progress bar upload, kontrol video
├── videos/sample.mp4      # sumber video demo (taruh sendiri)
├── storage/uploads/       # hasil upload (auto-generated)
├── requirements.txt
└── .env.example           # template kredensial
```

## Setup

```bash
cd uas
pip install -r requirements.txt
cp .env.example .env       
```

Taruh sebuah video di `videos/sample.mp4` untuk didemokan.

### Konfigurasi `.env`

| Variabel | Keterangan |
| --- | --- |
| `SECRET_KEY` | string acak untuk session Flask |
| `GMAIL_ADDRESS` | alamat Gmail pengirim OTP |
| `GMAIL_APP_PASSWORD` | App Password 16 digit (bukan password asli) |
| `TCP_FILE_HOST/PORT` | alamat TCP file server (default 127.0.0.1:9010) |
| `UDP_VIDEO_HOST/PORT` | alamat UDP video (default 127.0.0.1:9020) |

> **Cara buat Gmail App Password:** Akun Google → Keamanan → aktifkan Verifikasi 2 Langkah → App Passwords → buat baru → salin 16 digit ke `GMAIL_APP_PASSWORD`.
> Kalau `.env` dikosongkan, OTP akan **di-print ke terminal** (mode dev) supaya tetap bisa dites tanpa email.

## Cara Menjalankan (3 proses)

Buka 3 terminal (semua di folder `uas/`):

```bash
python tcp_file_server.py     # 1) backend upload TCP
python udp_video_server.py    # 2) streamer video UDP
python app.py                 # 3) web app (http://localhost:5000)
```

Buka `http://localhost:5000` → Daftar → cek OTP di email/terminal → verifikasi → login → dashboard.

## Deploy dengan Cloudflare (DNS)

Deploy pakai **Cloudflare Tunnel** — expose app ke domain Cloudflare tanpa buka port publik.

```bash
# di VM/server, install cloudflared lalu:
cloudflared tunnel login
cloudflared tunnel create netvault
cloudflared tunnel route dns netvault netvault.domainmu.com
cloudflared tunnel --url http://localhost:5000 run netvault
```

Aplikasi akan bisa diakses lewat `https://netvault.domainmu.com` (via DNS Cloudflare).

## Bukti TCP & UDP (Wireshark)

- Upload file → filter `tcp.port == 9010` → terlihat handshake + transfer byte via TCP.
- Streaming video → filter `udp.port == 9020` → terlihat aliran datagram UDP per-frame.

## Catatan Keamanan

- Password di-hash (`werkzeug.security`), bukan plaintext.
- Kredensial email di `.env` (tidak di-commit; ada di `.gitignore`).
- Nama file di-sanitasi (`os.path.basename`) + batas ukuran 10 MB.
