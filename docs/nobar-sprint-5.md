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

## Bug yang ditemukan saat pengujian: "audio lompat mundur"

Gejala: audio berulang kali ditarik mundur beberapa detik.

**Penyebab sebenarnya — siaran berjalan lebih lambat dari 1×.** Streamer memakai
`time.sleep(1/fps)`, sehingga waktu baca + resize + encode + kirim **ikut menambah** jeda.
Diukur: posisi siaran hanya maju ~0,42 detik tiap 0,5 detik nyata (**~0,85×**). Audio browser
selalu berjalan 1,0× → makin lama makin menyalip → melewati toleransi → **ditarik mundur**.
Jadi yang lompat adalah **audionya**, bukan videonya.

**Perbaikan (pacing real-time):** jadwalkan frame berikutnya berdasarkan jam
(`next_frame_at += delay`, tidur sisa waktunya), bukan tidur tetap. Kalau terlambat, jadwal
di-reset supaya "utang waktu" tidak menumpuk.

## Bug kedua: dua streamer saling rebutan

Guard lama (`last_id - frame_id > 300` dianggap restart) membuat dua streamer yang jalan
bersamaan **bergantian diterima** → siaran maju-mundur. Diperbaiki dengan **`stream_id`**
(acak per proses) di header: penerima mengunci satu streamer, mengabaikan yang lain, dan hanya
berpindah bila streamer terkunci diam > 2 detik.

Header final: `!IIHHI` → `stream_id | frame_id | total | index | pos_ms` (**16 byte**).

## Hasil Testing (terverifikasi)

Diuji pada instance terisolasi (port 5099 / UDP 9099) agar tidak mengganggu server yang berjalan.

- [x] Header `!IIHHI` = **16 byte**; roundtrip `pack/unpack` benar; datagram maks 40016 byte
      (jauh di bawah ~65507).
- [x] **Anti streamer-dobel**: 24 sampel `pos` sambil sengaja menyalakan streamer kedua di
      tengah pengujian → **0 kali posisi mundur**.
- [x] **Tempo real-time**: posisi maju 8,00 detik dalam 8,00 detik nyata → **0,999×**
      (sebelum perbaikan: ~0,85×).
- [x] Syntax check Python (`py_compile`) & JavaScript (`node --check`) lolos.

## Perbaikan UI

**1. Chat memanjangkan halaman (bukan menggulung sendiri).**
`overflow-y:auto` pada `.msgs` hanya menghasilkan area gulung bila tingginya **pasti**.
Sebelumnya tinggi `.chat` ditentukan flex dari isinya → chat memanjang → baris ikut memanjang →
`.player` teregang (muncul area hitam panjang di bawah video).
Perbaikan: chat dibungkus `.chat-wrap` (tanpa tinggi sendiri, ikut tinggi player lewat
`align-items:stretch`), lalu `.chat` dipasang `position:absolute; inset:0` sehingga isinya
tidak mungkin mendorong tinggi.

Terverifikasi di browser (viewport 1280×800), setelah menyuntik 60 pesan:

| Metrik | Hasil |
| --- | --- |
| Tinggi player vs chat | 484 px : 484 px (sama) |
| `.msgs` menggulung | ya (isi 3178 px, jendela 380 px) |
| Halaman memanjang | **0 px** |

**2. Warna nama per pengguna.**
Palet 11 hue berjarak 30° (pasti terbedakan mata), saturasi/terang dikunci agar terbaca di
latar gelap, merah dilewati karena dipakai sebagai warna aksen. Warna dibagikan menurut
**urutan kemunculan pertama** di chat — karena setiap klien memuat riwayat pesan yang sama dan
terurut, hasilnya konsisten di semua perangkat sekaligus menjamin tidak ada warna kembar.

> Percobaan awal memakai hash → HSL 330 hue ditolak: `ajrahari` (hue 240) dan `aditonomy`
> (hue 242) secara teknis berbeda, tapi terlihat sama persis.

Terverifikasi: 6 pengguna → 6 warna berbeda, identik antar klien.

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
