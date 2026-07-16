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

Seluruh lapisan sudah terintegrasi dan aktif (lihat `DOKUMENTASI_SISTEM.md`
untuk gambaran sistem penuh):

| Fitur | Status | Catatan |
|---|---|---|
| Event Bus + semua event internal | ✅ **Jalan** | `safe/core/`, `safe/orchestrator.py`, adapter |
| Kontrol servo internal (`servo_cmd`) | ✅ **Jalan** | `ServoActuator` (GroupSyncWrite + rate-limit) |
| Audio, tracking, fusi sensor IR | ✅ **Jalan** | Pipeline inti + fusi kaya (arah IR & kesepakatan) |
| Deteksi kamera (`YOLODetector`) | ✅ **Jalan** | Picamera2 + YOLO NCNN; publish `fire_detected`/`fire_cleared` |
| Scanning otomatis saat IDLE | ✅ **Jalan** | `tracking/scanner.py` (raster zig-zag) |
| WebBridge HTTP API (`/stream`, `/events`, `/cmd/*`) | ✅ **Jalan** | `safe/web/web_bridge.py` + `static/index.html`; aktif via `use_web=True` |
| Kontrol servo eksternal (`/cmd/jog`) | ✅ **Jalan** | Handler `_on_jog` di `ServoActuator` (state sudut dibagi dgn `servo_cmd`) |
| Stream kamera (`/stream`) | ✅ **Jalan** | `YOLODetector` mem-publish `frame_update` (JPEG beranotasi) |

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
| `SERVO_HOME` | Orch/WebBridge → Servo | `{}` |
| `SERVO_STOP` | Orch/WebBridge → Servo | `{}` (torque off) |
| `AUDIO_CMD` | Orch/WebBridge → DAC | `{freq, amplitude, duration, waveform?, f_start?, f_end?, n_cycles?, pulse_waveform?, inverted?, half_cycle?}` |
| `AUDIO_STOP` | Orch/WebBridge → DAC | `{}` |

### Status (notifikasi → siapa saja)
| Event | Arah | Payload |
|---|---|---|
| `STATE_CHANGED` | Orch → * | `{old: str, new: str}` |
| `TARGET_LOCKED` | Tracking → Orch | `{error_px: float}` |
| `EXTINGUISH_DONE` | Orch → * | `{}` |
| `AUDIO_STATE` | DAC → * | `{playing: bool, freq?, amplitude?, duration?, waveform?}` |
| `SERVO_STATE` | Servo → * | `{yaw_deg: float, pitch_deg: float, torque: bool}` |

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

# yaw & pitch 135-225 (netral 180) — turret di-center 180° ±45°
bus.publish(events.SERVO_CMD, {"yaw_deg": 200.0, "pitch_deg": 165.0})
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

Modul `safe/web/` sudah dibuat (`web_bridge.py`, `__init__.py`,
`static/index.html`). Lapis ini **tidak aktif secara default** — untuk menyalakannya:

1. Install dependency di Pi:
   ```bash
   pip3 install fastapi uvicorn
   ```
2. Aktifkan flag di [main.py](main.py):
   ```python
   bus, orchestrator, modules = build_system(use_fake_detector=True, use_web=True)
   ```
3. Jalankan SAFE, lalu akses dari klien: `http://<IP_PI>:8000`
   (host & port dari [safe/core/config.py](core/config.py): `WEB_HOST=0.0.0.0`,
   `WEB_PORT=8000`).

Pada contoh di bawah, ganti `<IP_PI>` dengan IP Raspberry Pi (mis. `10.7.101.150`).

## Daftar Endpoint

