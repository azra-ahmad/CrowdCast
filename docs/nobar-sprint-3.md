# Sprint 3 — UI theater + login (gaya streaming, dark/merah)

## Tujuan
Pasang UI CrowdCast (dark + merah, ala Netflix) ke Flask: halaman theater (video + chat
sidebar) dan halaman auth, sesuai mockup yang disetujui.

## Yang diimplementasikan

- **Rute** (`app.py`): `/` = theater **publik**; `/video_feed` & `/chat/poll` publik;
  `/dashboard` redirect ke `/`; login sukses → `/`. Model akses A.
- **Templates**: `base.html` (kerangka), `theater.html` (topbar + player + chat),
  `login.html` (hero "One stream. Everyone has the remote." + card), `register.html`,
  `verify.html`. Template lama (`index.html`, `dashboard.html`) dihapus.
- **CSS** (`style.css`): tema dark `#0B0B0F` + merah `#E50914`, logo filmstrip biru×merah,
  wordmark "CrowdCast" 1 warna, layout video+chat (chat setinggi video, scroll internal),
  overlay progress upload, halaman auth.
- **JS** (`main.js`): chat polling 1.2s + kirim, presence/online, now-playing title live,
  tombol "Ganti tontonan" → upload video dengan overlay progress. Guard `seen` cegah pesan dobel.

## Hasil Testing (terverifikasi via browser preview)

- [x] Theater publik tampil tanpa login: player + chat + "Masuk untuk ikut chat".
- [x] Tema dark benar (`body` = rgb(11,11,15)); logo + LIVE + merah tampil.
- [x] Presence: `online` update dari poll (1 penonton → "1 online").
- [x] `now-title` update otomatis ke video aktif (`clipC.mp4`) via poll.
- [x] Video streaming tampil di player (frame UDP clipC terlihat).
- [x] Login `azra` → muncul tombol "Ganti tontonan" + kotak chat + username.
- [x] Kirim chat dari UI → pesan muncul; **tidak dobel** (setelah fix guard `seen`).
- [x] Layout desktop: player 860×484 + chat 360×484 → **chat setinggi video, sebelahan**.
- [x] Anonim: kotak chat & tombol cast disembunyikan (model akses A).
- [x] Tidak ada error di console.

## Pending / catatan
- Logo masih placeholder SVG; PNG asli user dipasang nanti (taruh di `static/`).
- Upload dari UI memakai pipeline yang sama seperti Sprint 1 (sudah terverifikasi).
- Empty state (belum ada video sama sekali) & polish → Sprint 4.
