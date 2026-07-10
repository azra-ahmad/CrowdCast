/* CrowdCast — theater: chat polling + kirim + upload (ganti tontonan) */

document.addEventListener("DOMContentLoaded", () => {
  // auto-dismiss flash
  document.querySelectorAll(".flash").forEach((el) => setTimeout(() => el.remove(), 4500));

  if (document.getElementById("msgs")) {
    startChat();
    initCast();
    initAudio();
  }
});

// ─── Audio via HTTP, diselaraskan ke posisi siaran (jam server) ──────────────
// Video datang lewat UDP (boleh drop frame), audio lewat HTTP (harus utuh).
// Keduanya diikat ke `pos` dari server, jadi semua penonton dengar momen yang sama.
const DRIFT_TOLERANCE = 0.75;   // detik; di bawah ini dibiarkan jalan sendiri
const DRIFT_BIG = 3.0;          // lompatan besar (mis. video loop) -> koreksi langsung
const SEEK_COOLDOWN = 2000;     // ms; cegah seek beruntun yang malah bikin patah-patah
let _audioEl = null, _audioBtn = null, _audioOn = false;
let _loadedName = null, _currentName = null;
let _lastSeekAt = 0, _driftHits = 0;

const ICON_MUTE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>';
const ICON_SOUND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>';

function initAudio() {
  _audioEl = document.getElementById("audioTrack");
  _audioBtn = document.getElementById("audioBtn");
  if (!_audioEl || !_audioBtn) return;

  _audioBtn.addEventListener("click", () => {
    _audioOn = !_audioOn;
    if (_audioOn) {
      ensureAudioSrc(_currentName);          // baru diunduh saat audio dinyalakan
      _audioEl.play().catch(() => {});
    } else {
      _audioEl.pause();
    }
    paintAudioBtn();
  });

  _audioEl.addEventListener("error", () => {
    if (!_audioOn) return;
    _audioOn = false;
    paintAudioBtn();
    toast("Browser tidak bisa memutar audio dari format video ini.", "error");
  });

  paintAudioBtn();
}

function paintAudioBtn() {
  if (!_audioBtn) return;
  _audioBtn.innerHTML = _audioOn ? ICON_SOUND : ICON_MUTE;
  _audioBtn.classList.toggle("on", _audioOn);
  _audioBtn.title = _audioOn ? "Matikan audio" : "Nyalakan audio";
  _audioBtn.setAttribute("aria-label", _audioBtn.title);
}

function seekAudio(pos) {
  try { _audioEl.currentTime = pos; } catch (_) {}
  _lastSeekAt = Date.now();
  _driftHits = 0;
}

function ensureAudioSrc(name) {
  if (!_audioEl || !name || _loadedName === name) return;
  _loadedName = name;
  _audioEl.src = AUDIO_URL + "?v=" + encodeURIComponent(name);
}

function syncAudio(name, pos) {
  _currentName = name;
  if (!_audioEl || !_audioOn || !name || typeof pos !== "number") return;

  if (_loadedName !== name) {           // siaran berganti -> muat audio baru
    ensureAudioSrc(name);
    _driftHits = 0;
    _audioEl.play().catch(() => {});
    return;                            // biarkan poll berikutnya yang menyelaraskan
  }
  if (_audioEl.readyState < 1) return; // metadata belum siap, belum bisa di-seek
  if (_audioEl.seeking) return;        // masih pindah posisi, jangan ditumpuk

  const drift = Math.abs(_audioEl.currentTime - pos);
  const cooling = Date.now() - _lastSeekAt < SEEK_COOLDOWN;

  if (drift <= DRIFT_TOLERANCE) {
    _driftHits = 0;                    // masih selaras, biarkan jalan sendiri
  } else if (drift >= DRIFT_BIG) {
    seekAudio(pos);                    // loncatan besar (video loop) -> koreksi segera
  } else if (++_driftHits >= 2 && !cooling) {
    seekAudio(pos);                    // melenceng konsisten 2 poll -> baru dikoreksi
  }

  if (_audioEl.paused) _audioEl.play().catch(() => {});
}

