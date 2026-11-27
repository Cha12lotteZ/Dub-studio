"""The functions other projects call. Shared by the Python API, the CLI and /api/v1.

    import dubstudio
    dubstudio.process("line.wav", "giant.wav", character="giant", mood="angry", atmosphere="cave")
    audio, sr = dubstudio.speak("หยุดอยู่ตรงนั้น!", character="giant")
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Union

import numpy as np

from . import ai, effects, media

AudioIn = Union[str, os.PathLike, tuple]  # a file path, or (array, sample_rate)


def data_dir() -> Path:
    return Path(os.environ.get("DUB_DATA") or Path.home() / "DubStudio")


def presets() -> dict:
    """Character, mood and atmosphere ids with their Thai names."""
    return effects.catalog()


def models() -> list[str]:
    d = data_dir() / "models"
    return sorted(p.name for p in d.iterdir() if p.is_dir() and any(p.glob("*.pth"))) if d.is_dir() else []


def _model_dir(model: str | os.PathLike) -> Path:
    p = Path(model)
    if p.is_dir():
        return p
    p = data_dir() / "models" / str(model)
    if p.is_dir():
        return p
    raise FileNotFoundError(f"ไม่พบโมเดลเสียง: {model}")


def _load(src: AudioIn, workdir: Path) -> tuple[np.ndarray, int, Path]:
    """Return (channels x samples float32, sr, wav path) for a path or (array, sr)."""
    if isinstance(src, tuple):
        audio, sr = src
        audio = np.atleast_2d(np.asarray(audio, dtype=np.float32))
        if audio.shape[0] > audio.shape[1]:  # (samples, channels) -> (channels, samples)
            audio = audio.T
        wav = media.write(workdir / "in.wav", audio, int(sr))
        return audio, int(sr), wav
    wav = media.to_wav(Path(src), workdir / "in.wav")
    audio, sr = media.read(wav)
    return audio, sr, wav


def process(src: AudioIn, out: str | os.PathLike | None = None, *, character: str = "me", mood: str = "normal",
            atmosphere: str = "none", mix: float = 0.6, pitch: float | None = None,
            model: str | os.PathLike | None = None) -> tuple[np.ndarray, int]:
    """Turn a recording into a character line.

    src: any audio/video file ffmpeg can read, or (numpy_array, sample_rate).
    model: a voice model name (from the app's models folder) or a folder holding a .pth.
    Returns (audio as channels x samples float32, sample_rate); also writes WAV to `out` if given.
    """
    settings = effects.Settings.from_dict(
        {"character": character, "mood": mood, "atmosphere": atmosphere, "mix": mix, "pitch": pitch})
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        audio, sr, wav = _load(src, tmp)
        if model:
            char_pitch = next(c.pitch for c in effects.CHARACTERS if c.id == settings.character)
            shift = char_pitch if settings.pitch is None else settings.pitch
            converted = ai.convert_voice(wav, tmp / "vc.wav", _model_dir(model), int(round(shift)))
            audio, sr = media.read(converted)
            settings.pitch = 0
        result = effects.apply(audio, sr, settings)
    if out is not None:
        media.write(Path(out), result, sr)
    return result, sr


def speak(text: str, out: str | os.PathLike | None = None, **settings) -> tuple[np.ndarray, int]:
    """Thai text to speech, then the same character/mood/atmosphere/model as process()."""
    if not text.strip():
        raise ValueError("ข้อความว่าง")
    with tempfile.TemporaryDirectory() as tmp:
        wav = ai.tts(text.strip(), Path(tmp) / "tts.wav")
        return process(wav, out, **settings)


def transcribe(src: str | os.PathLike, language: str = "th") -> list[dict]:
    """Timed lines [{start, end, text}] from an audio or video file."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = media.to_wav(Path(src), Path(tmp) / "asr.wav", sr=16000)
        return ai.transcribe(wav, language)
