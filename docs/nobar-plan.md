# Plan: Reframe NetVault → "CrowdCast" (Nonton Bareng, chaos edition)

> Nama: **CrowdCast** — menonjolkan sistem chaos: siapa pun boleh upload dan langsung
> mengganti 1 theater yang ditonton semua orang.

## Context / Kenapa

Bentuk lama (login + kotak upload + player video) terasa seperti checklist tugas tanpa
tujuan. Reframe ini memberi **satu produk dengan cerita**: ruang nonton bareng di mana
video di-upload lalu disiarkan ke semua penonton sambil chat. Ketiga fitur wajib jadi
saling butuh, bukan nempel.

Keputusan yang sudah diambil: **satu ruangan global** ("theater") — bukan multi-room.
Cocok dengan arsitektur 1-stream yang sudah ada dan realistis untuk deadline (sebelum minggu 14).

## Konsep

- Semua user yang login masuk ke **1 theater** yang sama.
- Ada **1 video aktif** yang sedang diputar (now playing).
- Siapa pun bisa **upload video** (via TCP) untuk menggantikan tontonan saat ini.
- Server **menyiarkan** video itu (via UDP) ke semua penonton — semua melihat frame
  yang sama di waktu yang sama (tersinkron).
- Semua penonton bisa **chat** live sambil nonton.

Bukan YouTube (bukan library on-demand): ini **siaran bersama**, telat masuk = masuk di
tengah, seperti menyalakan TV saat acara sudah jalan. Justru itu yang membuat UDP masuk akal.

## Pemetaan ke ketentuan UAS (semua tetap terpenuhi)

| Ketentuan | Di Nobar |
| --- | --- |
| UI | Halaman theater: player siaran + chat + now playing + kontrol ganti video |
| Login | Tetap (register/login) |
| Integrasi email | Tetap — OTP verifikasi saat registrasi |
| Upload file via TCP | Upload video untuk jadi tontonan → lewat `tcp_file_server.py` |
| Streaming video via UDP | Server nyiarin video aktif ke semua penonton |
| Berbasis web | Flask |
| Deploy Cloudflare | Tetap (tidak berubah) |
| Bonus | Chat real-time + jumlah penonton online |

## Arsitektur & Alur Data

```
  Browser (theater)  ──HTTP──►  Flask (app.py)
     │  ▲                         │        │        │
   chat│ │video(MJPEG)      TCP   │   UDP  │   state │
     │  │                  upload │  frame │   file  │
     ▼  │                 ┌───────▼──┐  ┌──▼──────┐ ┌▼───────────────┐
   /chat/*                │tcp_file_ │  │udp_     │ │now_playing.txt │
   (polling)              │server    │  │receiver │ │(path video      │
                          └────┬─────┘  └────▲────┘ │ yang aktif)     │
                     simpan ke │             │      └───────▲─────────┘
                     storage/  │       ┌─────┴───────┐      │ ditulis Flask
                               └──────►│udp_video_    │──────┘ saat upload sukses
                                       │server (baca  │  baca tiap loop
                                       │now_playing)  │
                                       └──────────────┘
```

**Alur "upload jadi tontonan":**
1. User upload video → Flask `/upload` → forward ke `tcp_file_server` (TCP) → tersimpan di `storage/uploads/`.
2. Setelah OK, Flask **hapus video lama** (yang tadinya now-playing), lalu tulis path video
   baru ke `videos/now_playing.txt`. → disk hanya menyimpan ~1 video, tanpa DB, cocok tema chaos.
3. `udp_video_server` mengecek `now_playing.txt` tiap loop; kalau berubah → switch, mulai
   siarkan video baru dari awal.
4. Semua penonton di `/video_feed` otomatis lihat video baru (karena `udp_receiver`
   menyimpan 1 `latest_frame` yang dibagi ke semua).

**Penyimpanan & deploy (tanpa DB):** video disimpan sebagai file di disk mesin yang
menjalankan app (lokal = laptop; deploy = VM). Cloudflare Tunnel hanya "pintu" yang
mengekspos app ke domain publik — **bukan** tempat hosting/penyimpanan; file tetap di disk
VM. "Video aktif" cukup ditandai 1 penunjuk (`now_playing.txt`), bukan DB. Auto-hapus video
lama menjaga disk tidak penuh.

**Alur chat (sederhana, tanpa dependency baru):**
- Pesan disimpan in-memory: `messages = [{id, user, text, ts}]`.
- `POST /chat/send` → tambah pesan (user dari session).
- `GET /chat/poll?since=<id>` → balikin pesan baru + daftar penonton online.
- Client polling tiap ~1.5 detik. Cukup real-time untuk demo, bulletproof, tanpa WebSocket.

## Reuse vs Baru

**Dipakai lagi (sedikit/tanpa ubah):**
- `auth.py`, `email_sender.py` — login/OTP tetap.
- `tcp_file_server.py` — jalur upload TCP tetap (naikin batas ukuran untuk video).
- `udp_receiver.py` — sudah berbagi 1 frame ke semua = sinkron gratis. Tetap.

**Diubah:**
- `udp_video_server.py` — sumber bukan `sample.mp4` tetap, tapi baca `now_playing.txt` &
  bisa switch saat berubah.
- `app.py` — tambah state theater, endpoint chat, dan set now-playing setelah upload.
- `config.py` — `MAX_FILE_SIZE` dinaikkan untuk video (mis. 50 MB), batasi tipe video.

