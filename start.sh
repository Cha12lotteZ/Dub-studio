#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -x .venv/bin/dubstudio ]; then echo "ยังไม่ได้ติดตั้ง รัน ./install.sh ก่อน"; exit 1; fi
exec .venv/bin/dubstudio serve "$@"
