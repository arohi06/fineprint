"""Fineprint API + static frontend, all served by FastAPI."""
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import database as db
from .analyzer import BENCHMARKS, ScanError, analyze
from .ml_model import get_model
from .report import build_report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")

app = FastAPI(title="Fineprint", version="1.0")
db.init()
get_model()  # train / load the NLP model at startup


class Register(BaseModel):
    name: str
    email: str
    password: str


class Login(BaseModel):
    email: str
    password: str


class ScanReq(BaseModel):
    url: str


def current_user(authorization):
    if authorization and authorization.lower().startswith("bearer "):
        return db.user_from_token(authorization[7:])
    return None


def require_user(authorization):
    u = current_user(authorization)
    if not u:
        raise HTTPException(401, "Please log in first.")
    return u


@app.post("/api/register")
def register(body: Register):
    if len(body.password) < 6 or "@" not in body.email or not body.name.strip():
        raise HTTPException(400, "Enter a name, a valid email and a password of 6+ characters.")
    uid = db.create_user(body.email, body.name, body.password)
    if not uid:
        raise HTTPException(409, "That email is already registered.")
    return {"token": db.create_token(uid), "user": {"id": uid, "name": body.name.strip(), "email": body.email}}


@app.post("/api/login")
def login(body: Login):
    u = db.verify_user(body.email, body.password)
    if not u:
        raise HTTPException(401, "Wrong email or password.")
    return {"token": db.create_token(u["id"]), "user": {"id": u["id"], "name": u["name"], "email": u["email"]}}


@app.get("/api/me")
def me(authorization: str = Header(None)):
    u = require_user(authorization)
    u["is_admin"] = u["id"] == 1  # first registered account is the admin
    return u


@app.post("/api/scan")
def scan(body: ScanReq, authorization: str = Header(None)):
    user = current_user(authorization)
    try:
        result = analyze(body.url)
    except ScanError as ex:
        raise HTTPException(400, str(ex))

    scores = db.all_scores()
    below = sum(1 for s in scores if s < result["score"])
    result["comparison"] = {
        "site": result["score"],
        "average": round(sum(scores) / len(scores), 1) if scores else None,
        "percentile": round(100 * below / len(scores)) if len(scores) >= 5 else None,
        "sample_size": len(scores),
        "benchmarks": BENCHMARKS,
    }
    result["id"] = db.save_scan(user["id"] if user else None, result)
    return result


@app.get("/api/history")
def history(authorization: str = Header(None)):
    return db.list_scans(require_user(authorization)["id"])


def _owned_scan(scan_id, authorization):
    r = db.get_scan(scan_id)
    if not r:
        raise HTTPException(404, "Scan not found.")
    if r["user_id"] is not None:
        u = current_user(authorization)
        if not u or u["id"] != r["user_id"]:
            raise HTTPException(403, "This scan belongs to another account.")
    return r


@app.get("/api/scan/{scan_id}")
def get_scan(scan_id: int, authorization: str = Header(None)):
    return _owned_scan(scan_id, authorization)


@app.get("/api/report/{scan_id}", response_class=HTMLResponse)
def report(scan_id: int, authorization: str = Header(None)):
    r = _owned_scan(scan_id, authorization)
    html = build_report(r)
    return HTMLResponse(html, headers={"Content-Disposition": f'attachment; filename="fineprint-{r["domain"]}.html"'})


@app.get("/api/admin/stats")
def admin_stats(authorization: str = Header(None)):
    if require_user(authorization)["id"] != 1:
        raise HTTPException(403, "Admins only.")
    return db.stats()


app.mount("/assets", StaticFiles(directory=FRONTEND), name="assets")


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))