**Baru:**
- Endpoint chat (`/chat/send`, `/chat/poll`).
- Halaman **theater** (player + chat + now playing + kontrol upload).
- State presence (jumlah penonton online, dari heartbeat polling).

## Konsep UI (theater)

Layout utama = "bioskop + chat":
```
┌───────────────────────────────┬───────────────┐
│  NOW PLAYING: namafile.mp4    │   Chat        │
│  ┌─────────────────────────┐  │  ┌─────────┐  │
│  │                         │  │  │ pesan…  │  │
│  │   video siaran (UDP)    │  │  │ pesan…  │  │
│  │                         │  │  │         │  │
│  └─────────────────────────┘  │  └─────────┘  │
│  [LIVE] 3 nonton · 24 fps     │  [ketik…][→]  │
│  [ Ganti tontonan (upload) ]  │               │
└───────────────────────────────┴───────────────┘
```
- Arah visual (warna/font) **diputuskan di Sprint 3** — akan gua kasih 2-3 opsi mockup dulu
  sebelum ngoding, karena tema dark kemarin dinilai kurang. Tema "bioskop" membuka opsi
  gelap-elegan ATAU terang-bersih; ditentukan bareng.

## Sprint

- **Sprint 1 — Upload jadi sumber siaran.** `now_playing.txt` + `udp_video_server` switch
  source + Flask set now-playing setelah upload + naikin batas ukuran video.
  *Verifikasi:* upload video → stream berganti ke video itu.
- **Sprint 2 — Chat.** endpoint send/poll + presence + panel chat di UI.
  *Verifikasi:* 2 window, saling kirim pesan muncul < ~2 detik; counter penonton benar.
- **Sprint 3 — Theater UI.** redesign halaman utama (player+chat+now playing+kontrol),
  landing copy, tema. *(pilih arah visual dulu).* *Verifikasi:* rapi di desktop + iPad + HP.
- **Sprint 4 — Polish & docs.** empty state (belum ada video), error handling, README baru,
  bukti Wireshark, responsif final.

Tiap sprint ditulis di `docs/nobar-sprint-N.md` + hasil testing.

## Risiko / Catatan jujur

- **Ukuran video:** video >10 MB. Naikin batas ke ~50 MB dan pakai klip pendek untuk demo.
  Kalau file besar, upload TCP makan waktu — pakai video pendek (< ~1 menit) saat presentasi.
- **Sinkronisasi:** karena server siarkan 1 feed, semua penonton lihat frame sama otomatis.
  Tapi kalau ada yang telat play, dia mulai dari titik siaran saat ini (bukan awal) — ini
  memang perilaku "siaran", dan justru poin bagus untuk dijelaskan ke dosen.
- **Chat polling** ~1.5s: cukup untuk demo. Kalau mau instan, bisa diupgrade ke WebSocket/SSE
  nanti (opsional, bukan sekarang — hindari over-engineer).
- **Ganti video saat orang lagi nonton:** siapa pun bisa ganti → bisa "rebutan". Untuk 1 room
  demo, itu OK / malah lucu. Bisa dibatasi nanti kalau perlu.

## Keputusan (sudah diputuskan)

1. **Nama app:** ✅ **CrowdCast** (menonjolkan chaos).
2. **Siapa boleh ganti video:** ✅ **siapa pun yang login**.
3. **Chat:** ✅ **polling ~1.2 detik** (sederhana, tanpa dependency baru).
4. **Batas ukuran video:** ✅ **200 MB** + **upload chunked** (hemat RAM) + auto-hapus video lama.
5. **Video habis:** ✅ **loop** (opsi A) sampai ada yang ganti + empty state saat belum ada video.
6. **Model akses:** ✅ **A** — theater **publik** (nonton tanpa login); **login wajib hanya untuk
   chat & upload/cast**. (Sesuai referensi "Sign in to chat".)
7. **Arah visual UI:** ✅ **streaming ala Netflix** — dark charcoal `#0B0B0F` + **aksen merah
   `#E50914`** + sans tebal (Helvetica-style), cinematic. **Bukan hijau.**
   - **Logo:** pakai gambar upload user (filmstrip biru×merah "pecah" = tema chaos); akan diubah
     user. Di mockup Artifact dipakai placeholder (Artifact tak bisa muat gambar eksternal); di
     Flask asli PNG-nya ditaruh di `static/`.
   - **Wordmark:** "CrowdCast" — tanpa spasi, **1 warna (putih)**.
   - **Theater layout:** video besar (kiri) + **chat sidebar setinggi video, tinggi fixed,
     scroll internal** (chat panjang tidak menurunkan halaman). Tombol **"Ganti tontonan"** di
     top bar. **Tidak ada konten lain di bawah** video+chat.
   - **Halaman masuk (terpisah):** headline **"One stream. Everyone has the remote."** (English);
     sub Indonesia: *"Satu layar, ditonton bareng. Siapa pun bisa ganti siarannya — kapan aja."*
   - Mockup disetujui: `scratchpad/crowdcast-mockup.html` (v2).

## Catatan deploy (revisi)

Cloudflare Tunnel hanya menyambungkan device lain ke mesin yang menjalankan app — **bisa laptop
sendiri**. VM tidak wajib (tidak ada di syarat tugas); VM hanya opsional bila ingin app tetap
online saat laptop mati. File tetap tersimpan di disk mesin yang menjalankan app.
