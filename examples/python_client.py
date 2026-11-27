"""Call a running Dub Studio (dubstudio serve) over HTTP from any Python project.
Only needs `requests`. For in-process use without a server: `import dubstudio`.
"""
import requests

BASE = "http://localhost:8000"

# 1) Your own recording -> a giant shouting in a cave
with open("my_line.wav", "rb") as f:
    r = requests.post(f"{BASE}/api/v1/process", files={"audio": f},
                      data={"character": "giant", "mood": "angry", "atmosphere": "cave"})
r.raise_for_status()
open("giant_line.wav", "wb").write(r.content)

# 2) Typed Thai line -> robot on the radio (needs the AI part installed)
r = requests.post(f"{BASE}/api/v1/speak",
                  json={"text": "เปิดใช้งานโหมดต่อสู้", "character": "robot", "atmosphere": "radio"})
r.raise_for_status()
open("robot_line.wav", "wb").write(r.content)

print(requests.get(f"{BASE}/api/v1/presets").json()["characters"])
