/* CrowdCast — theater: chat polling + kirim + upload (ganti tontonan) */

document.addEventListener("DOMContentLoaded", () => {
  // auto-dismiss flash
  document.querySelectorAll(".flash").forEach((el) => setTimeout(() => el.remove(), 4500));

  if (document.getElementById("msgs")) {
    startChat();
    initCast();
  }
});

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
          div.innerHTML = `<span class="u">@${escapeHtml(m.user)}</span> ${escapeHtml(m.text)}`;
          msgs.appendChild(div);
        });
        if (data.messages.length && nearBottom) msgs.scrollTop = msgs.scrollHeight;
        if (onlineCount) onlineCount.textContent = data.online;
        if (onlineChip) onlineChip.textContent = data.online;
        if (nowTitle) nowTitle.textContent = data.now || "Belum ada siaran";
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
function fmtSize(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}
