# Sprint 1 — Upload video jadi siaran

## Tujuan
Upload video (TCP) langsung jadi sumber siaran (UDP) yang ditonton semua orang, dengan:
upload chunked (hemat RAM), video habis → loop, dan auto-hapus video lama.

## Yang diimplementasikan

| File | Perubahan |
| --- | --- |
| `config.py` | `MAX_FILE_SIZE` → 200 MB, `ALLOWED_VIDEO_EXT`, `NOW_PLAYING_FILE`, `VIDEOS_DIR` |
| `broadcast.py` (baru) | state siaran: `get_now_playing()` / `set_now_playing()` (tulis atomik, fallback ke `sample.mp4`) |
| `udp_video_server.py` | baca `now_playing`, switch sumber saat berubah, loop saat habis, idle saat kosong, hapus video lama (hasil upload) saat switch |
| `tcp_uploader.py` | streaming per-chunk dari file-like (tidak menahan seluruh file di RAM) |
| `app.py` `/upload` | validasi ekstensi video, hitung ukuran via seek, streaming ke TCP, set `now_playing` saat sukses |
| `.gitignore` | tambah `videos/now_playing.txt` |

## Alur
Browser → `/upload` (Flask) → `tcp_uploader` (TCP, chunked) → `tcp_file_server` simpan ke
`storage/uploads/` → Flask set `now_playing.txt` → `udp_video_server` switch & siarkan →
`udp_receiver` → `/video_feed` (MJPEG) ke penonton. Video lama dihapus streamer saat switch.

## Hasil Testing (terverifikasi)

Diuji via script `test_sprint1.py` (login user `azra`, app di port 5055):

- [x] Login berhasil → dashboard.
- [x] Upload `clipB.mp4` → sukses, `now_playing` = clipB, ada di `storage/uploads/`.
- [x] Upload `clipC.mp4` → sukses, siaran **switch** ke clipC.
- [x] **Auto-hapus**: setelah switch, `clipB.mp4` terhapus (uploads hanya berisi clipC).
- [x] Upload non-video (README.md) → **ditolak** (HTTP 400, pesan jelas).
- [x] `/video_feed` mengalir ~123 KB dalam ~2.5s → streaming UDP jalan.
- [x] Channel default `sample.mp4` tidak terhapus saat switch (hanya file upload yang dihapus).

## Pending / catatan
- UI theater belum ada (Sprint 3) — pengujian lewat route lama + script.
- Loop diuji implisit (klip 3 detik terus berputar); bukti visual di Sprint 3.
