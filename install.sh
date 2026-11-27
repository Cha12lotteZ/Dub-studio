#!/usr/bin/env bash
# ติดตั้งสตูดิโอพากเสียง (Mac/Linux) ไม่ต้องมี Python หรือ ffmpeg ในเครื่องก่อน
# ไม่ถาม: DUB_INSTALL_AI=1 ./install.sh  (หรือ 0 เพื่อข้ามส่วน AI)
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "กำลังติดตั้ง uv (ตัวจัดการ Python)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "กำลังเตรียม Python 3.11 และแพ็กเกจหลัก..."
uv venv --python 3.11 --allow-existing .venv
uv pip install --python .venv/bin/python -e .

ai="${DUB_INSTALL_AI:-}"
if [ -z "$ai" ]; then
  read -r -p "ติดตั้งส่วน AI ด้วยไหม (ถอดบท แยกเสียง พิมพ์บทให้พูด ใช้พื้นที่ประมาณ 2-3 GB) [y/N] " ans
  case "$ans" in [yY]*) ai=1 ;; *) ai=0 ;; esac
fi
if [ "$ai" = "1" ]; then
  if [ "$(uname -s)" = "Linux" ]; then
    # Linux PyPI torch includes CUDA (~4 GB); the CPU build is much smaller.
    uv pip install --python .venv/bin/python torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  fi
  uv pip install --python .venv/bin/python -e ".[ai]"
fi

echo
echo "เสร็จแล้ว เปิดแอปด้วย ./start.sh (Mac ดับเบิลคลิก start.command ได้)"
