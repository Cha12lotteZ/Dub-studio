"""Download the AI models once (used by the Dockerfile and the Colab notebook)."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

whisper_size = os.environ.get("DUB_WHISPER_MODEL", "small")
tts_model = os.environ.get("DUB_TTS_MODEL", "facebook/mms-tts-tha")

print(f"[1/3] Whisper {whisper_size}")
from faster_whisper import WhisperModel  # noqa: E402

WhisperModel(whisper_size, device="cpu", compute_type="int8")

print(f"[2/3] {tts_model}")
from transformers import VitsModel, VitsTokenizer  # noqa: E402

VitsTokenizer.from_pretrained(tts_model)
VitsModel.from_pretrained(tts_model)

print("[3/3] Demucs htdemucs")
with tempfile.TemporaryDirectory() as d:
    wav = Path(d) / "silence.wav"
    sf.write(wav, np.zeros((44100, 2), np.float32), 44100)
    subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-d", "cpu",
                    "-o", d, str(wav)], check=True, capture_output=True)
print("done")
