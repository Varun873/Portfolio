"""Portfolio backend: contact form API (Flask + SQLite + SMTP email)."""
import hmac, os, re, smtplib, sqlite3, threading
from datetime import datetime, timezone
from email.message import EmailMessage

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "messages.db")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
NOTIFY_TO = os.getenv("NOTIFY_TO", SMTP_USER)
ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ORIGINS}})
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day"], storage_uri="memory://")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL, email TEXT NOT NULL, message TEXT NOT NULL,
                 ip TEXT, created_at TEXT NOT NULL)"""
        )


def send_email(name, email, message):
    """Send a notification to the portfolio owner. Skipped if SMTP is not configured."""
    if not (SMTP_USER and SMTP_PASS and NOTIFY_TO):
        return
    msg = EmailMessage()
    msg["Subject"] = "Portfolio message from " + name.replace("\n", " ")[:80]
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_TO
    msg["Reply-To"] = email
    msg.set_content(f"Name: {name}\nEmail: {email}\n\n{message}")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    except Exception as exc:  # the message is already saved, so just log it
        app.logger.error("Email failed: %s", exc)


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/contact")
@limiter.limit("5 per hour")
def contact():
    data = request.get_json(silent=True) or {}
    if data.get("website"):  # honeypot: real visitors leave this empty
        return jsonify(ok=True)
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    message = str(data.get("message", "")).strip()
    if not 1 <= len(name) <= 100:
        return jsonify(error="Please enter your name."), 400
    if len(email) > 200 or not EMAIL_RE.match(email):
        return jsonify(error="Please enter a valid email."), 400
    if not 5 <= len(message) <= 2000:
        return jsonify(error="Message must be 5 to 2000 characters."), 400
    with db() as conn:
        conn.execute(
            "INSERT INTO messages (name, email, message, ip, created_at) VALUES (?,?,?,?,?)",
            (name, email, message, get_remote_address(), datetime.now(timezone.utc).isoformat()),
        )
    threading.Thread(target=send_email, args=(name, email, message), daemon=True).start()
    return jsonify(ok=True), 201


@app.get("/api/messages")
def messages():
    """Owner-only list of messages. Send header: Authorization: Bearer <ADMIN_TOKEN>."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not ADMIN_TOKEN or not hmac.compare_digest(token, ADMIN_TOKEN):
        return jsonify(error="Unauthorized"), 401
    with db() as conn:
        rows = conn.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 200").fetchall()
    return jsonify([dict(r) for r in rows])


init_db()

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", "5000")), debug=True)
