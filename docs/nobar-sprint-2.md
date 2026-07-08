# Sprint 2 — Chat real-time (polling) + presence

## Tujuan
Chat live sambil nonton, tanpa dependency baru (polling ~1.2s), plus jumlah penonton online.
Sesuai model akses A: nonton & baca chat bebas; kirim chat wajib login.

## Yang diimplementasikan (`app.py`)

- State in-memory: `_messages` (id, user, text, ts), `_presence` (viewer_id → last_seen).
- `POST /chat/send` (login wajib) — validasi kosong / maks 300 char, simpan pesan, simpan
  maksimal 200 pesan terakhir.
- `GET /chat/poll?since=<id>` (publik) — balikin pesan dengan id > since, jumlah `online`, dan
  `me` (username kalau login). Sekaligus jadi heartbeat presence.
- Presence: tiap penonton (termasuk anonim) dapat `viewer_id` di session; dihitung online kalau
  aktif dalam 10 detik terakhir.

## Hasil Testing (terverifikasi)

Via `test_sprint2.py` (2 sesi: `azra` login + 1 anonim):

- [x] azra kirim 2 pesan → sukses (id 1, 2).
- [x] Anonim `poll` → **membaca** kedua pesan (chat publik), `me: null`.
- [x] Presence: setelah 2 penonton poll → `online: 2`.
- [x] Poll incremental (`since` = id terakhir) → 0 pesan baru (tidak dobel).
- [x] Anonim `POST /chat/send` → **ditolak** (redirect login) — sesuai model A.
- [x] Pesan kosong → ditolak (HTTP 400).

## Pending
- Panel chat di UI (Sprint 3): input + auto-scroll + polling 1.2s + tampilan penonton online.
