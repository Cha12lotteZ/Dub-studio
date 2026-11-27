"""Dub Studio web server. Run: uvicorn app.main:app --reload  then open http://localhost:8000"""
from __future__ import annotations

import base64
import hmac
import io
import json
import os
import re
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from . import ai, effects, media

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DUB_DATA", ROOT / "data"))
PROJECTS, MODELS, DATASET = DATA / "projects", DATA / "models", DATA / "dataset"
for d in (PROJECTS, MODELS, DATASET):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Dub Studio")


@app.middleware("http")
async def password_gate(request: Request, call_next):
    """Optional login for public hosting (e.g. Hugging Face Spaces): set DUB_PASSWORD.
    Any username works; only the password is checked."""
    password = os.environ.get("DUB_PASSWORD")
    if password:
        ok = False
        auth = request.headers.get("authorization", "")
        if auth.startswith("Basic "):
            try:
                given = base64.b64decode(auth[6:]).decode("utf-8").split(":", 1)[1]
                ok = hmac.compare_digest(given.encode(), password.encode())
            except (ValueError, IndexError, UnicodeDecodeError):
                ok = False
        if not ok:
            return Response("ต้องใส่รหัสผ่าน", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Dub Studio", charset="UTF-8"'})
    return await call_next(request)
_lock = threading.Lock()


# ---------- storage ----------

def _safe(name: str) -> str:
    return re.sub(r"[^\w\-ก-๙]+", "_", name).strip("_")[:60] or "untitled"


def _pdir(pid: str) -> Path:
    p = PROJECTS / _safe(pid)
    if not (p / "project.json").exists():
        raise HTTPException(404, "ไม่พบโปรเจกต์นี้")
    return p


def _load(pid: str) -> dict:
    return json.loads((_pdir(pid) / "project.json").read_text("utf-8"))


def _save(proj: dict) -> dict:
    path = PROJECTS / proj["id"] / "project.json"
    with _lock:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(proj, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(path)
    return proj


def _line(proj: dict, lid: str) -> dict:
    for ln in proj["lines"]:
        if ln["id"] == lid:
            return ln
    raise HTTPException(404, "ไม่พบบรรทัดนี้")


def _new_line(start: float = 0.0, end: float | None = None, text: str = "", who: str = "") -> dict:
    return {"id": uuid.uuid4().hex[:8], "start": start, "end": end if end is not None else start + 2, "text": text,
            "who": who, "settings": {"character": "me", "mood": "normal", "atmosphere": "none", "mix": 0.6, "pitch": None},
            "model": None, "raw": None, "fx": None, "kept": False}


async def _store_upload(up: UploadFile, dst_dir: Path, stem: str) -> Path:
    suffix = Path(up.filename or "").suffix.lower() or ".bin"
    raw = dst_dir / f"{stem}_upload{suffix}"
    with raw.open("wb") as f:
        shutil.copyfileobj(up.file, f)
    return raw


def _err(e: Exception) -> HTTPException:
    if isinstance(e, ai.NotInstalled):
        return HTTPException(501, str(e))
    if isinstance(e, (media.MediaError, FileNotFoundError, KeyError, ValueError)):
        return HTTPException(400, str(e))
    return HTTPException(500, f"เกิดข้อผิดพลาด: {e}")


# ---------- catalog ----------

def _models() -> list[dict]:
    out = []
    for d in sorted(MODELS.iterdir()):
        if d.is_dir() and any(d.glob("*.pth")):
            out.append({"id": d.name, "name": d.name, "has_index": any(d.glob("*.index"))})
    return out


def _dataset_info() -> dict:
    meta = DATASET / "takes.jsonl"
    takes = [json.loads(l) for l in meta.read_text("utf-8").splitlines() if l.strip()] if meta.exists() else []
    return {"takes": len(takes), "minutes": round(sum(t.get("seconds", 0) for t in takes) / 60, 1)}


@app.get("/api/catalog")
def catalog():
    return {**effects.catalog(), "ai": {**ai.status(), "ffmpeg": ai.ffmpeg_ok()}, "models": _models(),
            "dataset": _dataset_info()}


# ---------- projects ----------

@app.get("/api/projects")
def list_projects():
    items = []
    for p in sorted(PROJECTS.glob("*/project.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        d = json.loads(p.read_text("utf-8"))
        items.append({"id": d["id"], "name": d["name"], "lines": len(d["lines"]), "has_video": bool(d.get("video"))})
    return items


@app.post("/api/projects")
async def create_project(name: str = Form(...), video: UploadFile | None = File(None)):
    pid = f"{_safe(name)}-{uuid.uuid4().hex[:6]}"
    pdir = PROJECTS / pid
    (pdir / "takes").mkdir(parents=True)
    proj = {"id": pid, "name": name, "video": None, "audio": None, "background": None, "duration": 0.0,
            "lines": [], "created": time.time()}
    (pdir / "project.json").write_text("{}", "utf-8")
    if video is not None and video.filename:
        try:
            raw = await _store_upload(video, pdir, "video")
            vid = raw.rename(pdir / f"video{raw.suffix}")
            media.to_wav(vid, pdir / "audio.wav", mono=False)
            proj.update(video=vid.name, audio="audio.wav", background="audio.wav", duration=media.duration(vid))
        except Exception as e:  # keep the folder consistent on failure
            shutil.rmtree(pdir, ignore_errors=True)
            raise _err(e)
    return _save(proj)


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    return _load(pid)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    shutil.rmtree(_pdir(pid))
    return {"ok": True}


@app.get("/api/projects/{pid}/files/{name:path}")
def project_file(pid: str, name: str):
    base = _pdir(pid).resolve()
    path = (base / name).resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(404, "ไม่พบไฟล์")
    return FileResponse(path)


@app.post("/api/projects/{pid}/separate")
def separate(pid: str):
    proj, pdir = _load(pid), _pdir(pid)
    if not proj.get("audio"):
        raise HTTPException(400, "โปรเจกต์นี้ยังไม่มีวิดีโอ")
    try:
        stems = ai.separate(pdir / proj["audio"], pdir / "stems")
    except Exception as e:
        raise _err(e)
    proj["background"] = str(stems["background"].relative_to(pdir))
    proj["original_voice"] = str(stems["vocals"].relative_to(pdir))
    return _save(proj)


@app.post("/api/projects/{pid}/transcribe")
def transcribe(pid: str, language: str = "th"):
    proj, pdir = _load(pid), _pdir(pid)
    src = proj.get("original_voice") or proj.get("audio")
    if not src:
        raise HTTPException(400, "โปรเจกต์นี้ยังไม่มีวิดีโอ")
    try:
        mono = media.to_wav(pdir / src, pdir / "for_asr.wav", sr=16000)
        segs = ai.transcribe(mono, language)
    except Exception as e:
        raise _err(e)
    proj["lines"] = [_new_line(s["start"], s["end"], s["text"]) for s in segs]
    return _save(proj)


# ---------- lines ----------

class LineIn(BaseModel):
    start: float | None = None
    end: float | None = None
    text: str | None = None
    who: str | None = None
    settings: dict | None = None
    model: str | None = None


@app.post("/api/projects/{pid}/lines")
def add_line(pid: str, body: LineIn):
    proj = _load(pid)
    ln = _new_line(body.start or 0.0, body.end, body.text or "", body.who or "")
    proj["lines"].append(ln)
    proj["lines"].sort(key=lambda x: x["start"])
    _save(proj)
    return ln


@app.patch("/api/projects/{pid}/lines/{lid}")
def update_line(pid: str, lid: str, body: LineIn):
    proj = _load(pid)
    ln = _line(proj, lid)
    data = body.model_dump(exclude_unset=True)
    if "settings" in data:
        try:
            effects.Settings.from_dict({**ln["settings"], **data["settings"]})
        except (KeyError, TypeError) as e:
            raise HTTPException(400, f"ค่าตั้งเสียงไม่ถูกต้อง: {e}")
        data["settings"] = {**ln["settings"], **data["settings"]}
    if "model" in data and data["model"] and not (MODELS / _safe(data["model"])).is_dir():
        raise HTTPException(400, "ไม่พบโมเดลเสียงนี้")
    ln.update(data)
    proj["lines"].sort(key=lambda x: x["start"])
    _save(proj)
    return ln


@app.delete("/api/projects/{pid}/lines/{lid}")
def delete_line(pid: str, lid: str):
    proj = _load(pid)
    proj["lines"] = [l for l in proj["lines"] if l["id"] != lid]
    _save(proj)
    return {"ok": True}


@app.post("/api/projects/{pid}/lines/{lid}/take")
async def upload_take(pid: str, lid: str, audio: UploadFile = File(...)):
    proj, pdir = _load(pid), _pdir(pid)
    ln = _line(proj, lid)
    try:
        up = await _store_upload(audio, pdir / "takes", lid)
        media.to_wav(up, pdir / "takes" / f"{lid}_raw.wav")
        up.unlink(missing_ok=True)
    except Exception as e:
        raise _err(e)
    ln.update(raw=f"takes/{lid}_raw.wav", fx=None, kept=False, source="voice")
    _save(proj)
    return await run_in_threadpool(render, pid, lid)


class TtsIn(BaseModel):
    text: str


@app.post("/api/projects/{pid}/lines/{lid}/tts")
def tts_take(pid: str, lid: str, body: TtsIn):
    proj, pdir = _load(pid), _pdir(pid)
    ln = _line(proj, lid)
    if not body.text.strip():
        raise HTTPException(400, "กรุณาพิมพ์บทก่อน")
    try:
        tmp = ai.tts(body.text.strip(), pdir / "takes" / f"{lid}_tts.wav")
        media.to_wav(tmp, pdir / "takes" / f"{lid}_raw.wav")
    except Exception as e:
        raise _err(e)
    ln.update(text=body.text.strip(), raw=f"takes/{lid}_raw.wav", fx=None, kept=False, source="tts")
    _save(proj)
    return render(pid, lid)


@app.post("/api/projects/{pid}/lines/{lid}/render")
def render(pid: str, lid: str):
    proj, pdir = _load(pid), _pdir(pid)
    ln = _line(proj, lid)
    if not ln.get("raw"):
        raise HTTPException(400, "บรรทัดนี้ยังไม่มีเสียง อัดหรือพิมพ์บทก่อน")
    try:
        settings = effects.Settings.from_dict(ln["settings"])
        src = pdir / ln["raw"]
        if ln.get("model"):
            # The voice model sets the timbre; the character's pitch is passed to it
            # and not applied a second time by the effects chain.
            char_pitch = next(c.pitch for c in effects.CHARACTERS if c.id == settings.character)
            pitch = char_pitch if settings.pitch is None else settings.pitch
            src = ai.convert_voice(src, pdir / "takes" / f"{lid}_vc.wav", MODELS / _safe(ln["model"]), int(round(pitch)))
            settings.pitch = 0
        audio, sr = media.read(src)
        out = effects.apply(audio, sr, settings)
        name = f"takes/{lid}_fx_{int(time.time() * 1000)}.wav"
        for old in (pdir / "takes").glob(f"{lid}_fx_*.wav"):
            old.unlink()
        media.write(pdir / name, out, sr)
    except HTTPException:
        raise
    except Exception as e:
        raise _err(e)
    ln["fx"] = name
    _save(proj)
    return ln


@app.post("/api/projects/{pid}/lines/{lid}/keep")
def keep_take(pid: str, lid: str):
    """Save the raw take (your real voice) as training data for the next model version."""
    proj, pdir = _load(pid), _pdir(pid)
    ln = _line(proj, lid)
    if not ln.get("raw") or ln.get("source") == "tts":
        raise HTTPException(400, "เก็บได้เฉพาะเสียงที่คุณอัดเอง")
    name = f"{proj['id']}_{lid}.wav"
    shutil.copy(pdir / ln["raw"], DATASET / name)
    audio, sr = media.read(DATASET / name)
    with _lock, (DATASET / "takes.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"file": name, "text": ln["text"], "seconds": audio.shape[-1] / sr,
                            "mood": ln["settings"]["mood"], "at": time.time()}, ensure_ascii=False) + "\n")
    ln["kept"] = True
    _save(proj)
    return {"line": ln, "dataset": _dataset_info()}


@app.post("/api/projects/{pid}/export")
def export(pid: str):
    proj, pdir = _load(pid), _pdir(pid)
    clips = []
    for ln in proj["lines"]:
        if ln.get("fx"):
            audio, sr = media.read(pdir / ln["fx"])
            if sr != media.SR:
                raise HTTPException(500, "sample rate ไม่ตรงกัน")
            clips.append((float(ln["start"]), audio))
    if not clips:
        raise HTTPException(400, "ยังไม่มีบรรทัดที่พากเสียงแล้ว")
    try:
        bg = None
        if proj.get("background"):
            bg_wav = media.to_wav(pdir / proj["background"], pdir / "bg_44k.wav", mono=False)
            bg, _ = media.read(bg_wav)
        mix = media.mix_lines(bg, proj.get("duration") or 0, clips)
        media.write(pdir / "dub_mix.wav", mix, media.SR)
        if proj.get("video"):
            media.mux(pdir / proj["video"], pdir / "dub_mix.wav", pdir / "export.mp4")
            proj["export"] = "export.mp4"
        else:
            proj["export"] = "dub_mix.wav"
    except HTTPException:
        raise
    except Exception as e:
        raise _err(e)
    proj["exported_at"] = time.time()
    return _save(proj)


# ---------- voice models & training data ----------

@app.post("/api/models")
async def upload_model(name: str = Form(...), pth: UploadFile = File(...), index: UploadFile | None = File(None)):
    if not (pth.filename or "").endswith(".pth"):
        raise HTTPException(400, "ไฟล์โมเดลต้องเป็น .pth")
    d = MODELS / _safe(name)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "model.pth").open("wb") as f:
        shutil.copyfileobj(pth.file, f)
    if index is not None and index.filename:
        with (d / "model.index").open("wb") as f:
            shutil.copyfileobj(index.file, f)
    return {"models": _models()}


@app.get("/api/dataset.zip")
def dataset_zip():
    """All kept takes, ready to upload to the Colab/Kaggle training notebook."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in DATASET.iterdir():
            z.write(f, f.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=my-voice-dataset.zip"})


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
