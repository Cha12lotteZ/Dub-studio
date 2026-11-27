import importlib
import io
import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app import effects, media

SR = 44100


def tone(seconds=1.0, freq=220.0, sr=SR):
    t = np.arange(int(seconds * sr)) / sr
    # A voice-ish signal: harmonics with a slow amplitude wobble.
    sig = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 6)) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t))
    return (0.3 * sig).astype(np.float32)[None, :]


@pytest.mark.parametrize("char", [c.id for c in effects.CHARACTERS])
@pytest.mark.parametrize("mood", [m.id for m in effects.MOODS])
def test_character_and_mood_presets_render(char, mood):
    out = effects.apply(tone(0.5), SR, effects.Settings(character=char, mood=mood))
    assert out.shape[-1] >= SR * 0.5 - 1
    assert np.isfinite(out).all() and 0 < np.abs(out).max() <= 0.91


@pytest.mark.parametrize("amb", [a.id for a in effects.ATMOSPHERES])
def test_atmospheres_render(amb):
    out = effects.apply(tone(0.5), SR, effects.Settings(atmosphere=amb, mix=0.8))
    assert np.isfinite(out).all() and np.abs(out).max() > 0
    if amb in ("cave", "hall", "room", "dream"):
        assert out.shape[-1] > SR * 0.5  # reverb tail is kept


def test_pitch_shift_keeps_duration_and_changes_pitch():
    src = tone(1.0, 220)
    out = effects.apply(src, SR, effects.Settings(character="kid"))  # +5 semitones
    assert out.shape[-1] == src.shape[-1]
    peak = lambda a: np.argmax(np.abs(np.fft.rfft(a[0]))) * SR / a.shape[-1]
    assert peak(out) == pytest.approx(220 * 2 ** (5 / 12), rel=0.05)


def test_invalid_settings_rejected():
    with pytest.raises(KeyError):
        effects.Settings.from_dict({"mood": "nope"})


def test_mix_lines_places_clips_and_ducks_background():
    bg = np.full((2, SR * 2), 0.2, np.float32)
    clip = tone(0.5) * 0.3
    out = media.mix_lines(bg, 2.0, [(1.0, clip)])
    assert out.shape == (2, SR * 2)
    assert np.abs(out[:, : int(0.5 * SR)]).mean() == pytest.approx(0.2, rel=0.05)  # untouched before speech
    a, b = int(1.2 * SR), int(1.3 * SR)
    background_under_speech = out[0, a:b] - clip[0, a - SR: b - SR]
    assert background_under_speech.mean() == pytest.approx(0.2 * 0.35, rel=0.1)  # ducked


needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DUB_DATA", str(tmp_path))
    import app.main as main
    importlib.reload(main)
    return TestClient(main.app)


def wav_bytes(seconds=1.0):
    buf = io.BytesIO()
    sf.write(buf, tone(seconds)[0], SR, format="WAV")
    return buf.getvalue()


@needs_ffmpeg
def test_full_flow_without_video(client):
    cat = client.get("/api/catalog").json()
    assert {"characters", "moods", "atmospheres", "ai", "models"} <= cat.keys()

    p = client.post("/api/projects", data={"name": "ทดสอบ"}).json()
    ln = client.post(f"/api/projects/{p['id']}/lines", json={"start": 0.5, "text": "สวัสดี"}).json()

    r = client.post(f"/api/projects/{p['id']}/lines/{ln['id']}/render")
    assert r.status_code == 400  # no take yet

    r = client.post(f"/api/projects/{p['id']}/lines/{ln['id']}/take", files={"audio": ("take.wav", wav_bytes(), "audio/wav")})
    assert r.status_code == 200, r.text
    assert r.json()["fx"]

    r = client.patch(f"/api/projects/{p['id']}/lines/{ln['id']}", json={"settings": {"character": "giant", "atmosphere": "cave"}})
    assert r.json()["settings"]["character"] == "giant"
    r = client.patch(f"/api/projects/{p['id']}/lines/{ln['id']}", json={"settings": {"mood": "bogus"}})
    assert r.status_code == 400
    fx = client.post(f"/api/projects/{p['id']}/lines/{ln['id']}/render").json()["fx"]
    assert client.get(f"/api/projects/{p['id']}/files/{fx}").status_code == 200

    kept = client.post(f"/api/projects/{p['id']}/lines/{ln['id']}/keep").json()
    assert kept["dataset"]["takes"] == 1
    assert client.get("/api/dataset.zip").status_code == 200

    out = client.post(f"/api/projects/{p['id']}/export").json()
    assert out["export"] == "dub_mix.wav"


