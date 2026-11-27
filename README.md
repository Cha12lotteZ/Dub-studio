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
2. สร้าง Space ใหม่ที่ [huggingface.co/new-space](https://huggingface.co/new-space): ตั้งชื่อ `dub-studio` เลือก **Docker → Blank** ฮาร์ดแวร์ **CPU basic (ฟรี)** และแนะนำให้เลือก **Private**
3. ใน Space ไปที่ **Settings → Variables and secrets → New secret** ตั้งชื่อ `DUB_PASSWORD` แล้วใส่รหัสผ่านที่ต้องการ (เปิดเว็บแล้วจะถามรหัสนี้ ชื่อผู้ใช้ใส่อะไรก็ได้)
4. สร้าง token ที่ [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) แบบ **Write**
5. ใน GitHub repo นี้ ไปที่ **Settings → Secrets and variables → Actions**
   - แท็บ Secrets: เพิ่ม `HF_TOKEN` = token จากข้อ 4
   - แท็บ Variables: เพิ่ม `HF_SPACE` = `ชื่อผู้ใช้-huggingface/dub-studio`
6. ไปที่แท็บ **Actions → Deploy to Hugging Face Space → Run workflow** หลังจากนี้ทุกครั้งที่มีโค้ดใหม่เข้า `main` จะส่งขึ้น Space ให้เอง (Space ใช้เวลา build ครั้งแรกประมาณ 15–20 นาที)

ถ้าตั้ง Space เป็น Public โดยไม่ตั้ง `DUB_PASSWORD` ใครมีลิงก์ก็เห็นโปรเจกต์และเสียงที่เก็บไว้ทั้งหมด

## ติดตั้งบนคอมตัวเอง

ต้องมี [Python 3.10+](https://www.python.org/downloads/) และ [ffmpeg](https://ffmpeg.org/download.html)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app
```

เปิด http://localhost:8000

ตอนนี้ใช้อัดเสียง ใส่เอฟเฟกต์ และรวมวิดีโอได้แล้ว ถ้าต้องการใช้ส่วน AI ให้ติดตั้งเพิ่ม (ประมาณ 2–3 GB):

```bash
pip install -r requirements-ai.txt
```

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

## สำหรับนักพัฒนา

```bash
pip install -r requirements-dev.txt
pytest
```

- `app/effects.py`: พรีเซ็ตตัวละคร อารมณ์ บรรยากาศ (pedalboard)
- `app/media.py`: แปลงไฟล์ รวมเสียง และใส่เสียงกลับเข้าวิดีโอ (ffmpeg)
- `app/ai.py`: ถอดบท แยกเสียง พิมพ์บทให้พูด แปลงเสียง (โหลดเมื่อติดตั้งแล้วเท่านั้น)
- `app/main.py`: API และหน้าเว็บ
- `data/`: โปรเจกต์ โมเดล และเทคที่เก็บไว้ (ไม่ถูก commit)
