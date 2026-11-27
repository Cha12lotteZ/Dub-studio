"""Character, mood and atmosphere presets applied with Spotify's pedalboard.

Every preset works on CPU in real time, so no GPU is needed for this step.
Audio arrays are float32 shaped (channels, samples).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from pedalboard import (
    Chorus,
    Compressor,
    Delay,
    Distortion,
    Gain,
    HighpassFilter,
    LowpassFilter,
    LowShelfFilter,
    PeakFilter,
    Pedalboard,
    PitchShift,
    Reverb,
)


@dataclass(frozen=True)
class Preset:
    id: str
    name: str  # Thai label shown in the UI
    pitch: float = 0.0  # semitones, only used by characters
    extra: str | None = None  # special processing that pedalboard has no plugin for


CHARACTERS = [
    Preset("me", "เสียงฉัน", 0),
    Preset("kid", "เด็ก", 5),
    Preset("woman", "ผู้หญิง", 4),
    Preset("man", "ผู้ชายเสียงทุ้ม", -3),
    Preset("giant", "ยักษ์", -7),
    Preset("robot", "หุ่นยนต์", 0, "robot"),
    Preset("ghost", "ผี", 3, "ghost"),
]

MOODS = [
    Preset("normal", "ปกติ"),
    Preset("angry", "โกรธ"),
    Preset("sad", "เศร้า"),
    Preset("whisper", "กระซิบ"),
    Preset("shout", "ตะโกน"),
    Preset("happy", "ร่าเริง"),
]

ATMOSPHERES = [
    Preset("none", "ไม่มี"),
    Preset("room", "ในห้อง"),
    Preset("hall", "ห้องโถง"),
    Preset("cave", "ในถ้ำ"),
    Preset("radio", "วิทยุ"),
    Preset("phone", "โทรศัพท์"),
    Preset("monster", "สัตว์ประหลาด"),
    Preset("dream", "ความฝัน"),
]


def _by_id(items: list[Preset], pid: str) -> Preset:
    for p in items:
        if p.id == pid:
            return p
    raise KeyError(f"unknown preset: {pid}")


def catalog() -> dict:
    as_list = lambda items: [{"id": p.id, "name": p.name, "pitch": p.pitch} for p in items]
    return {"characters": as_list(CHARACTERS), "moods": as_list(MOODS), "atmospheres": as_list(ATMOSPHERES)}


@dataclass
class Settings:
    character: str = "me"
    mood: str = "normal"
    atmosphere: str = "none"
    pitch: float | None = None  # overrides the character's default pitch
    mix: float = 0.6  # atmosphere strength 0..1
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        s = cls(**{k: d[k] for k in ("character", "mood", "atmosphere", "pitch", "mix") if k in d and d[k] is not None})
        _by_id(CHARACTERS, s.character)
        _by_id(MOODS, s.mood)
        _by_id(ATMOSPHERES, s.atmosphere)
        s.mix = float(min(1.0, max(0.0, s.mix)))
        return s


def _mood_board(mood: str) -> Pedalboard:
    return Pedalboard({
        "normal": [],
        "angry": [PeakFilter(2500, 6, 1.0), Distortion(6), Compressor(-20, 4)],
        "sad": [LowpassFilter(2800), PitchShift(-0.7)],
        "whisper": [HighpassFilter(1400), Compressor(-30, 6), Gain(6)],
        "shout": [Compressor(-30, 8), Distortion(4), PeakFilter(3000, 4, 0.8)],
        "happy": [PitchShift(1.0), PeakFilter(4000, 3, 0.8)],
    }[mood])


def _ring_mod(audio: np.ndarray, sr: int, freq: float = 55.0) -> np.ndarray:
    t = np.arange(audio.shape[-1], dtype=np.float32) / sr
    return (audio * np.sin(2 * np.pi * freq * t)).astype(np.float32) * 1.6


def _atmosphere(audio: np.ndarray, sr: int, atmosphere: str, mix: float) -> np.ndarray:
    if atmosphere == "none" or mix <= 0:
        return audio
    # Reverbs are mixed by pedalboard itself and need a tail.
    reverbs = {
        "room": Reverb(room_size=0.3, damping=0.6, wet_level=mix * 0.5, dry_level=1 - mix * 0.3),
        "hall": Reverb(room_size=0.75, damping=0.4, wet_level=mix * 0.6, dry_level=1 - mix * 0.4),
        "cave": Reverb(room_size=0.95, damping=0.25, wet_level=mix * 0.8, dry_level=1 - mix * 0.5),
        "dream": None,
    }
    if atmosphere in reverbs:
        tail = np.zeros((audio.shape[0], int(sr * (3.0 if atmosphere in ("cave", "dream") else 1.5))), np.float32)
        padded = np.concatenate([audio, tail], axis=1)
        if atmosphere == "dream":
            board = Pedalboard([Chorus(rate_hz=0.6, depth=0.4, mix=mix), Reverb(room_size=0.9, wet_level=mix * 0.7), LowpassFilter(5000)])
        else:
            board = Pedalboard([reverbs[atmosphere]])
        return board(padded, sr)
    wet_board = {
        "radio": Pedalboard([HighpassFilter(500), LowpassFilter(3000), Distortion(18), Gain(-8)]),
        "phone": Pedalboard([HighpassFilter(400), LowpassFilter(3200), Distortion(6), Gain(-3)]),
        "monster": Pedalboard([PitchShift(-5), LowShelfFilter(200, 10), Distortion(12), LowpassFilter(2500), Gain(-6)]),
    }[atmosphere]
    wet = wet_board(audio, sr)
    return audio * (1 - mix) + wet * mix


def normalize(audio: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = float(np.max(np.abs(audio))) if audio.size else 0.0
    return audio if m < 1e-6 else (audio * (peak / m)).astype(np.float32)


def apply(audio: np.ndarray, sr: int, settings: Settings) -> np.ndarray:
    """Run character -> mood -> atmosphere on a (channels, samples) float32 array."""
    audio = np.atleast_2d(audio).astype(np.float32)
    char = _by_id(CHARACTERS, settings.character)
    pitch = char.pitch if settings.pitch is None else float(settings.pitch)
    if pitch:
        audio = Pedalboard([PitchShift(pitch)])(audio, sr)  # keeps duration unchanged
    audio = _mood_board(settings.mood)(audio, sr)
    if char.extra == "robot":
        audio = _ring_mod(audio, sr)
    elif char.extra == "ghost":
        audio = Pedalboard([Delay(0.18, 0.45, 0.4), Reverb(room_size=0.8, wet_level=0.4)])(audio, sr)
    audio = _atmosphere(audio, sr, settings.atmosphere, settings.mix)
    return normalize(audio)
