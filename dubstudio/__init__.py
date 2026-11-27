"""Dub Studio: dub videos and games with your own voice.

    import dubstudio
    dubstudio.process("take.wav", "out.wav", character="giant", mood="angry", atmosphere="cave")
    dubstudio.speak("หยุดอยู่ตรงนั้น!", "line.wav", character="robot")
    dubstudio.presets()
"""
from .core import models, presets, process, speak, transcribe

__all__ = ["models", "presets", "process", "speak", "transcribe"]
__version__ = "0.2.0"
