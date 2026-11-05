"""SQLite storage: users, login tokens and every scan (this is also the
'tracking' layer that feeds the admin analytics)."""
import hashlib
import json
import os
import secrets
import sqlite3
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "fineprint.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            pw_hash TEXT NOT NULL, salt TEXT NOT NULL, created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS tokens(
            token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS scans(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            url TEXT NOT NULL, domain TEXT NOT NULL, score INTEGER NOT NULL,
            result TEXT NOT NULL, created_at REAL NOT NULL);
        """)


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()


def create_user(email, name, password):
    salt = secrets.token_hex(16)
    try:
        with _conn() as c:
            cur = c.execute(
                "INSERT INTO users(email,name,pw_hash,salt,created_at) VALUES(?,?,?,?,?)",
                (email.lower().strip(), name.strip(), _hash(password, salt), salt, time.time()))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def verify_user(email, password):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
    if row and secrets.compare_digest(row["pw_hash"], _hash(password, row["salt"])):
        return dict(row)
    return None


def create_token(user_id):
    token = secrets.token_urlsafe(32)
    with _conn() as c:
        c.execute("INSERT INTO tokens VALUES(?,?,?)", (token, user_id, time.time()))
    return token


def user_from_token(token):
    if not token:
        return None
    with _conn() as c:
        row = c.execute(
            "SELECT u.id,u.email,u.name FROM tokens t JOIN users u ON u.id=t.user_id WHERE t.token=?",
            (token,)).fetchone()
    return dict(row) if row else None


def save_scan(user_id, result):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO scans(user_id,url,domain,score,result,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, result["url"], result["domain"], result["score"], json.dumps(result), time.time()))
        return cur.lastrowid


def list_scans(user_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT id,url,domain,score,created_at FROM scans WHERE user_id=? ORDER BY id DESC LIMIT 50",
            (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_scan(scan_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
    if not row:
        return None
    data = json.loads(row["result"])
    data["id"], data["user_id"], data["created_at"] = row["id"], row["user_id"], row["created_at"]
    return data


def all_scores():
    with _conn() as c:
        return [r["score"] for r in c.execute("SELECT score FROM scans").fetchall()]


def stats():
    with _conn() as c:
        rows = c.execute("SELECT domain,score,result,created_at FROM scans ORDER BY id DESC").fetchall()
        users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    trackers, labels, scores = {}, {}, []
    for r in rows:
        scores.append(r["score"])
        data = json.loads(r["result"])
        for t in data.get("trackers", []):
            trackers[t["name"]] = trackers.get(t["name"], 0) + 1
        for cl in data.get("clauses", []):
            labels[cl["label_name"]] = labels.get(cl["label_name"], 0) + 1
    top = lambda d: sorted(({"name": k, "count": v} for k, v in d.items()), key=lambda x: -x["count"])[:6]
    return {
        "total_scans": len(rows), "total_users": users,
        "average_score": round(sum(scores) / len(scores), 1) if scores else None,
        "lowest": sorted(({"domain": r["domain"], "score": r["score"]} for r in rows), key=lambda x: x["score"])[:5],
        "top_trackers": top(trackers), "top_risks": top(labels),
    }
