# สตูดิโอพากเสียง (Dub Studio)

เว็บแอปสำหรับพากเสียงวิดีโอ เกม หรือคลิปต่างๆ ด้วยเสียงของคุณเอง รันบนคอมของคุณ ใช้ฟรี และไม่ต้องมีการ์ดจอ

- **พูดเองแล้วแปลงเสียง:** อัดเสียงทีละบรรทัดตามวิดีโอ แล้วเปลี่ยนเป็นเสียงตัวละคร
- **พิมพ์บทให้พูด:** พิมพ์บทภาษาไทย ระบบสร้างเสียง แล้วแปลงเป็นเสียงตัวละครหรือเสียงคุณ
- **ตัวละคร:** เสียงฉัน เด็ก ผู้หญิง ผู้ชายเสียงทุ้ม ยักษ์ หุ่นยนต์ ผี
- **อารมณ์:** ปกติ โกรธ เศร้า กระซิบ ตะโกน ร่าเริง
- **บรรยากาศ:** ในห้อง ห้องโถง ในถ้ำ วิทยุ โทรศัพท์ สัตว์ประหลาด ความฝัน
- **วิดีโอ:** แยกเสียงพูดเดิมออก ถอดบทภาษาไทยอัตโนมัติ แล้วรวมเสียงพากเป็น MP4 (ลดเสียงพื้นหลังตอนมีคนพูดให้เอง)
- **เรียนรู้ไปเรื่อยๆ:** กด 👍 เก็บเทคที่ชอบ แล้วนำไปเทรนโมเดลเสียงรุ่นใหม่บน GPU ฟรีของ Colab หรือ Kaggle

## ใช้งานโดยไม่ต้องติดตั้ง

