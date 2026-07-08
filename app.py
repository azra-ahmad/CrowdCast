"""
NetVault - Flask web gateway (UAS Pemrograman Jaringan).
Menyatukan: UI, login, verifikasi email, upload file via TCP, streaming video via UDP.

Alur:
  Browser  <--HTTP-->  Flask (app.py)  <--TCP socket-->  tcp_file_server.py
                                        <--UDP socket-->  udp_video_server.py (via udp_receiver)
"""

import os
import time
import functools
import threading
import uuid

import cv2
import numpy as np
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, Response, jsonify,
)

import config
import auth
import email_sender
import tcp_uploader
import udp_receiver
import broadcast

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_FILE_SIZE + (1024 * 1024)  # sisa buffer

# Mulai penerima UDP di background begitu app hidup
udp_receiver.start()


# ─── Placeholder frame (saat streaming belum ada) ────────────────────────────
def _make_placeholder() -> bytes:
    img = np.full((360, 640, 3), 240, dtype=np.uint8)  # abu terang
    cv2.putText(img, "Menunggu stream UDP...", (110, 185),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (120, 120, 120), 2)
    ok, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


PLACEHOLDER = _make_placeholder()


# ─── State chat & presence (in-memory, tanpa DB) ─────────────────────────────
_chat_lock = threading.Lock()
_messages: list[dict] = []      # {id, user, text, ts}
_next_msg_id = 1
_presence: dict[str, float] = {}  # viewer_id -> last_seen
PRESENCE_TTL = 10               # detik dianggap masih online
MAX_MSG_LEN = 300
MAX_KEEP = 200                  # simpan maksimal pesan terakhir


def _touch_presence():
    """Tandai penonton ini masih aktif (termasuk yang belum login)."""
    vid = session.get("vid")
    if not vid:
        vid = uuid.uuid4().hex
        session["vid"] = vid
    _presence[vid] = time.time()


def _online_count() -> int:
    cutoff = time.time() - PRESENCE_TTL
    return sum(1 for t in _presence.values() if t >= cutoff)


# ─── Helper: wajib login ─────────────────────────────────────────────────────
def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            flash("Silakan login dulu.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ─── Halaman ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Theater publik — semua orang bisa nonton; login untuk chat & ganti siaran."""
    return render_template("theater.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        ok, msg = auth.register_user(username, email, password)
        if not ok:
            flash(msg, "error")
            return render_template("register.html", form=request.form)

        # Kirim OTP ke email
        code = auth.generate_otp(username)
        email_sender.send_otp_email(email, username, code)

        session["pending_user"] = username
        session["pending_email"] = email
        flash("Kode OTP dikirim ke email kamu. Cek inbox / spam.", "success")
        return redirect(url_for("verify"))

    return render_template("register.html", form={})


@app.route("/verify", methods=["GET", "POST"])
def verify():
    username = session.get("pending_user")
    if not username:
        flash("Tidak ada proses verifikasi aktif. Daftar dulu.", "error")
        return redirect(url_for("register"))

    if request.method == "POST":
        code = request.form.get("code", "")
        ok, msg = auth.verify_otp(username, code)
        if ok:
            auth.set_verified(username)
            session.pop("pending_user", None)
            session.pop("pending_email", None)
            flash("Akun terverifikasi! Silakan login.", "success")
            return redirect(url_for("login"))
        flash(msg, "error")

    return render_template("verify.html", email=session.get("pending_email", ""))


@app.route("/resend-otp")
def resend_otp():
    username = session.get("pending_user")
    email = session.get("pending_email")
    if not username or not email:
        return redirect(url_for("register"))
    code = auth.generate_otp(username)
    email_sender.send_otp_email(email, username, code)
    flash("OTP baru sudah dikirim.", "success")
    return redirect(url_for("verify"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        ok, msg = auth.check_login(username, password)
        if ok:
            session["user"] = username
            user = auth.get_user(username)
            if user:
                email_sender.send_login_alert(user["email"], username)  # best-effort
            flash(f"Selamat datang, {username}!", "success")
            return redirect(url_for("index"))

        # Kalau belum verified, arahkan ke verify + kirim ulang OTP
        user = auth.get_user(username)
        if user and not user.get("verified"):
            code = auth.generate_otp(username)
            email_sender.send_otp_email(user["email"], username, code)
            session["pending_user"] = username
            session["pending_email"] = user["email"]
            flash("Akun belum diverifikasi. OTP baru dikirim.", "error")
            return redirect(url_for("verify"))

        flash(msg, "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Kamu sudah logout.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    return redirect(url_for("index"))


# ─── API: Upload via TCP ─────────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
@login_required
def upload():
    """Upload video via TCP; kalau sukses, langsung jadi siaran aktif (now playing)."""
    if "file" not in request.files:
        return jsonify(success=False, message="Tidak ada file."), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify(success=False, message="Nama file kosong."), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in config.ALLOWED_VIDEO_EXT:
        return jsonify(success=False,
                       message="Harus file video (mp4, mkv, avi, mov, webm)."), 400

    # ukuran file dari stream (tanpa baca semua ke RAM)
    stream = f.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)

    filename = os.path.basename(f.filename)
    ok, msg = tcp_uploader.upload_via_tcp(filename, stream, size)

    if ok:
        # jadikan video ini siaran aktif; video lama dihapus oleh streamer saat switch
        broadcast.set_now_playing(os.path.join(config.UPLOAD_DIR, filename))

    return jsonify(success=ok, message=msg), (200 if ok else 502)


# ─── API: Daftar file terupload ──────────────────────────────────────────────
@app.route("/files")
@login_required
def files():
    items = []
    if os.path.isdir(config.UPLOAD_DIR):
        for name in sorted(os.listdir(config.UPLOAD_DIR)):
            if name.startswith("."):
                continue  # sembunyikan .gitkeep dan file tersembunyi
            path = os.path.join(config.UPLOAD_DIR, name)
            if os.path.isfile(path):
                items.append({"name": name, "size": os.path.getsize(path)})
    return jsonify(files=items)


# ─── Chat (polling) ──────────────────────────────────────────────────────────
@app.route("/chat/send", methods=["POST"])
@login_required
def chat_send():
    data = request.get_json(silent=True) or request.form
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(ok=False, message="Pesan kosong."), 400
    if len(text) > MAX_MSG_LEN:
        return jsonify(ok=False, message=f"Pesan maksimal {MAX_MSG_LEN} karakter."), 400

    global _next_msg_id
    with _chat_lock:
        msg = {"id": _next_msg_id, "user": session["user"], "text": text, "ts": time.time()}
        _messages.append(msg)
        _next_msg_id += 1
        if len(_messages) > MAX_KEEP:
            del _messages[:-MAX_KEEP]
    return jsonify(ok=True, id=msg["id"])


@app.route("/chat/poll")
def chat_poll():
    """Publik: siapa pun (termasuk belum login) bisa baca chat & terhitung sebagai penonton."""
    since = request.args.get("since", 0, type=int)
    _touch_presence()
    with _chat_lock:
        new = [m for m in _messages if m["id"] > since]
    now = os.path.basename(broadcast.get_now_playing() or "") or None
    return jsonify(messages=new, online=_online_count(), me=session.get("user"), now=now)


# ─── Streaming: relay frame UDP -> MJPEG ─────────────────────────────────────
@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            frame = udp_receiver.get_latest_frame() or PLACEHOLDER
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(1 / 30)

    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False, threaded=True)
