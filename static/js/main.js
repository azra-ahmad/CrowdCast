/* NetVault — GSAP reveal + packet-flow signature + upload(TCP) & video(UDP) logic */

document.addEventListener("DOMContentLoaded", () => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (window.gsap && !reduce) {
    gsap.to(".reveal", { opacity: 1, y: 0, duration: 0.6, ease: "power2.out", stagger: 0.07 });
  } else {
    document.querySelectorAll(".reveal").forEach((el) => (el.style.opacity = 1));
  }

  // flash auto-dismiss
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      if (window.gsap && !reduce) gsap.to(el, { opacity: 0, x: 20, duration: 0.4, onComplete: () => el.remove() });
      else el.remove();
    }, 4500);
  });

  initPacketFlow(reduce);
  initUpload();
  initVideo();
});

// ─── Signature: aliran paket TCP vs UDP ─────────────────────────────────────
function initPacketFlow(reduce) {
  const tcpLane = document.getElementById("tcpLane");
  const udpLane = document.getElementById("udpLane");
  if (!tcpLane || !udpLane) return;

  const NS = "http://www.w3.org/2000/svg";
  const START = 112, END = 596, TCP_Y = 65.5, UDP_Y = 125.5, SPAN = END - START;

  function packet(color, y) {
    const r = document.createElementNS(NS, "rect");
    r.setAttribute("width", "16"); r.setAttribute("height", "9");
    r.setAttribute("rx", "2"); r.setAttribute("fill", color);
    r.setAttribute("x", START); r.setAttribute("y", y);
    return r;
  }

  if (!window.gsap || reduce) {
    // fallback statis
    [0.25, 0.5, 0.75].forEach((f) => { const r = packet("#38BDF8", TCP_Y); r.setAttribute("x", START + SPAN * f); tcpLane.appendChild(r); });
    [0.35, 0.65].forEach((f) => { const r = packet("#FBBF24", UDP_Y); r.setAttribute("x", START + SPAN * f); udpLane.appendChild(r); });
    return;
  }

  // TCP: setiap paket sampai, berurutan
  function sendTCP() {
    const r = packet("#38BDF8", TCP_Y); tcpLane.appendChild(r);
    gsap.fromTo(r, { x: 0 }, {
      x: SPAN, duration: 2.1, ease: "none",
      onComplete: () => gsap.to(r, { opacity: 0, duration: 0.2, onComplete: () => r.remove() }),
    });
  }

  // UDP: lebih cepat, sebagian drop di tengah
  function sendUDP() {
    const r = packet("#FBBF24", UDP_Y); udpLane.appendChild(r);
    const drop = Math.random() < 0.35;
    const endX = drop ? SPAN * (0.3 + Math.random() * 0.4) : SPAN;
    const tl = gsap.timeline({ onComplete: () => r.remove() });
    tl.fromTo(r, { x: 0, opacity: 1 }, { x: endX, duration: 1.3, ease: "none" });
    tl.to(r, { opacity: 0, duration: drop ? 0.25 : 0.2 }, drop ? "-=0.1" : ">");
  }

  sendTCP(); sendUDP();
  setInterval(sendTCP, 780);
  setInterval(sendUDP, 430);
}

// ─── Upload via TCP (progress bar) ──────────────────────────────────────────
function initUpload() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const uploadBtn = document.getElementById("uploadBtn");
  if (!dropzone || !fileInput || !uploadBtn) return;

  const dzMain = document.getElementById("dzMain");
  const dzSub = document.getElementById("dzSub");
  const progressWrap = document.getElementById("progressWrap");
  const progressBar = document.getElementById("progressBar");
  const progressPct = document.getElementById("progressPct");
  const progressName = document.getElementById("progressName");

  let selectedFile = null;

  function pickFile(file) {
    selectedFile = file;
    dzMain.textContent = file.name;
    dzSub.textContent = formatSize(file.size);
    uploadBtn.disabled = false;
  }

  fileInput.addEventListener("change", (e) => { if (e.target.files.length) pickFile(e.target.files[0]); });

  ["dragenter", "dragover"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag"); }));
  dropzone.addEventListener("drop", (e) => { if (e.dataTransfer.files.length) pickFile(e.dataTransfer.files[0]); });

  uploadBtn.addEventListener("click", () => {
    if (!selectedFile) return;
    const form = new FormData();
    form.append("file", selectedFile);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", UPLOAD_URL);
    progressWrap.classList.add("show");
    progressName.textContent = selectedFile.name;
    uploadBtn.disabled = true;

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = pct + "%";
        progressPct.textContent = pct + "%";
      }
    });

    xhr.onload = () => {
      let res = {};
      try { res = JSON.parse(xhr.responseText); } catch (_) {}
      if (xhr.status === 200 && res.success) {
        progressPct.textContent = "done";
        loadFiles();
        resetDropzone();
      } else {
        progressPct.textContent = "gagal";
        alert(res.message || "Upload gagal.");
        uploadBtn.disabled = false;
      }
    };
    xhr.onerror = () => { progressPct.textContent = "error"; alert("Koneksi ke server bermasalah."); uploadBtn.disabled = false; };
    xhr.send(form);
  });

  function resetDropzone() {
    setTimeout(() => {
      selectedFile = null;
      fileInput.value = "";
      dzMain.textContent = "Klik atau tarik file ke sini";
      dzSub.textContent = "semua tipe file didukung";
      progressWrap.classList.remove("show");
      progressBar.style.width = "0%";
    }, 1200);
  }

  loadFiles();

  function loadFiles() {
    fetch(FILES_URL).then((r) => r.json()).then((data) => {
      const list = document.getElementById("fileList");
      if (!data.files.length) {
        list.innerHTML = '<div class="empty">belum ada file terupload</div>';
        return;
      }
      const icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
      list.innerHTML = data.files.map((f) => `
        <div class="file-row">
          <span class="fname">${icon} ${escapeHtml(f.name)} <span class="tag tag-tcp">TCP</span></span>
          <span class="fsize">${formatSize(f.size)}</span>
        </div>`).join("");
      if (window.gsap) gsap.from(".file-row", { opacity: 0, y: 8, duration: 0.4, stagger: 0.05 });
    }).catch(() => {});
  }
}

// ─── Streaming via UDP ──────────────────────────────────────────────────────
function initVideo() {
  const img = document.getElementById("videoImg");
  const playBtn = document.getElementById("playBtn");
  const stopBtn = document.getElementById("stopBtn");
  const liveTag = document.getElementById("liveTag");
  const fpsStat = document.getElementById("fpsStat");
  if (!img || !playBtn || !stopBtn) return;

  let fpsTimer = null, frameCount = 0;

  playBtn.addEventListener("click", () => {
    img.src = VIDEO_FEED_URL + "?t=" + Date.now();
    liveTag.classList.add("on");
    liveTag.innerHTML = '<span class="pulse"></span> LIVE';
    playBtn.disabled = true;
    stopBtn.disabled = false;
    frameCount = 0;
    img.onload = () => frameCount++;
    fpsTimer = setInterval(() => { fpsStat.textContent = frameCount + " fps"; frameCount = 0; }, 1000);
  });

  stopBtn.addEventListener("click", () => {
    img.src = "";
    img.onload = null;
    liveTag.classList.remove("on");
    liveTag.innerHTML = '<span class="pulse"></span> OFFLINE';
    fpsStat.textContent = "0 fps";
    playBtn.disabled = false;
    stopBtn.disabled = true;
    if (fpsTimer) clearInterval(fpsTimer);
  });
}

// ─── Util ───────────────────────────────────────────────────────────────────
function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}
function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