// ─── Chat (polling 1.2s) ─────────────────────────────────────────────────────
function startChat() {
  const msgs = document.getElementById("msgs");
  const onlineCount = document.getElementById("onlineCount");
  const onlineChip = document.getElementById("onlineChip");
  const nowTitle = document.getElementById("nowTitle");
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSend");
  let lastId = 0;
  const seen = new Set();

  function poll() {
    fetch(CHAT_POLL_URL + "?since=" + lastId)
      .then((r) => r.json())
      .then((data) => {
        const nearBottom = msgs.scrollTop + msgs.clientHeight >= msgs.scrollHeight - 50;
        data.messages.forEach((m) => {
          if (seen.has(m.id)) return;          // cegah dobel (race poll)
          seen.add(m.id);
          if (m.id > lastId) lastId = m.id;
          const div = document.createElement("div");
          div.className = "m";
          div.innerHTML = `<span class="u" style="color:${userColor(m.user)}">@${escapeHtml(m.user)}</span> ${escapeHtml(m.text)}`;
          msgs.appendChild(div);
        });
        if (data.messages.length && nearBottom) msgs.scrollTop = msgs.scrollHeight;
        if (onlineCount) onlineCount.textContent = data.online;
        if (onlineChip) onlineChip.textContent = data.online;
        if (nowTitle) nowTitle.textContent = data.now || "Belum ada siaran";
        syncAudio(data.now, data.pos);
      })
      .catch(() => {});
  }
  poll();
  setInterval(poll, 1200);

  // kirim pesan (kalau login)
  if (input && sendBtn && typeof CHAT_SEND_URL !== "undefined") {
    function send() {
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      fetch(CHAT_SEND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      }).then(() => poll()).catch(() => {});
    }
    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); send(); } });
  }
}

// ─── Ganti tontonan (upload video) ───────────────────────────────────────────
function initCast() {
  const castBtn = document.getElementById("castBtn");
  const fileInput = document.getElementById("fileInput");
  if (!castBtn || !fileInput || typeof UPLOAD_URL === "undefined") return;

  const overlay = document.getElementById("upOverlay");
  const bar = document.getElementById("upBar");
  const label = document.getElementById("upLabel");

  castBtn.addEventListener("click", () => fileInput.click());

  const ALLOWED_EXT = /\.(mp4|mkv|avi|mov|webm)$/i;

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;

    // ── validasi di client: gagal cepat, jangan biarkan user menunggu sia-sia ──
    if (!ALLOWED_EXT.test(file.name)) {
      toast("Harus file video (mp4, mkv, avi, mov, webm).", "error");
      fileInput.value = "";
      return;
    }
    if (typeof MAX_UPLOAD_BYTES === "number" && file.size > MAX_UPLOAD_BYTES) {
      toast(`Video terlalu besar (${fmtSize(file.size)}). Maksimal ${fmtSize(MAX_UPLOAD_BYTES)}.`, "error");
      fileInput.value = "";
      return;
    }

    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", UPLOAD_URL);
    overlay.classList.add("show");
    label.textContent = "Mengunggah " + file.name;
    bar.style.width = "0%";
    castBtn.disabled = true;

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) bar.style.width = Math.round((e.loaded / e.total) * 100) + "%";
    });
    function fail(msg) {
      castBtn.disabled = false;
      fileInput.value = "";
      overlay.classList.remove("show");
      toast(msg, "error");
    }

    xhr.onload = () => {
      // Cloudflare/Flask bisa membalas HTML saat menolak; jangan asumsikan JSON
      let res = {};
      try { res = JSON.parse(xhr.responseText); } catch (_) {}

      if (xhr.status === 200 && res.success) {
        castBtn.disabled = false;
        fileInput.value = "";
        label.textContent = "Siaran diganti!";
        toast(res.message || "Siaran diganti.", "success");
        setTimeout(() => overlay.classList.remove("show"), 900);
        return;
      }
      if (res.message) return fail(res.message);
      if (xhr.status === 413) return fail("Video terlalu besar — ditolak server.");
      if (xhr.status === 502) return fail("File server (TCP) tidak merespons. Cek apakah tcp_file_server.py jalan.");
      fail(`Gagal mengganti siaran (HTTP ${xhr.status}).`);
    };
    xhr.onerror = () => fail("Koneksi terputus saat mengunggah. Coba ulangi, atau pakai video yang lebih kecil.");
    xhr.onabort = () => fail("Upload dibatalkan.");
    xhr.send(form);
  });
}

// ─── util ────────────────────────────────────────────────────────────────────
function toast(msg, kind) {
  let box = document.querySelector(".flashes");
  if (!box) { box = document.createElement("div"); box.className = "flashes"; document.body.appendChild(box); }
  const el = document.createElement("div");
  el.className = "flash " + (kind || "success");
  el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

// Warna nama: palet dengan jarak hue 30 derajat (pasti bisa dibedakan mata), saturasi &
// terang dikunci agar terbaca di latar gelap, dan merah dilewati (itu warna aksen aplikasi).
// Warna dibagikan menurut urutan kemunculan pertama di chat. Karena setiap klien memuat
// riwayat pesan yang sama dan terurut, hasilnya konsisten di semua perangkat — sekaligus
// menjamin tidak ada dua pengguna berwarna sama (sampai 11 pengguna).
const NAME_HUES = [20, 50, 80, 110, 140, 170, 200, 230, 260, 290, 320];
const _userColors = new Map();
function userColor(name) {
  if (!_userColors.has(name)) {
    const hue = NAME_HUES[_userColors.size % NAME_HUES.length];
    _userColors.set(name, `hsl(${hue} 75% 68%)`);
  }
  return _userColors.get(name);
}
function fmtSize(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}
