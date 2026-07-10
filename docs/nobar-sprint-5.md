# Sprint 5 — Audio via HTTP, diselaraskan ke siaran UDP

## Latar belakang
Syarat tugas diperbarui: cukup **TCP, UDP, atau HTTP** (tidak lagi mewajibkan kombinasi
tertentu). Audio tidak diwajibkan, tapi diinginkan. Masalahnya: video dikirim sebagai frame
JPEG lewat UDP — gambar tidak membawa suara.

**Opsi yang ditolak** dan alasannya:
- Ganti ke tag `<video>` (HTTP) → dapat audio, tapi **menghancurkan konsep theater**: tiap
  penonton memutar berkasnya sendiri, tidak tersinkron, chat jadi tidak nyambung.
- WebRTC → benar secara teknis, tapi (a) Cloudflare Tunnel hanya menyalurkan HTTP sehingga
  media WebRTC butuh TURN/IP publik, (b) perlu SFU + signaling, (c) socket UDP yang ditulis
  sendiri digantikan library — justru menghilangkan inti mata kuliah.

## Solusi: pisahkan jalur, satukan jamnya

- **Video** tetap lewat **UDP** (boleh drop frame).
- **Audio** diambil lewat **HTTP** dari berkas video yang sama (harus utuh, bisa di-seek).
- **Penyelaras**: posisi putar (`pos_ms`) dititipkan di **header paket UDP**, jadi waktu berjalan
  bersama framenya — tanpa jalur IPC tambahan. Klien menyeret audio ke posisi itu.

Karena semua penonton mengacu ke jam yang sama (jam server), mereka mendengar momen yang sama.

## Perubahan

| File | Perubahan |
| --- | --- |
| `udp_video_server.py` | Header `!IHH` → `!IHHI` (+`pos_ms`); ambil `CAP_PROP_POS_MSEC` (fallback ke `POS_FRAMES/fps`) |
| `udp_receiver.py` | Unpack `pos_ms`, simpan bersama frame, tambah `get_latest_pos_ms()` |
| `app.py` | Route `/audio` (kirim berkas aktif, `conditional=True` → HTTP Range); `pos` ikut di `/chat/poll` |
| `templates/theater.html` | Elemen `<audio>` tersembunyi + tombol audio di kontrol player |
| `static/js/main.js` | `initAudio()` / `syncAudio()`: seek bila melenceng > 0,75 detik; muat ulang saat siaran berganti |
| `static/css/style.css` | State tombol audio (`.ico.on`) |

**Keamanan**: `/audio` hanya menyajikan berkas yang sedang disiarkan (`broadcast.get_now_playing()`);
path tidak pernah berasal dari input pengguna.

## Hasil Testing (terverifikasi)

- [x] Header baru `!IHHI` = **12 byte**; roundtrip `pack/unpack` benar.
- [x] Datagram maksimum 40012 byte → masih jauh di bawah batas UDP (~65507).
- [x] Syntax check Python (`py_compile`) & JavaScript (`node --check`) lolos.

## Pending (diuji manual oleh user)

- [ ] Audio berbunyi setelah tombol ditekan, dan **selaras** dengan video.
- [ ] Saat siaran diganti, audio ikut berganti.
- [ ] Saat video loop ke awal, audio ikut mundur (koreksi drift).

## Catatan jujur / keterbatasan

- Sinkronisasi **perkiraan** (toleransi ~0,75 detik), bukan frame-accurate. Cocok untuk
  slide/musik/narasi; video dengan gerak bibir akan terlihat sedikit meleset.
- Audio hanya berbunyi bila codec didukung browser (mp4/webm aman; mkv/avi sering tidak).
- Browser melarang audio otomatis → perlu satu klik tombol.
- `/audio` mengirim berkas video utuh ke tiap penonton (browser hanya memakai track audionya).
  Perbaikan lanjutan: ekstrak audio ke berkas terpisah, atau pindah ke RTP/WebRTC.
