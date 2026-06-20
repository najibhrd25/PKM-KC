# S.A.F.E — Panduan Komunikasi Antar Program

Cara program lain berkomunikasi dengan sistem S.A.F.E: **stream kamera, kontrol
servo, baca status, ganti mode**, dan menambah modul sendiri.

Ada **dua lapis** komunikasi. Pilih sesuai posisi program Anda:

| Lapis | Untuk siapa | Mekanisme | Dokumen |
|---|---|---|---|
| **Internal** | Modul Python baru yang jalan di dalam proses SAFE yang sama | Event Bus (publish/subscribe, in-process) | [Bagian A](#bagian-a--komunikasi-internal-event-bus) |
| **Eksternal** | Program/proses/komputer lain (dashboard, script, mesin lain) | HTTP WebBridge (REST + SSE + MJPEG) | [Bagian B](#bagian-b--komunikasi-eksternal-http-webbridge) |

Aturan emas: program eksternal **tidak pernah** mengakses Event Bus langsung.
Ia bicara HTTP ke WebBridge, lalu WebBridge yang menerjemahkannya menjadi event
internal. Jalur kritis (servo loop, audio) tetap di dalam Event Bus.

---

## Status Implementasi

Penting dibaca dulu — sebagian fitur masih rencana, bukan kode aktif:

| Fitur | Status | Catatan |
|---|---|---|
| Event Bus + semua event internal | ✅ **Jalan** | `safe/core/`, `safe/orchestrator.py`, adapter |
| Kontrol servo internal (`servo_cmd`) | ✅ **Jalan** | `ServoActuator` sudah subscribe |
| Audio, tracking, fusi sensor IR | ✅ **Jalan** | Pipeline inti tahap 1–5 |
| WebBridge HTTP API (`/stream`, `/events`, `/cmd/*`) | 🔶 **Rencana** | Spesifikasi di `Reference/WebBridgeReference.py`; folder `safe/web/` belum dibuat |
| Kontrol servo eksternal (`/cmd/jog`) | 🔶 **Rencana** | Butuh WebBridge **dan** handler `_on_jog` di `ServoActuator` (lihat B.3) |
| Stream kamera (`/stream`) | 🔶 **Rencana** | Butuh `YOLODetector` mem-publish `frame_update` (masih placeholder) |

> 🔶 = kontraknya sudah ditetapkan dan stabil, jadi Anda boleh menulis klien
> sekarang. Begitu lapis eksternal diaktifkan (lihat [prasyarat B](#prasyarat-aktivasi)),
> klien langsung berfungsi tanpa perubahan.

---

# Bagian A — Komunikasi Internal (Event Bus)

Untuk **modul Python baru** di dalam proses SAFE (mis. logger, notifikasi Telegram,
pola scan servo). Modul tidak saling memanggil; semua lewat papan pengumuman bersama.

## Konsep

- Satu `EventBus` ([safe/core/event_bus.py](core/event_bus.py)) memproses event
  **berurutan dalam satu worker thread**. Jadi antar-handler tidak ada race.
- Modul **publish** event (kirim pesan) dan **subscribe** event (dengar pesan).
- Modul tidak tahu siapa pengirim/penerima — cukup tahu **nama event + payload**.

## API Inti

```python
bus.subscribe(event_type: str, handler)   # handler(data: dict) -> None
bus.publish(event_type: str, data: dict)  # non-blocking
```

Selalu pakai konstanta dari [safe/core/events.py](core/events.py), jangan string
mentah — supaya typo ketahuan saat import.

## Daftar Event Lengkap

Sumber kebenaran: [safe/core/events.py](core/events.py).

### Input (sensor / detektor → bus)
| Event | Arah | Payload |
|---|---|---|
| `IR_READING` | IR Sensor → bus | `{sensor_id: int, voltage: float, triggered: bool}` |
| `FIRE_DETECTED` | YOLO/Fake → bus | `{bbox: [cx, cy, w, h], confidence: float, frame_w: int, frame_h: int}` |
| `FIRE_CLEARED` | YOLO → bus | `{}` |

### Perintah (Orchestrator/Tracking → aktuator)
| Event | Arah | Payload |
|---|---|---|
| `TRACK_START` | Orch → Tracking | `{bbox, frame_w, frame_h}` |
| `TRACK_STOP` | Orch → Tracking | `{}` |
| `SERVO_CMD` | Tracking → Servo | `{yaw_deg: float, pitch_deg: float}` |
| `SERVO_HOME` | Orch → Servo | `{}` |
| `SERVO_STOP` | Orch → Servo | `{}` |
| `AUDIO_CMD` | Orch → DAC | `{freq: float, amplitude: float, duration: float}` |
| `AUDIO_STOP` | Orch → DAC | `{}` |

### Status (notifikasi → siapa saja)
| Event | Arah | Payload |
|---|---|---|
| `STATE_CHANGED` | Orch → * | `{old: str, new: str}` |
| `TARGET_LOCKED` | Tracking → Orch | `{error_px: float}` |
| `EXTINGUISH_DONE` | Orch → * | `{}` |

### Web (dipakai lapis eksternal)
| Event | Arah | Payload |
|---|---|---|
| `FRAME_UPDATE` | YOLO → WebBridge | `{jpeg: bytes}` |
| `SET_MODE` | WebBridge → Orch | `{mode: "auto" \| "manual"}` |
| `SERVO_JOG` | WebBridge → Servo | `{d_yaw: float, d_pitch: float}` |
| `MODE_CHANGED` | Orch → WebBridge | `{mode: "auto" \| "manual"}` |

Nilai `new`/`old` pada `STATE_CHANGED` adalah salah satu dari:
`idle`, `pre_alarm`, `tracking`, `extinguishing`, `evaluating`, `cooldown`, `manual`
(lihat [safe/core/state_machine.py](core/state_machine.py)).

## Lifecycle Modul

Tiap modul mengimplementasi kontrak [BaseModule](core/interfaces.py):

```python
class BaseModule(ABC):
    def start(self) -> None: ...   # inisialisasi/thread, dipanggil saat boot
    def stop(self)  -> None: ...   # matikan dengan aman, dipanggil saat shutdown
```

Subscribe dilakukan di `__init__`, kerja berat dimulai di `start()`.

## Contoh 1 — Subscribe: modul CSVLogger

Mencatat tiap perubahan state & pemadaman selesai ke file CSV.

```python
# safe/logging/csv_logger.py
import csv, time, logging
from core.interfaces import BaseModule
from core import events

logger = logging.getLogger(__name__)


class CSVLogger(BaseModule):
    def __init__(self, event_bus, path="safe_log.csv"):
        self._bus = event_bus
        self._path = path
        # subscribe cukup sekali di __init__
        self._bus.subscribe(events.STATE_CHANGED, self._on_state)
        self._bus.subscribe(events.EXTINGUISH_DONE, self._on_done)

    def start(self):
        self._file = open(self._path, "a", newline="")
        self._writer = csv.writer(self._file)
        logger.info("CSVLogger mencatat ke %s", self._path)

    def stop(self):
        self._file.close()

    def _on_state(self, data):
        self._writer.writerow([time.time(), "state", data["old"], data["new"]])
        self._file.flush()

    def _on_done(self, data):
        self._writer.writerow([time.time(), "extinguish_done", "", ""])
        self._file.flush()
```

Daftarkan di [main.py](main.py) → fungsi `build_system`, tambahkan ke list `modules`:

```python
from logging.csv_logger import CSVLogger
...
modules = [
    IRSensorArray(bus),
    detector,
    TrackingLogic(bus),
    ServoActuator(bus),
    DACAudio(bus),
    CSVLogger(bus),          # <-- modul baru, cukup tambah satu baris
]
```

## Contoh 2 — Publish: gerakkan servo dari script (✅ jalan sekarang)

`ServoActuator` sudah subscribe `SERVO_CMD`, jadi mem-publish event ini langsung
menggerakkan servo ke sudut absolut (akan di-clamp ke batas fisik di config).

```python
from core import events

# yaw 0-180 (netral 90), pitch 50-140 (netral 70)
bus.publish(events.SERVO_CMD, {"yaw_deg": 120.0, "pitch_deg": 80.0})
```

> Catatan: di mode operasi otomatis, Tracking juga mem-publish `SERVO_CMD`. Untuk
> uji manual, lakukan saat Orchestrator tidak sedang `TRACKING` agar tidak berebut.

## Aturan Thread-Safety

- **Handler harus cepat & non-blocking.** Worker bus memproses event satu per satu;
  handler yang lambat menahan seluruh antrean. Kerja berat (inferensi, I/O panjang)
  → jalankan di thread sendiri di dalam modul.
- **Bus Dynamixel tidak thread-safe.** `ServoActuator` sudah menjaganya dengan
  `threading.Lock`; jangan akses driver servo dari luar modul itu.

---

# Bagian B — Komunikasi Eksternal (HTTP WebBridge)

Untuk program/proses/komputer **lain**. Contoh: dashboard di laptop, script Python
pengontrol, atau sistem monitoring terpisah.

## Prasyarat Aktivasi

Lapis ini 🔶 **belum aktif secara default**. Untuk menyalakannya:

1. Buat modul `safe/web/web_bridge.py` dari `Reference/WebBridgeReference.py`
   (+ `safe/web/__init__.py` dan `safe/web/static/index.html`).
2. Install dependency di Pi:
   ```bash
   pip3 install fastapi uvicorn
   ```
3. Aktifkan flag di [main.py](main.py):
   ```python
   bus, orchestrator, modules = build_system(use_fake_detector=True, use_web=True)
   ```
4. Jalankan SAFE, lalu akses dari klien: `http://<IP_PI>:8000`
   (host & port dari [safe/core/config.py](core/config.py): `WEB_HOST=0.0.0.0`,
   `WEB_PORT=8000`).

Pada contoh di bawah, ganti `<IP_PI>` dengan IP Raspberry Pi (mis. `10.7.101.150`).

## Daftar Endpoint

| Endpoint | Metode | Fungsi |
|---|---|---|
| `/` | GET | Halaman dashboard (HTML) |
| `/stream` | GET | Live kamera (MJPEG, `multipart/x-mixed-replace`) |
| `/events` | GET | Status real-time (SSE: state, mode, deteksi) |
| `/cmd/mode` | POST | Ganti mode: `{"mode": "auto"\|"manual"}` |
| `/cmd/jog` | POST | Gerak servo inkremental: `{"d_yaw": float, "d_pitch": float}` |
| `/heartbeat` | POST | Tanda UI masih aktif (cegah balik ke AUTO) |

## B.1 — Stream Kamera (`GET /stream`)

Stream MJPEG. 🔶 Frame baru muncul saat `YOLODetector` aktif mem-publish
`frame_update`; selama YOLO masih placeholder, stream menampilkan placeholder kosong.

**Python (OpenCV) — paling praktis untuk olah frame:**
```python
import cv2

cap = cv2.VideoCapture("http://<IP_PI>:8000/stream")
while True:
    ok, frame = cap.read()
    if not ok:
        break
    cv2.imshow("SAFE stream", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
cap.release()
cv2.destroyAllWindows()
```

**Python (requests) — simpan/teruskan byte mentah:**
```python
import requests

with requests.get("http://<IP_PI>:8000/stream", stream=True) as r:
    buf = bytes()
    for chunk in r.iter_content(4096):
        buf += chunk
        a, b = buf.find(b"\xff\xd8"), buf.find(b"\xff\xd9")
        if a != -1 and b != -1:
            jpg = buf[a:b + 2]      # satu frame JPEG utuh
            buf = buf[b + 2:]
            # ... proses jpg ...
```

**curl — cek cepat apakah stream hidup:**
```bash
curl -s -I http://<IP_PI>:8000/stream
# cari header: Content-Type: multipart/x-mixed-replace; boundary=frame
```

## B.2 — Status Real-time (`GET /events`)

Server-Sent Events. Tiap baris `data:` berisi JSON. Tiga jenis payload:

```json
{"type": "state",     "value": "tracking"}
{"type": "mode",      "value": "manual"}
{"type": "detection", "bbox": [320, 240, 80, 100], "confidence": 0.91}
```

**Python:**
```python
import json, requests

with requests.get("http://<IP_PI>:8000/events", stream=True) as r:
    for line in r.iter_lines():
        if line and line.startswith(b"data: "):
            msg = json.loads(line[6:])
            print(msg["type"], msg.get("value", msg))
```

**curl:**
```bash
curl -N http://<IP_PI>:8000/events
```
(`-N` = no-buffer, supaya event muncul real-time)

## B.3 — Kontrol Servo (`POST /cmd/jog`)

Gerak servo **inkremental** (delta derajat) dari posisi sekarang, lalu di-clamp ke
batas fisik. Cocok untuk joystick.

> ⚠️ Prasyarat: (1) mode harus **`manual`** dulu (lihat B.4) — di mode auto, jog
> diabaikan demi keamanan; (2) 🔶 butuh handler `_on_jog` di `ServoActuator`. Pada
> scaffold inti sekarang handler itu belum ada — tambahkan saat fase web (lihat
> `Reference/ARCHITECTURE.md` §11.4). Tanpa itu, `/cmd/jog` terkirim tapi servo diam.

**Python:**
```python
import requests
BASE = "http://<IP_PI>:8000"

# geser yaw +3°, pitch tetap
requests.post(f"{BASE}/cmd/jog", json={"d_yaw": 3.0, "d_pitch": 0.0})
```

**curl:**
```bash
curl -X POST http://<IP_PI>:8000/cmd/jog \
     -H "Content-Type: application/json" \
     -d '{"d_yaw": 3.0, "d_pitch": 0.0}'
```

Besar langkah yang disarankan: `WEB_JOG_STEP_DEG = 3.0` (dari config).

## B.4 — Ganti Mode (`POST /cmd/mode`)

`manual` menjeda fusi sensor & tracking otomatis (servo tidak berebut). `auto`
mengembalikan ke siaga otomatis (`IDLE`). Demi keamanan, mode `manual` **tidak
pernah** membunyikan audio.

**Python:**
```python
requests.post("http://<IP_PI>:8000/cmd/mode", json={"mode": "manual"})
# ... kendalikan servo via /cmd/jog ...
requests.post("http://<IP_PI>:8000/cmd/mode", json={"mode": "auto"})
```

**curl:**
```bash
curl -X POST http://<IP_PI>:8000/cmd/mode \
     -H "Content-Type: application/json" -d '{"mode": "manual"}'
```

## B.5 — Heartbeat (`POST /heartbeat`)

Selama mode `manual`, klien wajib mengirim heartbeat berkala. Jika WebBridge tidak
menerima heartbeat selama `WEB_HEARTBEAT_TIMEOUT` (default **5 detik**), sistem
otomatis kembali ke **AUTO** — ini mencegah servo terkunci di manual saat klien
mati/koneksi putus.

**Python (loop di thread terpisah):**
```python
import requests, threading, time

def heartbeat_loop(base, stop):
    while not stop.is_set():
        try:
            requests.post(f"{base}/heartbeat", timeout=1)
        except requests.RequestException:
            pass
        time.sleep(2)        # < WEB_HEARTBEAT_TIMEOUT (5 dtk)

stop = threading.Event()
threading.Thread(target=heartbeat_loop,
                 args=("http://<IP_PI>:8000", stop), daemon=True).start()
```

**curl:**
```bash
curl -X POST http://<IP_PI>:8000/heartbeat
```

## Alur Tipikal Mode Manual (Python)

```python
import requests, threading, time
BASE = "http://<IP_PI>:8000"

def heartbeat_loop(base, stop):          # sama seperti contoh di B.5
    while not stop.is_set():
        try:
            requests.post(f"{base}/heartbeat", timeout=1)
        except requests.RequestException:
            pass
        time.sleep(2)

# 1. masuk manual + mulai heartbeat
requests.post(f"{BASE}/cmd/mode", json={"mode": "manual"})
stop = threading.Event()
threading.Thread(target=heartbeat_loop, args=(BASE, stop), daemon=True).start()

# 2. kontrol servo
for _ in range(5):
    requests.post(f"{BASE}/cmd/jog", json={"d_yaw": 3.0, "d_pitch": 0.0})
    time.sleep(0.3)

# 3. selesai -> kembali auto
stop.set()
requests.post(f"{BASE}/cmd/mode", json={"mode": "auto"})
```

---

# Bagian C — Lampiran

## Peta Event ↔ Endpoint

Endpoint HTTP hanyalah "gerbang" yang menerjemahkan request eksternal menjadi event
internal (atau sebaliknya):

| Endpoint eksternal | Event internal | Arah |
|---|---|---|
| `POST /cmd/mode` | `SET_MODE` | masuk |
| `POST /cmd/jog` | `SERVO_JOG` | masuk |
| `GET /events` (`state`) | `STATE_CHANGED` | keluar |
| `GET /events` (`mode`) | `MODE_CHANGED` | keluar |
| `GET /events` (`detection`) | `FIRE_DETECTED` | keluar |
| `GET /stream` | `FRAME_UPDATE` | keluar |

## Ringkasan Keamanan

- **Audio dibatasi keras di kode**, bukan opsional: `AMPLITUDE_MAX_SAFE` &
  `AUDIO_MAX_DURATION` (lihat [config.py](core/config.py)). Perintah `audio_cmd`
  yang melebihi batas otomatis dipotong oleh `DACAudio`.
- **Cooldown wajib** setelah tiap operasi audio (state `COOLDOWN`).
- **Mode `manual` tidak pernah menyalakan audio.** Saat masuk manual, Orchestrator
  mengirim `AUDIO_STOP` + `TRACK_STOP`.
- **Heartbeat = safety net**: klien manual yang hilang → sistem balik AUTO sendiri.

## Referensi Lanjutan

- Desain lengkap & rasional: `Reference/ARCHITECTURE.md`
- Implementasi referensi WebBridge: `Reference/WebBridgeReference.py`
- Definisi event: [safe/core/events.py](core/events.py)
- Parameter & batas: [safe/core/config.py](core/config.py)
