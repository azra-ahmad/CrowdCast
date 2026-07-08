# CrowdCast

> One stream. Everyone has the remote.

Aplikasi **nonton bareng (watch party)** berbasis web — pengembangan dari tugas Socket
Programming (TCP & UDP). Satu theater global: siapa pun yang login bisa **upload video (via TCP)**
untuk langsung jadi siaran yang **ditonton semua orang (via UDP)**, sambil **chat real-time**.

Repo: https://github.com/azra-ahmad/CrowdCast

## Konsep

- **1 theater global**, 1 video aktif.
- Upload video (TCP) → langsung jadi siaran (mengganti yang lama, auto-hapus file lama).
- Server menyiarkan ke semua penonton (UDP) → nonton bareng tersinkron.
- **Chat live** sambil nonton.
- **Nonton bebas**; login wajib hanya untuk chat & ganti siaran ("chaos": siapa pun bisa ganti).

## Fitur (ketentuan UAS)

1. Interface (UI) berbasis web.
2. Sistem login + **verifikasi email** (OTP, Gmail SMTP).
3. **Upload file via TCP**.
4. **Streaming video via UDP**.
5. Chat real-time (bonus).
6. Deploy via DNS Cloudflare.

Tanpa database — user disimpan di `users.json`, state siaran & chat in-memory.

## Arsitektur

```
  Browser (theater)  ──HTTP──►  Flask (app.py)  ──┬── TCP ──►  tcp_file_server  (simpan video)
   nonton · chat · upload                         └── UDP ──►  udp_video_server (siarkan frame)
```

Browser tidak bisa membuka socket TCP/UDP mentah, jadi Flask jadi **gateway**: kode socket jadi
backend service. TCP & UDP asli tetap dipakai (bisa dibuktikan di Wireshark).

## Menjalankan (lokal, 3 proses)

```bash
cd CrowdCast
pip install -r requirements.txt
cp .env.example .env        # isi kredensial (lihat .env.example)

python tcp_file_server.py    # backend upload TCP
python udp_video_server.py   # streamer video UDP
python app.py                # web app (http://localhost:5000)
```

## Status pengembangan

- [x] Fondasi socket: login + OTP email, upload via TCP, streaming via UDP
- [ ] Sprint 1 — upload video → jadi sumber siaran (chunked, loop, auto-hapus lama)
- [ ] Sprint 2 — chat real-time (polling) + presence
- [ ] Sprint 3 — UI theater + login (gaya streaming, dark/merah)
- [ ] Sprint 4 — polish, empty state, deploy Cloudflare, bukti Wireshark

Detail rencana: [`docs/nobar-plan.md`](docs/nobar-plan.md).

## Keamanan

- Password di-hash (`werkzeug.security`).
- Kredensial email di `.env` (tidak di-commit — ada di `.gitignore`).
- Nama file di-sanitasi + batas ukuran upload.