| Endpoint | Metode | Fungsi |
|---|---|---|
| `/` | GET | Halaman dashboard (HTML) |
| `/stream` | GET | Live kamera (MJPEG, `multipart/x-mixed-replace`) |
| `/events` | GET | Status real-time (SSE: state, mode, deteksi, ir, audio, servo, log) |
| `/logs` | GET | Riwayat log kejadian (JSON, ring buffer 200 entri) |
| `/cmd/mode` | POST | Ganti mode: `{"mode": "auto"\|"manual"}` |
| `/cmd/jog` | POST | Gerak servo inkremental: `{"d_yaw": float, "d_pitch": float}` — hanya mode manual (409 jika tidak) |
| `/cmd/servo` | POST | `{"action": "home"\|"torque_off"\|"move", "yaw_deg"?, "pitch_deg"?}` — `home`/`move` hanya manual; `torque_off` selalu boleh |
| `/cmd/audio` | POST | `{"action": "play"\|"stop", "freq", "amplitude", "duration", "waveform", ...}` — `play` hanya manual; `stop` selalu boleh |
| `/heartbeat` | POST | Tanda UI masih aktif (cegah balik ke AUTO) |

## B.1 — Stream Kamera (`GET /stream`)

Stream MJPEG. Frame beranotasi muncul saat `YOLODetector` aktif mem-publish
`frame_update` (jalankan dengan `use_fake_detector=False`); dengan FakeDetector,
stream menampilkan placeholder kosong.

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

Server-Sent Events. Tiap baris `data:` berisi JSON. Jenis payload:

```json
{"type": "state",     "value": "tracking"}
{"type": "mode",      "value": "manual"}
{"type": "detection", "bbox": [320, 240, 80, 100], "confidence": 0.91}
{"type": "ir",        "sensors": [{"sensor_id": 1, "raw": 12345, "voltage": 1.54, "triggered": true}, ...],
                      "ir_hot": true, "ir_x": -0.42}
{"type": "audio",     "playing": true, "freq": 45.0, "amplitude": 0.3, "duration": 10.0, "waveform": "sine"}
{"type": "servo",     "yaw_deg": 183.0, "pitch_deg": 178.5, "torque": true}
{"type": "log",       "t": 1752600000.0, "msg": "Mode: MANUAL"}
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

> ✅ Handler `_on_jog` di `ServoActuator` sudah ada dan berbagi state sudut dengan
> `servo_cmd` (jog menambah delta ke posisi terakhir, lalu di-clamp). Dashboard hanya
> mengirim `/cmd/jog` saat mode **`manual`** (lihat B.4); di mode auto, orchestrator
> sendiri dapat mengirim jog kecil ke arah IR (fallback ir-seek saat PRE_ALARM).

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

## B.3b — Kontrol Servo Lanjutan (`POST /cmd/servo`)

Aksi diskret servo (selain jog inkremental):

```bash
# kembali ke posisi netral 180/180 (hanya mode manual)
curl -X POST http://<IP_PI>:8000/cmd/servo \
     -H "Content-Type: application/json" -d '{"action": "home"}'

# posisi absolut (hanya mode manual; clamp 135-225° di ServoActuator)
curl -X POST http://<IP_PI>:8000/cmd/servo \
     -H "Content-Type: application/json" \
     -d '{"action": "move", "yaw_deg": 200.0, "pitch_deg": 170.0}'

# matikan torsi (boleh dari mode apa pun — mematikan selalu aman)
curl -X POST http://<IP_PI>:8000/cmd/servo \
     -H "Content-Type: application/json" -d '{"action": "torque_off"}'
```

Setelah `torque_off`, perintah gerak berikutnya (jog/home/move) otomatis
menyalakan kembali torsi.

## B.3c — Kontrol Audio/DAC (`POST /cmd/audio`)

Memutar sinyal pemadaman secara manual. `play` hanya diterima saat mode
`manual` (409 jika tidak); `stop` selalu boleh. Amplitudo & durasi tetap
dipotong keras oleh `DACAudio` (`AMPLITUDE_MAX_SAFE`, `AUDIO_MAX_DURATION`)
apa pun nilai yang dikirim.

```bash
# sine 45 Hz, 10 detik
curl -X POST http://<IP_PI>:8000/cmd/audio \
     -H "Content-Type: application/json" \
     -d '{"action": "play", "freq": 45, "amplitude": 0.3, "duration": 10, "waveform": "sine"}'

