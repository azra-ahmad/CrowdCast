# Sprint 4 — Polish, docs, deploy

## Tujuan
Rapikan pengalaman & dokumentasi: perbaikan playback, empty state, README CrowdCast,
panduan deploy Cloudflare, dan bukti Wireshark.

## Yang dikerjakan

- **Fix video tersendat / loncat mundur.** Penyebab: lebih dari satu `udp_video_server`
  berjalan bersamaan (dua streamer mengirim ke port yang sama di posisi berbeda). Solusi:
  jalankan hanya satu streamer + tambah **guard anti-mundur** di `udp_receiver.py` (frame
  hanya ditampilkan bila `frame_id` lebih baru; id jauh lebih kecil = streamer restart).
- **Empty state**: placeholder "Belum ada siaran — Upload video untuk memulai" (tema dark),
  dan judul siaran menampilkan "Belum ada siaran" bila kosong.
- **README** ditulis ulang untuk CrowdCast: konsep, arsitektur, struktur file, cara
  menjalankan (3 proses), deploy Cloudflare, bukti Wireshark, catatan (tanpa audio, dsb).
- (dari fix sebelumnya) letterbox portrait + logo asli + video tampil di mobile.

## Hasil Testing (terverifikasi)

- [x] Hanya 1 `udp_video_server` + 1 `app` berjalan → stream mengalir (~137 KB/s), tidak
      tersendat/loncat.
- [x] Guard anti-mundur aktif di `udp_receiver` (frame lama diabaikan).
- [x] Empty-state text muncul saat tidak ada siaran (placeholder & judul).

## Pending (dikerjakan saat demo / oleh user)

- Deploy Cloudflare Tunnel (butuh akun Cloudflare kelas) — langkah ada di README.
- Capture Wireshark (`tcp.port==9010`, `udp.port==9020`) sebagai bukti — saat demo.
- Rebranding label "LIVE" (opsional, menunggu keputusan) — lihat catatan di bawah.

## Catatan: "video streaming" vs "live"
Dosen meminta **video streaming** (bukan live camera). CrowdCast menyiarkan **file video yang
di-upload** (bukan kamera langsung), jadi secara teknis sudah "video streaming via UDP". Label
"LIVE" di UI hanya menandakan "sedang menyiarkan"; bisa diganti netral bila diperlukan.
