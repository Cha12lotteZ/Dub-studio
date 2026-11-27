"""Command line: `dubstudio serve`, `dubstudio fx`, `dubstudio speak`, `dubstudio presets`."""
from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from pathlib import Path


def _voice_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--character", "-c", default="me", help="เช่น me, kid, woman, man, giant, robot, ghost")
    p.add_argument("--mood", "-m", default="normal", help="เช่น normal, angry, sad, whisper, shout, happy")
    p.add_argument("--atmosphere", "-a", default="none", help="เช่น none, room, hall, cave, radio, phone, monster, dream")
    p.add_argument("--mix", type=float, default=0.6, help="ความแรงของบรรยากาศ 0–1")
    p.add_argument("--pitch", type=float, default=None, help="ระดับเสียง (semitone) แทนค่าของตัวละคร")
    p.add_argument("--model", default=None, help="ชื่อโมเดลเสียง หรือโฟลเดอร์ที่มีไฟล์ .pth")


def _settings(a: argparse.Namespace) -> dict:
    return {k: getattr(a, k) for k in ("character", "mood", "atmosphere", "mix", "pitch", "model")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dubstudio", description="สตูดิโอพากเสียง")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="เปิดเว็บแอปและ HTTP API")
    s.add_argument("--host", default="127.0.0.1", help="ใช้ 0.0.0.0 ถ้าต้องการให้เครื่องอื่นในบ้านเข้าได้")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--no-browser", action="store_true", help="ไม่ต้องเปิดเบราว์เซอร์ให้")

    f = sub.add_parser("fx", help="ใส่ตัวละคร อารมณ์ บรรยากาศ ให้ไฟล์เสียง (ทีละหลายไฟล์ได้)")
    f.add_argument("inputs", nargs="+", type=Path)
    f.add_argument("--out", "-o", type=Path, required=True,
                   help="ไฟล์ผลลัพธ์ .wav หรือโฟลเดอร์ (เมื่อใส่หลายไฟล์)")
    _voice_args(f)

    t = sub.add_parser("speak", help="พิมพ์บทให้พูด (ต้องติดตั้งส่วน AI)")
    t.add_argument("text")
    t.add_argument("--out", "-o", type=Path, required=True)
    _voice_args(t)

    sub.add_parser("presets", help="แสดงตัวละคร อารมณ์ บรรยากาศ ที่ใช้ได้")

    a = ap.parse_args(argv)

    if a.cmd == "serve":
        import uvicorn

        url = f"http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{a.port}"
        print(f"สตูดิโอพากเสียงเปิดอยู่ที่ {url}  (API docs: {url}/docs)  กด Ctrl+C เพื่อปิด")
        if not a.no_browser:
            threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        uvicorn.run("dubstudio.main:app", host=a.host, port=a.port, log_level="warning")
        return 0

    from . import core

    if a.cmd == "presets":
        print(json.dumps(core.presets(), ensure_ascii=False, indent=2))
        return 0

    try:
        if a.cmd == "fx":
            many = len(a.inputs) > 1 or a.out.suffix.lower() != ".wav"
            if many:
                a.out.mkdir(parents=True, exist_ok=True)
            for src in a.inputs:
                dst = a.out / f"{src.stem}_{a.character}.wav" if many else a.out
                core.process(src, dst, **_settings(a))
                print(f"✓ {src} → {dst}")
        elif a.cmd == "speak":
            core.speak(a.text, a.out, **_settings(a))
            print(f"✓ {a.out}")
    except Exception as e:  # show a readable message, not a traceback
        print(f"ผิดพลาด: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