# sweep 30 -> 90 Hz
curl -X POST http://<IP_PI>:8000/cmd/audio \
     -H "Content-Type: application/json" \
     -d '{"action": "play", "waveform": "sweep", "f_start": 30, "f_end": 90, "duration": 10, "amplitude": 0.3}'

# pulsa vortex-ring (durasi = n_cycles / freq)
curl -X POST http://<IP_PI>:8000/cmd/audio \
     -H "Content-Type: application/json" \
     -d '{"action": "play", "waveform": "pulse", "freq": 45, "n_cycles": 3, "pulse_waveform": "sine", "inverted": false, "half_cycle": false}'

# stop
curl -X POST http://<IP_PI>:8000/cmd/audio \
     -H "Content-Type: application/json" -d '{"action": "stop"}'
```

Waveform yang tersedia: `sine`, `square`, `sawtooth`, `triangle`, `sweep`,
`pulse`. Status pemutaran dipublikasikan sebagai SSE `{"type": "audio", ...}`.

## B.4 — Ganti Mode (`POST /cmd/mode`)

`manual` menjeda fusi sensor & tracking otomatis (servo tidak berebut) dan
membuka kontrol per-komponen (`/cmd/jog`, `/cmd/servo`, `/cmd/audio`). `auto`
mengembalikan ke siaga otomatis (`IDLE`). Demi keamanan, audio yang sedang
diputar **selalu dihentikan** saat berpindah mode — baik masuk maupun keluar
manual (termasuk saat heartbeat timeout memaksa balik ke AUTO).

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
| `POST /cmd/servo` (`home`/`torque_off`/`move`) | `SERVO_HOME` / `SERVO_STOP` / `SERVO_CMD` | masuk |
| `POST /cmd/audio` (`play`/`stop`) | `AUDIO_CMD` / `AUDIO_STOP` | masuk |
| `GET /events` (`state`) | `STATE_CHANGED` | keluar |
| `GET /events` (`mode`) | `MODE_CHANGED` | keluar |
| `GET /events` (`detection`) | `FIRE_DETECTED` | keluar |
| `GET /events` (`ir`) | `IR_READING` (agregat 5 sensor, throttle 0.2 s, + arah `ir_x`) | keluar |
| `GET /events` (`audio`) | `AUDIO_STATE` | keluar |
| `GET /events` (`servo`) | `SERVO_STATE` | keluar |
| `GET /events` (`log`) / `GET /logs` | ring buffer WebBridge | keluar |
| `GET /stream` | `FRAME_UPDATE` | keluar |

## Ringkasan Keamanan

- **Audio dibatasi keras di kode**, bukan opsional: `AMPLITUDE_MAX_SAFE` &
  `AUDIO_MAX_DURATION` (lihat [config.py](core/config.py)). Perintah `audio_cmd`
  yang melebihi batas otomatis dipotong oleh `DACAudio` — termasuk yang datang
  dari `/cmd/audio` manual (n_cycles pulsa juga di-clamp agar durasi ≤ batas).
- **Cooldown wajib** setelah tiap operasi audio otomatis (state `COOLDOWN`).
- **Audio manual diizinkan hanya saat mode `manual`** (endpoint `play` menolak
  409 di mode lain), dan **`AUDIO_STOP` dijamin saat keluar manual** — baik user
  menekan AUTO maupun watchdog heartbeat yang memaksa balik.
- **Perintah gerak servo dari web** (`/cmd/jog`, `/cmd/servo` home/move) hanya
  diterima saat manual; `torque_off` dan `stop` audio selalu boleh (mematikan
  selalu aman).
- **Heartbeat = safety net**: klien manual yang hilang → sistem balik AUTO
  sendiri (dan audio manual ikut berhenti).

## Referensi Lanjutan

- **Kontrak API web lengkap untuk integrasi UI kustom: [web/DOKUMENTASI_WEB.md](web/DOKUMENTASI_WEB.md)**
- Desain lengkap & rasional: `Reference/ARCHITECTURE.md`
- Implementasi referensi WebBridge: `Reference/WebBridgeReference.py`
- Definisi event: [safe/core/events.py](core/events.py)
- Parameter & batas: [safe/core/config.py](core/config.py)