| ที่ไหน | เหมาะกับ | ข้อจำกัด |
|---|---|---|
| [Google Colab](https://colab.research.google.com/github/Cha12lotteZ/dub-studio/blob/main/notebooks/dub_studio_colab.ipynb) | ใช้ครบทุกอย่าง รวมแปลงเป็นเสียงคุณบน GPU ฟรี | เปิดโน้ตบุ๊กใหม่ทุกครั้ง ปิดเองเมื่อไม่ใช้งาน |
| Hugging Face Spaces | ลิงก์เว็บถาวร เปิดจากมือถือหรือคอมเครื่องไหนก็ได้ | CPU ฟรี จึงช้ากว่า ยังไม่มีการแปลงเสียงด้วยโมเดล งานหายเมื่อ Space รีสตาร์ท |

### ตั้งค่า Hugging Face Spaces (ครั้งเดียว)

1. สมัครบัญชีที่ [huggingface.co/join](https://huggingface.co/join)
2. สร้าง token แบบ **Write** ที่ [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
3. ใน GitHub repo นี้ ไปที่ **Settings → Secrets and variables → Actions**
   - แท็บ Secrets: เพิ่ม `HF_TOKEN` = token จากข้อ 2 และ `DUB_PASSWORD` = รหัสผ่านที่เว็บจะถาม (ชื่อผู้ใช้ใส่อะไรก็ได้)
   - (ไม่บังคับ) แท็บ Variables: `HF_SPACE` ถ้าต้องการชื่อ Space อื่น ค่าเริ่มต้นคือ `ชื่อผู้ใช้ของคุณ/dub-studio`
4. แท็บ **Actions → Deploy to Hugging Face Space → Run workflow** ครั้งแรกจะสร้าง Space แบบ Private ให้เอง หลังจากนั้นทุกครั้งที่มีโค้ดใหม่เข้า `main` จะส่งขึ้น Space ให้อัตโนมัติ (build ครั้งแรกประมาณ 15–20 นาที)

ถ้าเปลี่ยน Space เป็น Public โดยไม่ตั้ง `DUB_PASSWORD` ใครมีลิงก์ก็เห็นโปรเจกต์และเสียงที่เก็บไว้ทั้งหมด

## ติดตั้งบนคอมตัวเอง (ไม่ต้องมีการ์ดจอ)

1. ดาวน์โหลดโค้ด: ปุ่มเขียว **Code → Download ZIP** แล้วแตกไฟล์
2. ติดตั้งครั้งเดียว:
   - **Windows:** ดับเบิลคลิก `install.bat`
   - **Mac:** ดับเบิลคลิก `install.command` (ถ้าเปิดไม่ได้ ให้คลิกขวา → Open)
   - **Linux:** `./install.sh`
3. เปิดแอปทุกครั้ง: `start.bat` / `start.command` / `./start.sh` เบราว์เซอร์จะเปิด http://localhost:8000 ให้เอง

ตัวติดตั้งจะลง Python 3.11 และ ffmpeg ให้เอง (ผ่าน [uv](https://docs.astral.sh/uv/)) ไม่ต้องติดตั้งอะไรล่วงหน้า และจะถามว่าจะลงส่วน AI ด้วยไหม (ประมาณ 2–3 GB) ถ้าตอนแรกตอบไม่ ภายหลังรันตัวติดตั้งซ้ำแล้วตอบใช่ได้

โปรเจกต์ เทคเสียง และโมเดลเก็บไว้ที่โฟลเดอร์ `DubStudio` ในโฟลเดอร์ผู้ใช้ของคุณ อัปเดตโค้ดแล้วงานไม่หาย (เปลี่ยนที่เก็บได้ด้วยตัวแปร `DUB_DATA`)

| ส่วน AI | ใช้ทำอะไร | บน CPU |
|---|---|---|
| faster-whisper | ถอดบทจากวิดีโอ | วิดีโอ 1 นาที ใช้เวลาประมาณ 1 นาที |
| Demucs | แยกเสียงพูดออกจากดนตรีและเอฟเฟกต์ | ประมาณเท่าความยาววิดีโอ |
| MMS-TTS ภาษาไทย | พิมพ์บทให้พูด (ใช้ได้เฉพาะงานไม่เชิงพาณิชย์ ตามสัญญาอนุญาต CC-BY-NC 4.0) | ไม่กี่วินาทีต่อประโยค |

ครั้งแรกที่ใช้ แต่ละส่วนจะดาวน์โหลดโมเดลจาก Hugging Face และ Meta อัตโนมัติ (รวมประมาณ 1 GB)

## แปลงเสียงด้วยโมเดล

การแปลงเสียงด้วยโมเดล RVC ใช้ [Applio](https://github.com/IAHispano/Applio) 3.7.2 ซึ่งติดตั้งแยกจากแอปนี้ เพราะต้องใช้แพ็กเกจคนละเวอร์ชัน

1. ติดตั้ง Applio ตามวิธีในหน้า GitHub ของ Applio (Windows ใช้ `run-install.bat`)
2. ตั้งค่าตัวแปร `DUB_APPLIO_DIR` ให้ชี้ไปที่โฟลเดอร์ Applio ก่อนเปิดแอป เช่น
   - Windows: `set DUB_APPLIO_DIR=C:\Applio`
   - Mac/Linux: `export DUB_APPLIO_DIR=~/Applio`
3. ถ้า Python ของ Applio ไม่ได้อยู่ใน `.venv` ของมัน ให้ตั้ง `DUB_APPLIO_PYTHON` เป็น path ของ Python นั้น

## สอนเสียงของคุณ

1. อัดเสียงในแอป แล้วกด 👍 เก็บเทคที่ชอบ (เทรนรอบแรกควรมีอย่างน้อย 10 นาที)
2. กด **ดาวน์โหลดเทคที่เก็บไว้ (.zip)**
3. เปิด `notebooks/train_voice.ipynb` ใน Google Colab หรือ Kaggle แล้วรันตามขั้นตอน
4. อัปโหลด `.pth` และ `.index` กลับเข้าแอป แล้วเลือกใน **โมเดลเสียง**

ใช้เฉพาะเสียงของคุณเอง หรือเสียงที่เจ้าของอนุญาตแล้วเท่านั้น

## ใช้ใน project อื่น

### 1. แพ็กเกจ Python

```bash
pip install "dubstudio[ai] @ git+https://github.com/Cha12lotteZ/dub-studio"   # ไม่เอา AI: ตัด [ai] ออก
```

```python
import dubstudio

# ไฟล์เสียงหรือวิดีโอ → เสียงยักษ์โกรธในถ้ำ
dubstudio.process("take.wav", "giant.wav", character="giant", mood="angry", atmosphere="cave")

# numpy array ก็ได้ ได้ (audio, sample_rate) กลับมา
audio, sr = dubstudio.process((samples, 44100), character="robot")

# พิมพ์บทให้พูด (ต้องมีส่วน AI)
dubstudio.speak("เปิดใช้งานโหมดต่อสู้", "robot.wav", character="robot", atmosphere="radio")

dubstudio.presets()       # รายชื่อตัวละคร อารมณ์ บรรยากาศ
dubstudio.transcribe("clip.mp4")  # [{start, end, text}, ...]
```

ใส่ `model="ชื่อโมเดล"` เพื่อแปลงเป็นเสียงจากโมเดลที่เทรนไว้ (ต้องตั้งค่า Applio ตามหัวข้อด้านบน)

### 2. คำสั่งในเทอร์มินัล

```bash
dubstudio fx take.wav -o giant.wav --character giant --mood angry --atmosphere cave
dubstudio fx lines/*.wav -o out/ --character kid          # ทำทีละหลายไฟล์
dubstudio speak "หยุดอยู่ตรงนั้น!" -o line.wav --character giant
dubstudio presets
dubstudio serve --host 0.0.0.0   # ให้มือถือหรือเครื่องอื่นในบ้านเข้าได้
```

### 3. HTTP API (เกม Unity, Godot, เว็บ หรือภาษาอื่น)

เปิดแอปไว้ แล้วเรียก API ได้เลย ดูและลองกดทุกคำสั่งได้ที่ http://localhost:8000/docs

| คำสั่ง | ส่งอะไร | ได้อะไร |
|---|---|---|
| `GET /api/v1/presets` | | รายชื่อตัวละคร อารมณ์ บรรยากาศ โมเดล |
| `POST /api/v1/process` | ไฟล์ `audio` + `character`, `mood`, `atmosphere`, `mix`, `pitch`, `model` (form) | ไฟล์ WAV |
| `POST /api/v1/speak` | JSON `{"text": "...", "character": "...", ...}` | ไฟล์ WAV |
| `POST /api/v1/transcribe` | ไฟล์ `audio` | JSON บทพร้อมเวลา |

```bash
curl -X POST localhost:8000/api/v1/speak -H "Content-Type: application/json" \
  -d '{"text":"สวัสดี","character":"kid"}' -o hello.wav
```

ตัวอย่างโค้ดพร้อมใช้ใน [`examples/`](examples): Python, JavaScript, Godot 4 (`DubStudio.gd`) และ Unity (`DubStudioClient.cs`)

เว็บที่อยู่คนละโดเมนต้องตั้ง `DUB_CORS_ORIGINS=https://เว็บของคุณ` ก่อนเปิดแอป (เกมไม่ต้องตั้ง) ถ้าเปิดให้เครื่องอื่นเข้าได้ แนะนำให้ตั้ง `DUB_PASSWORD` ด้วย

## สำหรับนักพัฒนา

```bash
pip install -e ".[dev]"
pytest
```

- `dubstudio/core.py`: ฟังก์ชันที่ project อื่นเรียกใช้ (`process`, `speak`, `transcribe`)
- `dubstudio/effects.py`: พรีเซ็ตตัวละคร อารมณ์ บรรยากาศ (pedalboard)
- `dubstudio/media.py`: แปลงไฟล์ รวมเสียง และใส่เสียงกลับเข้าวิดีโอ (ffmpeg ในเครื่อง หรือตัวที่มากับ imageio-ffmpeg)
- `dubstudio/ai.py`: ถอดบท แยกเสียง พิมพ์บทให้พูด แปลงเสียง (โหลดเมื่อติดตั้งแล้วเท่านั้น)
- `dubstudio/main.py`: HTTP API และหน้าเว็บ (`dubstudio/web/`)
- `dubstudio/cli.py`: คำสั่ง `dubstudio`
