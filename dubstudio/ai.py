"""Optional AI steps. Each one imports its library lazily, so the app still runs
(with effects, recording and export) before the [ai] extra is installed.

All of them run on CPU. Training happens on Colab/Kaggle (see notebooks/).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path


class NotInstalled(RuntimeError):
    pass


def _need(module: str, pip_name: str):
    try:
        return __import__(module)
    except ImportError as e:
        raise NotInstalled(f"ยังไม่ได้ติดตั้ง {pip_name} (pip install dubstudio[ai] หรือรัน install อีกครั้งแล้วเลือกติดตั้งส่วน AI)") from e


def status() -> dict:
    def has(m: str) -> bool:
        try:
            __import__(m)
            return True
        except ImportError:
            return False
    return {
        "transcribe": has("faster_whisper"),
        "separate": has("demucs"),
        "tts": has("transformers") and has("torch"),
        "voice_model": voice_model_ready(),
    }


# ---------- Transcribe (Whisper) ----------

@lru_cache(maxsize=1)
def _whisper():
    fw = _need("faster_whisper", "faster-whisper")
    size = os.environ.get("DUB_WHISPER_MODEL", "small")
    return fw.WhisperModel(size, device="cpu", compute_type="int8")


def transcribe(wav: Path, language: str = "th") -> list[dict]:
    """wav must be 16 kHz mono (media.to_wav(..., sr=16000)). We decode it ourselves
    so faster-whisper does not depend on the installed PyAV version."""
    import soundfile as sf

    audio, sr = sf.read(str(wav), dtype="float32")
    if sr != 16000:
        raise ValueError("transcribe() ต้องการไฟล์ 16 kHz")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    segments, _ = _whisper().transcribe(audio, language=language, vad_filter=True)
    return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]


# ---------- Separate speech from music/effects (Demucs) ----------

def separate(audio: Path, out_dir: Path) -> dict[str, Path]:
    _need("demucs", "demucs")
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-d", "cpu", "-o", str(out_dir), str(audio)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-800:])
    stem_dir = out_dir / "htdemucs" / audio.stem
    return {"vocals": stem_dir / "vocals.wav", "background": stem_dir / "no_vocals.wav"}


# ---------- Text to speech (Thai) ----------

@lru_cache(maxsize=1)
def _mms():
    _need("torch", "torch")
    tr = _need("transformers", "transformers")
    name = os.environ.get("DUB_TTS_MODEL", "facebook/mms-tts-tha")
    return tr.VitsTokenizer.from_pretrained(name), tr.VitsModel.from_pretrained(name)


def tts(text: str, out: Path) -> Path:
    """Thai speech from text. The base voice is generic; pass it through a voice
    model (convert_voice) to make it sound like you or a character.
    MMS-TTS is licensed CC-BY-NC 4.0, so it is for non-commercial use."""
    import numpy as np
    import soundfile as sf
    import torch

    tok, model = _mms()
    inputs = tok(text, return_tensors="pt")
    with torch.no_grad():
        wav = model(**inputs).waveform[0].numpy().astype(np.float32)
    sf.write(str(out), wav, model.config.sampling_rate)
    return out


# ---------- Voice conversion (RVC model trained on Colab/Kaggle) ----------
# Runs through Applio (https://github.com/IAHispano/Applio), installed separately in
# its own Python environment, because RVC's dependencies clash with this app's.
# Set DUB_APPLIO_DIR to the Applio folder; DUB_APPLIO_PYTHON overrides its Python.

def _applio() -> tuple[str, Path]:
    d = os.environ.get("DUB_APPLIO_DIR")
    if not d or not (Path(d) / "core.py").exists():
        raise NotInstalled("ยังไม่ได้ตั้งค่า Applio สำหรับแปลงเสียง (ดูหัวข้อ \"แปลงเสียงด้วยโมเดล\" ใน README)")
    root = Path(d)
    py = os.environ.get("DUB_APPLIO_PYTHON")
    if not py:
        for cand in (root / ".venv" / "bin" / "python", root / ".venv" / "Scripts" / "python.exe", root / "env" / "python.exe"):
            if cand.exists():
                py = str(cand)
                break
    return py or sys.executable, root


def convert_voice(src: Path, out: Path, model_dir: Path, pitch: int = 0) -> Path:
    pth = next(model_dir.glob("*.pth"), None)
    if pth is None:
        raise FileNotFoundError(f"ไม่พบไฟล์ .pth ใน {model_dir.name}")
    idx = next(model_dir.glob("*.index"), None)
    py, root = _applio()
    cmd = [py, "core.py", "infer", "--input-path", str(src.resolve()), "--output-path", str(out.resolve()),
           "--pth-path", str(pth.resolve()), "--index-path", str(idx.resolve()) if idx else "",
           "--pitch", str(int(max(-24, min(24, pitch)))), "--f0-method", "rmvpe", "--export-format", "WAV"]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError("แปลงเสียงไม่สำเร็จ: " + (proc.stderr or proc.stdout)[-600:])
    return out


def voice_model_ready() -> bool:
    try:
        _applio()
        return True
    except NotInstalled:
        return False


def ffmpeg_ok() -> bool:
    from .media import ffmpeg_exe

    return ffmpeg_exe() is not None
