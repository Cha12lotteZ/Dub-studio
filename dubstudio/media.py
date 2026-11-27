"""ffmpeg helpers: normalise any upload to WAV, and mix dubbed lines back onto a video."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100


class MediaError(RuntimeError):
    pass


def ffmpeg_exe() -> str | None:
    """System ffmpeg if installed, else the copy bundled by imageio-ffmpeg."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _ffmpeg(*args: str) -> None:
    exe = ffmpeg_exe()
    if not exe:
        raise MediaError("ไม่พบ ffmpeg กรุณาติดตั้งก่อน (ดู README)")
    proc = subprocess.run([exe, "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise MediaError(proc.stderr.strip() or "ffmpeg ทำงานไม่สำเร็จ")


def to_wav(src: Path, dst: Path, sr: int = SR, mono: bool = True) -> Path:
    """Convert any audio/video file (webm from the browser, mp3, m4a, mp4...) to WAV."""
    _ffmpeg("-i", str(src), "-vn", "-ac", "1" if mono else "2", "-ar", str(sr), "-c:a", "pcm_s16le", str(dst))
    return dst


def read(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data.T.copy(), sr  # (channels, samples)


def write(path: Path, audio: np.ndarray, sr: int) -> Path:
    sf.write(str(path), np.atleast_2d(audio).T, sr, subtype="PCM_16")
    return path


def mix_lines(background: np.ndarray | None, duration_s: float, clips: list[tuple[float, np.ndarray]],
              sr: int = SR, duck: float = 0.35) -> np.ndarray:
    """Place each (start_seconds, mono clip) on a stereo bed; lower the background under speech."""
    total = int(duration_s * sr)
    for start, clip in clips:
        total = max(total, int(start * sr) + clip.shape[-1])
    bed = np.zeros((2, total), np.float32)
    voice = np.zeros(total, np.float32)
    for start, clip in clips:
        mono = np.atleast_2d(clip).mean(axis=0)
        i = int(start * sr)
        voice[i:i + mono.size] += mono
    if background is not None:
        bg = np.atleast_2d(background)
        if bg.shape[0] == 1:
            bg = np.repeat(bg, 2, axis=0)
        n = min(total, bg.shape[1])
        # Smooth duck envelope: background drops while someone speaks.
        env = np.abs(voice) > 0.02
        kernel = np.ones(int(0.25 * sr), np.float32)
        env = np.clip(np.convolve(env.astype(np.float32), kernel, "same"), 0, 1)
        gain = 1.0 - (1.0 - duck) * env
        bed[:, :n] += bg[:, :n] * gain[:n]
    bed += voice
    peak = float(np.max(np.abs(bed))) or 1.0
    return bed / peak * 0.95 if peak > 0.95 else bed


def mux(video: Path, audio_wav: Path, out: Path) -> Path:
    _ffmpeg("-i", str(video), "-i", str(audio_wav), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out))
    return out


def duration(path: Path) -> float:
    """Media length in seconds, read from ffmpeg's own report (no ffprobe needed)."""
    import re

    exe = ffmpeg_exe()
    if not exe:
        raise MediaError("ไม่พบ ffmpeg")
    out = subprocess.run([exe, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", out)
    if not m:
        raise MediaError("อ่านความยาววิดีโอไม่ได้")
    h, mi, se = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(se)
