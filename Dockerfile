# Dub Studio for Hugging Face Spaces (free CPU: 2 vCPU, 16 GB RAM).
# Also runs anywhere Docker does: docker build -t dub-studio . && docker run -p 7860:7860 dub-studio
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Spaces runs the container as user 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface TORCH_HOME=/home/user/.cache/torch \
    DUB_DATA=/home/user/data PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# CPU-only torch keeps the image several GB smaller than the default CUDA build.
RUN pip install --no-cache-dir --user torch torchaudio --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user . .
RUN pip install --no-cache-dir --user ".[ai]"

# Download the Thai transcription, Thai TTS and voice-separation models at build
# time, so the first click in the app does not wait for a 1 GB download.
RUN python scripts/preload_models.py

EXPOSE 7860
CMD ["dubstudio", "serve", "--host", "0.0.0.0", "--port", "7860", "--no-browser"]