@needs_ffmpeg
def test_export_with_video(client, tmp_path):
    vid = tmp_path / "in.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=160x90:d=2",
                    "-f", "lavfi", "-i", "sine=f=440:d=2", "-shortest", "-c:v", "libx264", "-c:a", "aac", str(vid)], check=True)
    p = client.post("/api/projects", data={"name": "วิดีโอ"}, files={"video": ("in.mp4", vid.read_bytes(), "video/mp4")}).json()
    assert p["video"] == "video.mp4" and p["duration"] == pytest.approx(2, abs=0.2)
    ln = client.post(f"/api/projects/{p['id']}/lines", json={"start": 0.5}).json()
    client.post(f"/api/projects/{p['id']}/lines/{ln['id']}/take", files={"audio": ("t.wav", wav_bytes(0.8), "audio/wav")})
    out = client.post(f"/api/projects/{p['id']}/export")
    assert out.status_code == 200, out.text
    assert client.get(f"/api/projects/{p['id']}/files/export.mp4").status_code == 200


def test_file_route_blocks_path_traversal(client):
    p = client.post("/api/projects", data={"name": "x"}).json()
    assert client.get(f"/api/projects/{p['id']}/files/../../projects").status_code == 404


FAKE_APPLIO = '''
import shutil, sys
a = sys.argv
assert a[1] == "infer"
opt = {a[i]: a[i + 1] for i in range(2, len(a) - 1, 2)}
assert opt["--f0-method"] == "rmvpe" and opt["--pth-path"].endswith(".pth")
open(opt["--output-path"] + ".args", "w").write(" ".join(a[1:]))
shutil.copy(opt["--input-path"], opt["--output-path"])
'''


@needs_ffmpeg
def test_voice_model_runs_through_applio(client, tmp_path, monkeypatch):
    applio = tmp_path / "Applio"
    applio.mkdir()
    (applio / "core.py").write_text(FAKE_APPLIO)
    monkeypatch.setenv("DUB_APPLIO_DIR", str(applio))
    assert client.get("/api/catalog").json()["ai"]["voice_model"] is True

    r = client.post("/api/models", data={"name": "เสียงฉัน-v1"}, files={"pth": ("m.pth", b"x"), "index": ("m.index", b"y")})
    model_id = r.json()["models"][0]["id"]
    p = client.post("/api/projects", data={"name": "vc"}).json()
    ln = client.post(f"/api/projects/{p['id']}/lines", json={"start": 0}).json()
    client.patch(f"/api/projects/{p['id']}/lines/{ln['id']}", json={"model": model_id, "settings": {"character": "kid"}})
    r = client.post(f"/api/projects/{p['id']}/lines/{ln['id']}/take", files={"audio": ("t.wav", wav_bytes(), "audio/wav")})
    assert r.status_code == 200, r.text
    args = next((tmp_path / "projects" / p["id"] / "takes").glob("*_vc.wav.args")).read_text()
    assert "--pitch 5" in args and "model.index" in args  # kid pitch goes to the model, not applied twice


def test_voice_model_missing_applio_is_reported(client, monkeypatch):
    monkeypatch.delenv("DUB_APPLIO_DIR", raising=False)
    assert client.get("/api/catalog").json()["ai"]["voice_model"] is False


def test_password_gate(client, monkeypatch):
    monkeypatch.setenv("DUB_PASSWORD", "ลับมาก")
    assert client.get("/api/catalog").status_code == 401
    assert client.get("/api/catalog", auth=("ใครก็ได้", "ผิด")).status_code == 401
    assert client.get("/api/catalog", auth=("me", "ลับมาก")).status_code == 200
    monkeypatch.delenv("DUB_PASSWORD")
    assert client.get("/api/catalog").status_code == 200
