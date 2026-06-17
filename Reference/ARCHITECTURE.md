# S.A.F.E — Dokumentasi Arsitektur Perangkat Lunak

**Smart Acoustic Fire Extinguisher**
Sistem pemadam api akustik berbasis Raspberry Pi 5 — deteksi YOLO + fusi sensor IR, tracking servo 2-sumbu, pemadaman gelombang suara 30–60 Hz.

Bahasa: **Python 3** · Platform: **Raspberry Pi 5 (Pi OS Lite, headless)**

---

## Daftar Isi

1. [Filosofi Desain](#1-filosofi-desain)
2. [Arsitektur Komunikasi (Event Bus)](#2-arsitektur-komunikasi-event-bus)
3. [Struktur Folder](#3-struktur-folder)
4. [Kontrak Event](#4-kontrak-event)
5. [State Machine Orchestrator](#5-state-machine-orchestrator)
6. [Interface Tiap Modul](#6-interface-tiap-modul)
7. [Alur Eksekusi Lengkap](#7-alur-eksekusi-lengkap)
8. [Dependency Injection & Bootstrap](#8-dependency-injection--bootstrap)
9. [Strategi Testing](#9-strategi-testing)
10. [Catatan Implementasi & Keamanan](#10-catatan-implementasi--keamanan)
11. [Antarmuka Web (Dashboard)](#11-antarmuka-web-dashboard)
12. [Roadmap Integrasi](#12-roadmap-integrasi)

---

## 1. Filosofi Desain

Tiga prinsip yang menjadi dasar seluruh arsitektur:

**Modul terpisah, komunikasi via Event Bus.** Setiap subsistem (sensor IR, deteksi YOLO, tracking, servo, audio) adalah modul mandiri. Modul tidak saling memanggil langsung — mereka *publish* event ke bus dan *subscribe* event yang relevan. Konsekuensinya: satu modul bisa diubah, diganti, atau dimatikan tanpa menyentuh modul lain.

**Interface abstrak sebagai kontrak.** Setiap kategori modul mengimplementasikan sebuah base class (`BaseSensor`, `BaseDetector`, `BaseActuator`, `BaseAudio`). Orchestrator hanya tahu kontraknya, tidak peduli implementasi konkretnya. Inilah arti "API" dalam proyek ini: kontrak yang stabil antar bagian.

**Dependency Injection untuk testability.** Orchestrator menerima modul dari luar (`main.py`), bukan membuatnya sendiri. Karena itu, modul nyata bisa diganti dengan *fake/mock* saat testing. YOLO yang belum jadi cukup digantikan `FakeDetector` — seluruh rantai tracking → servo → audio tetap bisa diuji penuh tanpa kamera dan tanpa api sungguhan.

Semua modul berjalan **in-process** dalam satu interpreter Python. Komunikasi data realtime (frame, koordinat, status) lewat Event Bus internal. Tidak ada overhead HTTP/serialisasi di jalur kritis. Lapisan HTTP (FastAPI) bersifat **opsional** dan hanya dipasang di *tepi* sistem (dashboard, notifikasi) tanpa mengubah inti.

---

## 2. Arsitektur Komunikasi (Event Bus)

Analogi: Event Bus adalah **papan pengumuman**. Modul menempel pesan (publish) dan membaca pesan relevan (subscribe). Tidak ada yang harus menelepon langsung.

```
                  ┌──────────────────────────┐
                  │      ORCHESTRATOR         │
                  │  state machine + fusi     │
                  └──────────┬───────────────┘
                             │ pub/sub
                  ┌──────────┴───────────────┐
                  │       EVENT BUS           │
                  │   (pusat komunikasi)      │
                  └──┬─────┬─────┬─────┬──────┘
        publish ─────┘     │     │     └───── subscribe
   ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐
   │ IR Sensor│  │  YOLO   │  │ Tracking │  │   Servo   │  │   DAC    │
   │   (pub)  │  │ (pub)*  │  │(sub/pub) │  │   (sub)   │  │  (sub)   │
   └──────────┘  └─────────┘  └──────────┘  └───────────┘  └──────────┘
   *YOLO masih placeholder — diisi belakangan
```

### Implementasi Event Bus

Cukup ringan: dictionary callback + thread-safe queue. Tidak perlu library berat.

```python
# safe/core/event_bus.py
"""
Event Bus internal — publish/subscribe sederhana, thread-safe.

Modul tidak saling memanggil langsung. Mereka publish event ke bus,
dan bus meneruskan ke semua subscriber event tersebut.
"""

import queue
import threading
import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()

    # ---------- API publik ----------
    def subscribe(self, event_type: str, handler: Callable[[dict], None]) -> None:
        """Daftarkan handler untuk sebuah jenis event."""
        with self._lock:
            self._subscribers[event_type].append(handler)
        logger.debug("Subscribe '%s' -> %s", event_type, handler.__qualname__)

    def publish(self, event_type: str, data: dict | None = None) -> None:
        """Kirim event ke bus. Non-blocking — diproses oleh worker thread."""
        self._queue.put((event_type, data or {}))

    # ---------- lifecycle ----------
    def start(self) -> None:
        self._running = True
        self._worker = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._worker.start()
        logger.info("EventBus berjalan.")

    def stop(self) -> None:
        self._running = False
        self._queue.put(("__stop__", {}))
        if self._worker:
            self._worker.join(timeout=2.0)
        logger.info("EventBus berhenti.")

    # ---------- internal ----------
    def _dispatch_loop(self) -> None:
        while self._running:
            event_type, data = self._queue.get()
            if event_type == "__stop__":
                break
            for handler in list(self._subscribers.get(event_type, [])):
                try:
                    handler(data)
                except Exception:
                    logger.exception("Handler gagal untuk event '%s'", event_type)
```

Catatan: satu worker thread memproses event berurutan, sehingga handler tidak perlu khawatir race antar event. Operasi berat (inferensi YOLO, loop audio) tetap berjalan di thread modulnya sendiri — bus hanya untuk *pesan*, bukan untuk komputasi.

---

## 3. Struktur Folder

```
safe/
├── core/
│   ├── __init__.py
│   ├── event_bus.py          # EventBus (pub/sub)
│   ├── interfaces.py         # base class abstrak semua modul
│   ├── events.py             # konstanta nama event + skema payload
│   ├── state_machine.py      # enum State + transisi
│   └── config.py             # semua parameter terpusat
│
├── sensors/
│   ├── __init__.py
│   ├── ir_sensor.py          # IRSensorArray (bungkus IR.py)
│   └── _ir_driver.py         # = IR.py lama, tak diubah
│
├── detection/
│   ├── __init__.py
│   ├── base.py               # (opsional) re-export BaseDetector
│   ├── fake_detector.py      # FakeDetector untuk testing
│   └── yolo_detector.py      # YOLODetector — PLACEHOLDER, diisi nanti
│
├── tracking/
│   ├── __init__.py
│   └── tracker.py            # TrackingLogic: bbox -> sudut servo
│
├── actuation/
│   ├── __init__.py
│   ├── servo_actuator.py     # ServoActuator (bungkus Servo.py)
│   └── _servo_driver.py      # = Servo.py lama, tak diubah
│
├── audio/
│   ├── __init__.py
│   ├── dac_audio.py          # DACAudio (bungkus DAC.py)
│   └── _dac_driver.py        # = DAC.py lama, tak diubah
│
├── web/                      # OPSIONAL — antarmuka web (tepi sistem)
│   ├── __init__.py
│   ├── web_bridge.py         # WebBridge: FastAPI + SSE + MJPEG
│   └── static/
│       └── index.html        # frontend dashboard (kerangka contoh)
│
├── orchestrator.py           # otak: fusi sensor + state machine
├── main.py                   # bootstrap + dependency injection
│
└── tests/
    ├── test_event_bus.py
    ├── test_tracker.py
    ├── test_orchestrator.py  # pakai FakeDetector + FakeSensor
    └── test_integration.py   # rantai penuh tanpa hardware
```

Prinsip penamaan: file driver lama Anda (`IR.py`, `Servo.py`, `DAC.py`) disalin menjadi `_ir_driver.py`, `_servo_driver.py`, `_dac_driver.py` **tanpa perubahan logika**. Prefix underscore menandakan "internal, jangan dipakai langsung". Modul publik (`ir_sensor.py`, dst.) membungkusnya dengan interface standar.

---

## 4. Kontrak Event

Inilah "API" antar modul. Semua nama event dan bentuk payload didefinisikan di satu tempat agar tidak ada salah ketik.

```python
# safe/core/events.py
"""
Definisi terpusat semua event yang lewat di Event Bus.

Pakai konstanta ini, jangan string mentah, supaya typo ketahuan
saat import (bukan saat runtime).
"""

# ---- Event dari sensor / detektor (INPUT) ----
IR_READING      = "ir_reading"       # IR Sensor   -> bus
FIRE_DETECTED   = "fire_detected"    # YOLO        -> bus
FIRE_CLEARED    = "fire_cleared"     # YOLO        -> bus (api hilang dari frame)

# ---- Event perintah dari Orchestrator (COMMAND) ----
TRACK_START     = "track_start"      # Orchestrator -> Tracking
TRACK_STOP      = "track_stop"       # Orchestrator -> Tracking
SERVO_CMD       = "servo_cmd"        # Tracking     -> Servo
SERVO_HOME      = "servo_home"       # Orchestrator -> Servo
SERVO_STOP      = "servo_stop"       # Orchestrator -> Servo
AUDIO_CMD       = "audio_cmd"        # Orchestrator -> DAC (mulai pemadaman)
AUDIO_STOP      = "audio_stop"       # Orchestrator -> DAC

# ---- Event status (NOTIFIKASI, untuk logging / dashboard) ----
STATE_CHANGED   = "state_changed"    # Orchestrator -> siapa saja
TARGET_LOCKED   = "target_locked"    # Tracking     -> Orchestrator
EXTINGUISH_DONE = "extinguish_done"  # Orchestrator -> siapa saja

# ---- Event antarmuka web (OPSIONAL, tepi sistem) ----
FRAME_UPDATE    = "frame_update"     # YOLO        -> WebBridge (stream MJPEG)
SET_MODE        = "set_mode"         # WebBridge   -> Orchestrator (AUTO/MANUAL)
SERVO_JOG       = "servo_jog"        # WebBridge   -> Servo (joystick inkremental)
MODE_CHANGED    = "mode_changed"     # Orchestrator -> WebBridge (notifikasi mode)
```

### Skema Payload

| Event | Arah | Payload |
|---|---|---|
| `ir_reading` | IR → bus | `{ sensor_id: int, voltage: float, triggered: bool }` |
| `fire_detected` | YOLO → bus | `{ bbox: [cx, cy, w, h], confidence: float, frame_w: int, frame_h: int }` |
| `fire_cleared` | YOLO → bus | `{}` |
| `track_start` | Orch → Tracking | `{ bbox: [cx, cy, w, h], frame_w: int, frame_h: int }` |
| `track_stop` | Orch → Tracking | `{}` |
| `servo_cmd` | Tracking → Servo | `{ yaw_deg: float, pitch_deg: float }` |
| `servo_home` | Orch → Servo | `{}` |
| `servo_stop` | Orch → Servo | `{}` |
| `audio_cmd` | Orch → DAC | `{ freq: float, amplitude: float, duration: float }` |
| `audio_stop` | Orch → DAC | `{}` |
| `state_changed` | Orch → * | `{ old: str, new: str }` |
| `target_locked` | Tracking → Orch | `{ error_px: float }` |
| `frame_update` | YOLO → WebBridge | `{ jpeg: bytes }` (frame ter-annotate, sudah JPEG-encoded) |
| `set_mode` | WebBridge → Orch | `{ mode: "auto" \| "manual" }` |
| `servo_jog` | WebBridge → Servo | `{ d_yaw: float, d_pitch: float }` (delta derajat) |
| `mode_changed` | Orch → WebBridge | `{ mode: "auto" \| "manual" }` |

Catatan koordinat bbox: `cx, cy` = titik tengah bounding box (piksel), `w, h` = lebar/tinggi. Semua relatif terhadap `frame_w × frame_h`. Ini format yang akan dikeluarkan YOLO nanti — dan format yang sama dipakai `FakeDetector` saat testing.

---

## 5. State Machine Orchestrator

Orchestrator adalah otak sistem. Ia tidak mengontrol hardware langsung; ia mengubah *state* berdasarkan event masuk, lalu menerbitkan perintah.

```python
# safe/core/state_machine.py
from enum import Enum

class State(Enum):
    IDLE          = "idle"           # siaga, scanning pasif
    PRE_ALARM     = "pre_alarm"      # IR memicu, menunggu konfirmasi visual
    TRACKING      = "tracking"       # api terkonfirmasi, servo mengunci target
    EXTINGUISHING = "extinguishing"  # servo terkunci + audio menyala
    EVALUATING    = "evaluating"     # cek apakah api sudah padam
    COOLDOWN      = "cooldown"       # jeda wajib setelah operasi audio
    MANUAL        = "manual"         # kontrol joystick dari web; fusi sensor dijeda
```

### Diagram Transisi

```
        ┌──────────────────────────────────────────────────┐
        │                                                   │ api masih ada
        ▼                                                   │
   ┌────────┐  IR triggered   ┌───────────┐  YOLO confirm   ┌──────────┐
   │  IDLE  │ ──────────────► │ PRE_ALARM │ ──────────────► │ TRACKING │
   └────────┘                 └───────────┘                 └────┬─────┘
        ▲                          │                              │ target locked
        │ timeout / no fire        │ timeout                      ▼
        │◄─────────────────────────┘                       ┌───────────────┐
        │                                                   │ EXTINGUISHING │
        │                                                   └───────┬───────┘
        │                                                           │ durasi habis
        │                                                           ▼
        │   api padam        ┌──────────┐   api masih    ┌────────────┐
        └────────────────────│ COOLDOWN │◄───────────────│ EVALUATING │
                             └──────────┘                 └────────────┘
                                                          (jika masih ada → TRACKING)
```

### Mode AUTO vs MANUAL

Selain alur otomatis di atas, ada satu jalur lintas-state yang dipicu dari web:

```
   (state apa pun)        set_mode {manual}        ┌──────────┐
   ─────────────────────────────────────────────► │  MANUAL  │
                                                   └────┬─────┘
        ▲   set_mode {auto}  ATAU  heartbeat timeout    │
        └───────────────────────────────────────────────┘
                          kembali ke IDLE
```

Aturan mode:

- Default sistem adalah **AUTO**. Fusi sensor + tracking otomatis berjalan normal.
- Saat web mengirim `set_mode {manual}`, Orchestrator masuk `MANUAL`: fusi sensor **dijeda** (event IR/YOLO tetap di-cache untuk dashboard, tapi tidak memicu transisi), sehingga servo tidak berebut antara perintah joystick dan tracking otomatis.
- Selama `MANUAL`, joystick web mengirim `servo_jog {d_yaw, d_pitch}` langsung ke Servo.
- Sistem kembali ke **AUTO** (state `IDLE`) lewat **dua jalur**: (a) toggle eksplisit `set_mode {auto}`, atau (b) **heartbeat timeout** — jika WebBridge tidak menerima heartbeat dari browser selama `WEB_HEARTBEAT_TIMEOUT` detik (browser ditutup, koneksi putus), ia otomatis mem-publish `set_mode {auto}`. Ini memenuhi syarat "saat pengguna tidak mengakses UI, otomatis masuk AUTO".
- Demi keamanan, `MANUAL` tidak pernah otomatis menyalakan audio. Pemadaman saat manual (jika diizinkan) harus tombol eksplisit di UI — di luar cakupan dokumen ini.

### Logika Fusi Sensor (kunci minimalisasi alarm palsu)

Sesuai proposal: dua tahap keputusan.

1. **Pre-alarm** — cukup salah satu sensor IR melebihi threshold → masuk `PRE_ALARM`. Sistem siaga tapi belum menembak.
2. **Aktivasi** — YOLO mengkonfirmasi api secara visual *dan* `confidence ≥ ambang* → masuk `TRACKING`. Baru di sini pemadaman dimulai.

Sensor IR juga menentukan **prioritas arah tracking**: jika YOLO mendeteksi >1 titik api, titik yang searah dengan sensor IR yang ter-trigger paling kuat diprioritaskan.

```python
# Inti logika fusi di dalam Orchestrator
def _evaluate_fusion(self):
    ir_hot = any(r["triggered"] for r in self._ir_readings.values())
    visual = self._last_detection is not None and \
             self._last_detection["confidence"] >= config.YOLO_CONF_THRESHOLD

    if self._state == State.IDLE and ir_hot:
        self._transition(State.PRE_ALARM)
    elif self._state == State.PRE_ALARM and visual:
        self._transition(State.TRACKING)
        self._bus.publish(events.TRACK_START, {
            "bbox": self._last_detection["bbox"],
            "frame_w": self._last_detection["frame_w"],
            "frame_h": self._last_detection["frame_h"],
        })
    elif self._state == State.PRE_ALARM and not ir_hot:
        self._transition(State.IDLE)   # alarm palsu, batal
```

---

## 6. Interface Tiap Modul

### 6.1 Base Class (kontrak)

```python
# safe/core/interfaces.py
"""
Base class abstrak. Setiap modul nyata maupun fake mengimplementasikan
salah satu dari kelas ini. Orchestrator hanya tahu kontraknya.
"""
from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Kontrak lifecycle dasar untuk semua modul."""

    @abstractmethod
    def start(self) -> None:
        """Inisialisasi hardware / thread. Dipanggil sekali saat boot."""

    @abstractmethod
    def stop(self) -> None:
        """Matikan dengan aman. Dipanggil saat shutdown."""


class BaseSensor(BaseModule):
    """Sensor mempublish pembacaan ke Event Bus secara periodik."""


class BaseDetector(BaseModule):
    """Detektor api. Mempublish fire_detected / fire_cleared."""


class BaseActuator(BaseModule):
    """Aktuator (servo). Subscribe perintah dari bus."""


class BaseAudio(BaseModule):
    """Pembangkit sinyal audio. Subscribe audio_cmd."""
```

### 6.2 IR Sensor (membungkus `IR.py`)

```python
# safe/sensors/ir_sensor.py
"""
IRSensorArray — bungkus driver IR.py menjadi modul Event Bus.
Driver asli (_ir_driver.py = IR.py) tidak diubah.
"""
import threading
import logging
from core.interfaces import BaseSensor
from core import events, config
from sensors import _ir_driver   # = IR.py lama

logger = logging.getLogger(__name__)


class IRSensorArray(BaseSensor):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._running = False
        self._thread = None
        self._channels = None

    def start(self):
        self._channels = _ir_driver.init_sensors()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("IRSensorArray berjalan (%d sensor).", len(self._channels))

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _poll_loop(self):
        while self._running:
            readings = _ir_driver.read_all_sensors(self._channels)
            for i, data in enumerate(readings, start=1):
                self._bus.publish(events.IR_READING, {
                    "sensor_id": i,
                    "voltage": data["voltage"],
                    "triggered": data["voltage"] >= config.IR_THRESHOLD_V,
                })
            _ir_driver.time.sleep(config.IR_READ_INTERVAL)
```

### 6.3 Detector — Fake & Placeholder YOLO

```python
# safe/detection/fake_detector.py
"""
FakeDetector — mensimulasikan output YOLO untuk testing TANPA kamera.
Publish fire_detected dengan bbox dummy sesuai jadwal.
"""
import threading
import logging
from core.interfaces import BaseDetector
from core import events

logger = logging.getLogger(__name__)


class FakeDetector(BaseDetector):
    def __init__(self, event_bus, scripted_events=None):
        self._bus = event_bus
        # daftar (delay_detik, payload) untuk disuntikkan
        self._script = scripted_events or [
            (3.0, {"bbox": [320, 240, 80, 100], "confidence": 0.91,
                   "frame_w": 640, "frame_h": 480}),
        ]
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._run_script, daemon=True).start()
        logger.info("FakeDetector aktif (mode skrip).")

    def stop(self):
        self._running = False

    def _run_script(self):
        import time
        for delay, payload in self._script:
            time.sleep(delay)
            if not self._running:
                return
            self._bus.publish(events.FIRE_DETECTED, payload)
            logger.info("FakeDetector publish fire_detected: %s", payload)
```

```python
# safe/detection/yolo_detector.py
"""
YOLODetector — PLACEHOLDER. Diisi setelah model .pt / ONNX siap.

Kontrak yang HARUS dipenuhi (sama persis dengan FakeDetector):
    publish events.FIRE_DETECTED dengan payload:
        { bbox: [cx, cy, w, h], confidence: float,
          frame_w: int, frame_h: int }
    publish events.FIRE_CLEARED saat api hilang dari frame.

Karena kontraknya identik, mengganti FakeDetector -> YOLODetector
di main.py TIDAK mengubah modul lain sama sekali.
"""
import logging
from core.interfaces import BaseDetector
# from ultralytics import YOLO     # diaktifkan saat implementasi
# import cv2

logger = logging.getLogger(__name__)


class YOLODetector(BaseDetector):
    def __init__(self, event_bus, model_path="models/safe_fire.pt"):
        self._bus = event_bus
        self._model_path = model_path
        # TODO: self._model = YOLO(model_path)
        # TODO: self._cap = cv2.VideoCapture(0)

    def start(self):
        raise NotImplementedError(
            "YOLODetector belum diimplementasikan. "
            "Gunakan FakeDetector untuk sementara."
        )

    def stop(self):
        pass

    # def _inference_loop(self):
    #     while self._running:
    #         ok, frame = self._cap.read()
    #         results = self._model(frame, verbose=False)
    #         ...  # ekstrak bbox + confidence, lalu publish FIRE_DETECTED
```

### 6.4 Tracking Logic (bbox → sudut servo)

```python
# safe/tracking/tracker.py
"""
TrackingLogic — ubah posisi bounding box di frame menjadi sudut servo
absolut (yaw, pitch), lalu publish servo_cmd.

Pendekatan: proportional centering. Error piksel dari pusat frame
dipetakan ke koreksi sudut. Sudut absolut = netral + koreksi terakumulasi.
"""
import logging
from core.interfaces import BaseModule
from core import events, config

logger = logging.getLogger(__name__)


class TrackingLogic(BaseModule):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._active = False
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._bus.subscribe(events.TRACK_START, self._on_start)
        self._bus.subscribe(events.TRACK_STOP, self._on_stop)
        self._bus.subscribe(events.FIRE_DETECTED, self._on_detection)

    def start(self):
        logger.info("TrackingLogic siap.")

    def stop(self):
        self._active = False

    def _on_start(self, data):
        self._active = True
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._on_detection(data)

    def _on_stop(self, data):
        self._active = False

    def _on_detection(self, data):
        """Konversi bbox -> koreksi sudut -> servo_cmd."""
        if not self._active:
            return
        cx, cy, _, _ = data["bbox"]
        fw, fh = data["frame_w"], data["frame_h"]

        # error piksel dari pusat frame, dinormalisasi ke [-1, 1]
        err_x = (cx - fw / 2) / (fw / 2)
        err_y = (cy - fh / 2) / (fh / 2)

        # koreksi proporsional (gain dari config)
        self._yaw   += err_x * config.YAW_GAIN_DEG
        self._pitch += err_y * config.PITCH_GAIN_DEG

        # clamp ke batas fisik
        self._yaw   = max(config.YAW_MIN,   min(config.YAW_MAX,   self._yaw))
        self._pitch = max(config.PITCH_MIN, min(config.PITCH_MAX, self._pitch))

        self._bus.publish(events.SERVO_CMD, {
            "yaw_deg": self._yaw,
            "pitch_deg": self._pitch,
        })

        # beri tahu Orchestrator kalau sudah cukup terpusat
        err_px = ((cx - fw / 2) ** 2 + (cy - fh / 2) ** 2) ** 0.5
        if err_px <= config.TARGET_LOCK_PX:
            self._bus.publish(events.TARGET_LOCKED, {"error_px": err_px})
```

### 6.5 Servo Actuator (membungkus `Servo.py`)

```python
# safe/actuation/servo_actuator.py
"""
ServoActuator — adapter Event Bus -> Dynamixel MX-106 (driver _servo_driver.py).
Driver asli (Servo.py) tidak diubah.

Batas fisik dari proposal:
    Yaw  (ID 1): 0-180°, netral 90°  (90° kiri / 90° kanan)
    Pitch (ID 2): 50-140°, netral 70° (20° atas / 70° bawah)
    * Nilai pitch dikalibrasi ulang setelah perakitan mekanik.
"""
import threading
import logging
from core.interfaces import BaseActuator
from core import events, config
from actuation import _servo_driver as drv   # = Servo.py lama

logger = logging.getLogger(__name__)


class ServoActuator(BaseActuator):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._lock = threading.Lock()   # Dynamixel bus tidak thread-safe
        self._ready = False
        self._port = None
        self._pkt = None
        self._bus.subscribe(events.SERVO_CMD,  self._on_cmd)
        self._bus.subscribe(events.SERVO_HOME, self._on_home)
        self._bus.subscribe(events.SERVO_STOP, self._on_stop)

    def start(self):
        self._port, self._pkt = drv.init_dynamixel()
        for sid in (drv.ID_X, drv.ID_Y):
            drv.set_torque(self._port, self._pkt, sid, 1)
            drv.set_joint_mode(self._port, self._pkt, sid)
        self._go_neutral()
        self._ready = True
        logger.info("ServoActuator siap.")

    def stop(self):
        if self._ready:
            self._go_neutral()
            for sid in (drv.ID_X, drv.ID_Y):
                drv.set_torque(self._port, self._pkt, sid, 0)
            self._port.closePort()
            self._ready = False

    def _on_cmd(self, data):
        if not self._ready:
            return
        yaw = max(config.YAW_MIN,   min(config.YAW_MAX,   float(data["yaw_deg"])))
        pitch = max(config.PITCH_MIN, min(config.PITCH_MAX, float(data["pitch_deg"])))
        with self._lock:
            drv.move_to_angle(self._port, self._pkt, drv.ID_X, yaw)
            drv.move_to_angle(self._port, self._pkt, drv.ID_Y, pitch)

    def _on_home(self, data):
        self._go_neutral()

    def _on_stop(self, data):
        if self._ready:
            with self._lock:
                for sid in (drv.ID_X, drv.ID_Y):
                    drv.set_torque(self._port, self._pkt, sid, 0)

    def _go_neutral(self):
        with self._lock:
            drv.move_to_angle(self._port, self._pkt, drv.ID_X, config.YAW_NEUTRAL)
            drv.move_to_angle(self._port, self._pkt, drv.ID_Y, config.PITCH_NEUTRAL)
```

### 6.6 DAC Audio (membungkus `DAC.py`)

```python
# safe/audio/dac_audio.py
"""
DACAudio — adapter Event Bus -> PCM5102A (driver _dac_driver.py = DAC.py).

PENTING (safety, sesuai catatan proyek):
    - amplitude dibatasi <= AMPLITUDE_MAX_SAFE (limiting perangkat lunak)
    - durasi tiap operasi dibatasi <= AUDIO_MAX_DURATION
    - wajib cooldown setelah operasi (dijaga Orchestrator)
"""
import threading
import logging
from core.interfaces import BaseAudio
from core import events, config
from audio import _dac_driver as drv   # = DAC.py lama

logger = logging.getLogger(__name__)


class DACAudio(BaseAudio):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._playing = False
        self._bus.subscribe(events.AUDIO_CMD,  self._on_cmd)
        self._bus.subscribe(events.AUDIO_STOP, self._on_stop)

    def start(self):
        drv.list_devices()
        logger.info("DACAudio siap.")

    def stop(self):
        self._on_stop({})

    def _on_cmd(self, data):
        freq = float(data.get("freq", config.AUDIO_DEFAULT_FREQ))
        amp = min(float(data.get("amplitude", config.AMPLITUDE_MAX_SAFE)),
                  config.AMPLITUDE_MAX_SAFE)               # hard limit
        dur = min(float(data.get("duration", config.AUDIO_MAX_DURATION)),
                  config.AUDIO_MAX_DURATION)               # hard limit

        def _play():
            self._playing = True
            signal = drv.generate_sine(freq, dur, amplitude=amp)
            drv.play(signal, label=f"Pemadaman {freq} Hz")
            self._playing = False

        threading.Thread(target=_play, daemon=True).start()

    def _on_stop(self, data):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            logger.exception("Gagal menghentikan audio.")
        self._playing = False
```

---

## 7. Alur Eksekusi Lengkap

Urutan kejadian dari api muncul sampai padam:

| # | Aktor | Aksi | Event |
|---|---|---|---|
| 1 | IR Sensor | Baca 5 sensor; satu melebihi threshold | `publish ir_reading` |
| 2 | Orchestrator | Fusi: IR triggered → `PRE_ALARM` | `publish state_changed` |
| 3 | YOLO* | Deteksi api di frame (placeholder) | `publish fire_detected` |
| 4 | Orchestrator | IR + YOLO terkonfirmasi → `TRACKING` | `publish track_start` |
| 5 | Tracking | Hitung error piksel → sudut servo | `publish servo_cmd` |
| 6 | Servo | Gerak ke yaw/pitch (Dynamixel joint mode) | — |
| 7 | Tracking | Target terpusat | `publish target_locked` |
| 8 | Orchestrator | → `EXTINGUISHING` | `publish audio_cmd` |
| 9 | DAC | Mainkan sine 30–60 Hz ke subwoofer | — |
| 10 | Orchestrator | Durasi habis → `EVALUATING` | `publish audio_stop` |
| 11 | Orchestrator | Api masih? ulang ke 5. Padam? → `COOLDOWN` → `IDLE` | `publish state_changed` |

\* Langkah 3 sekarang dijalankan `FakeDetector`; nanti diganti `YOLODetector` tanpa mengubah langkah lain.

---

## 8. Dependency Injection & Bootstrap

Inti testability: `main.py` yang merakit modul. Tukar satu baris untuk ganti fake↔nyata.

```python
# safe/main.py
"""
Bootstrap S.A.F.E — merakit semua modul dan menyuntikkannya ke Orchestrator.

Ganti FakeDetector -> YOLODetector di SATU baris saat YOLO siap.
Tidak ada modul lain yang perlu diubah.
"""
import logging
import signal
import time

from core.event_bus import EventBus
from orchestrator import Orchestrator

from sensors.ir_sensor import IRSensorArray
from detection.fake_detector import FakeDetector     # <-- tukar ke YOLODetector nanti
# from detection.yolo_detector import YOLODetector
from tracking.tracker import TrackingLogic
from actuation.servo_actuator import ServoActuator
from audio.dac_audio import DACAudio

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def build_system(use_fake_detector=True):
    bus = EventBus()

    detector = FakeDetector(bus) if use_fake_detector else None
    # detector = YOLODetector(bus)   # produksi

    modules = [
        IRSensorArray(bus),
        detector,
        TrackingLogic(bus),
        ServoActuator(bus),
        DACAudio(bus),
    ]
    orchestrator = Orchestrator(bus)
    return bus, orchestrator, modules


def main():
    bus, orchestrator, modules = build_system(use_fake_detector=True)

    bus.start()
    orchestrator.start()
    for m in modules:
        if m:
            m.start()

    logging.info("S.A.F.E berjalan. Ctrl+C untuk berhenti.")

    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    try:
        while not stop["flag"]:
            time.sleep(0.5)
    finally:
        for m in modules:
            if m:
                m.stop()
        orchestrator.stop()
        bus.stop()
        logging.info("S.A.F.E dimatikan dengan aman.")


if __name__ == "__main__":
    main()
```

---

## 9. Strategi Testing

Tiga lapis, dari murah ke mahal:

### Lapis 1 — Unit (tanpa hardware, paling cepat)
Tiap modul diuji sendiri dengan bus dummy. Contoh: konversi `TrackingLogic` dari bbox ke sudut.

```python
# tests/test_tracker.py
from core.event_bus import EventBus
from core import events
from tracking.tracker import TrackingLogic


def test_bbox_tengah_tidak_menggerakkan_servo():
    bus = EventBus()
    captured = []
    bus.subscribe(events.SERVO_CMD, lambda d: captured.append(d))
    bus.start()

    tracker = TrackingLogic(bus)
    tracker.start()
    # bbox tepat di tengah frame 640x480
    bus.publish(events.TRACK_START, {
        "bbox": [320, 240, 50, 50], "frame_w": 640, "frame_h": 480})

    import time; time.sleep(0.1)
    bus.stop()
    # servo harus tetap di netral (error nol)
    assert captured[-1]["yaw_deg"] == 90.0
    assert captured[-1]["pitch_deg"] == 70.0
```

### Lapis 2 — Integrasi (rantai penuh, masih tanpa hardware)
`FakeDetector` + bus dummy + servo/audio versi mock. Verifikasi: api palsu masuk → urutan event benar → state machine berakhir di `IDLE`.

```python
# tests/test_integration.py
# Suntik fire_detected palsu, pastikan Orchestrator mencapai EXTINGUISHING
def test_alur_deteksi_sampai_pemadaman(monkeypatch):
    ...  # rakit sistem dengan FakeDetector + servo mock
    # assert state berurutan: IDLE -> PRE_ALARM -> TRACKING -> EXTINGUISHING
```

### Lapis 3 — Hardware-in-the-loop (di Pi, satu modul per waktu)
- Servo saja: jalankan `python -m actuation.servo_actuator` lalu publish `servo_cmd` manual.
- Audio saja: publish `audio_cmd { freq: 45, amplitude: 0.5, duration: 2 }`.
- IR saja: nyalakan `IRSensorArray`, dekatkan sumber panas, amati log `ir_reading`.

Karena Event Bus memisahkan modul, Anda bisa menyuntik event palsu dari shell untuk menguji aktuator **tanpa** kamera, YOLO, atau api sungguhan.

---

## 10. Catatan Implementasi & Keamanan

**Servo — joint mode, sudut absolut.** Tracking mengirim sudut absolut hasil koreksi proporsional, bukan kecepatan. Lebih mudah dikontrol dan aman. Konstanta netral (`YAW_NEUTRAL=90`, `PITCH_NEUTRAL=70`) **wajib dikalibrasi ulang** setelah perakitan mekanik.

**Audio — limiting wajib di perangkat lunak.** Konfigurasi DVC paralel 2Ω menghasilkan daya melebihi rating program subwoofer. Karena itu `DACAudio` memberlakukan hard limit pada `amplitude` (`AMPLITUDE_MAX_SAFE`) dan `duration` (`AUDIO_MAX_DURATION`), serta Orchestrator menegakkan cooldown via state `COOLDOWN`. Jangan pernah lewati batas ini di kode.

**Isolasi daya servo.** Dynamixel MX-106 disuplai 12V terpisah, bukan dari rail GPIO Pi. Ini persyaratan wiring, bukan sekadar saran.

**Thread-safety Dynamixel.** Bus RS485 tidak boleh diakses dua thread sekaligus — `ServoActuator` menjaganya dengan `threading.Lock`.

**Single-writer Event Bus.** Satu worker memproses event berurutan, jadi handler tidak perlu lock antar event. Komputasi berat tetap di thread modul masing-masing.

---

## 11. Antarmuka Web (Dashboard)

Web adalah **modul opsional di tepi sistem**. Ia tidak mengubah inti: hanya satu modul (`WebBridge`) yang subscribe/publish ke Event Bus, persis seperti modul lain. Kalau web dimatikan, sistem berjalan penuh tanpanya.

### 11.1 Arsitektur

```
                       ┌────────────────────────────────┐
                       │          EVENT BUS              │
                       └──┬──────────┬──────────┬────────┘
              frame_update│   state_changed     │servo_jog / set_mode
              (dari YOLO) │   mode_changed       │(dari WebBridge)
                          ▼          ▼           ▲
                    ┌─────────────────────────────────┐
                    │           WebBridge             │
                    │  FastAPI (thread terpisah)      │
                    └───┬──────────┬──────────┬───────┘
              MJPEG     │   SSE    │   POST   │
           /stream      │ /events  │ /cmd/*   │
                        ▼          ▼          ▼
                    ┌─────────────────────────────────┐
                    │       Browser (dashboard)       │
                    │  • live stream + bbox deteksi   │
                    │  • status state real-time       │
                    │  • toggle AUTO / MANUAL         │
                    │  • joystick servo               │
                    └─────────────────────────────────┘
```

Tiga jalur, masing-masing protokol yang paling cocok:

| Jalur | Protokol | Arah | Isi |
|---|---|---|---|
| `/stream` | MJPEG | server → browser | frame kamera ter-annotate (dari `frame_update`) |
| `/events` | SSE | server → browser | perubahan state, mode, hasil deteksi |
| `/cmd/*`, `/heartbeat` | HTTP POST | browser → server | joystick, toggle mode, heartbeat |

Prinsip yang dipertahankan: HTTP hanya di tepi. Jalur kritis (servo loop, audio) tidak menyentuh HTTP. Joystick mem-*publish* event ke bus dan langsung kembali — eksekusi servo tetap lewat jalur internal yang sama.

### 11.2 Stream Kamera

Stream **hanya berasal dari YOLO**. Modul deteksi yang sudah memegang frame kamera mem-publish `frame_update {jpeg}` (frame yang sudah digambari bounding box, lalu di-encode JPEG). WebBridge menyimpan frame terakhir dan menyajikannya sebagai MJPEG.

Konsekuensi: kamera diakses **satu proses saja** (YOLO), tidak ada rebutan device. Selama `YOLODetector` belum aktif, `frame_update` tidak pernah terbit, dan `/stream` menampilkan placeholder "kamera tidak aktif". Saat YOLO siap, stream otomatis hidup tanpa mengubah WebBridge.

Penyisipan di `YOLODetector` nanti cukup beberapa baris di loop inferensi:

```python
# di dalam _inference_loop YOLODetector (saat diimplementasikan)
annotated = results[0].plot()          # frame + bounding box
ok, buf = cv2.imencode(".jpg", annotated)
if ok:
    self._bus.publish(events.FRAME_UPDATE, {"jpeg": buf.tobytes()})
```

### 11.3 WebBridge

```python
# safe/web/web_bridge.py
"""
WebBridge — antarmuka web opsional. Modul tepi: hanya subscribe/publish
ke Event Bus. Tidak memanggil modul lain langsung.

Menyediakan:
    GET  /             -> halaman dashboard (static/index.html)
    GET  /stream       -> MJPEG live kamera (dari frame_update)
    GET  /events       -> SSE status (state, mode, deteksi)
    POST /cmd/mode     -> { mode: "auto"|"manual" }  -> set_mode
    POST /cmd/jog      -> { d_yaw, d_pitch }         -> servo_jog
    POST /heartbeat    -> tanda UI masih aktif (cegah balik ke AUTO)
"""
import json
import time
import queue
import threading
import logging

from core.interfaces import BaseModule
from core import events, config

logger = logging.getLogger(__name__)


class WebBridge(BaseModule):
    def __init__(self, event_bus, host="0.0.0.0", port=8000):
        self._bus = event_bus
        self._host = host
        self._port = port

        self._latest_jpeg: bytes | None = None
        self._sse_clients: list[queue.Queue] = []
        self._last_heartbeat = 0.0
        self._mode = "auto"
        self._running = False

        # terima update dari sistem
        self._bus.subscribe(events.FRAME_UPDATE,  self._on_frame)
        self._bus.subscribe(events.STATE_CHANGED, self._on_state)
        self._bus.subscribe(events.MODE_CHANGED,  self._on_mode)
        self._bus.subscribe(events.FIRE_DETECTED, self._on_detection)

    # ---------- lifecycle ----------
    def start(self):
        self._running = True
        threading.Thread(target=self._serve, daemon=True).start()
        threading.Thread(target=self._heartbeat_watch, daemon=True).start()
        logger.info("WebBridge di http://%s:%d", self._host, self._port)

    def stop(self):
        self._running = False

    # ---------- handler dari bus ----------
    def _on_frame(self, data):
        self._latest_jpeg = data.get("jpeg")

    def _on_state(self, data):
        self._push_sse({"type": "state", "value": data["new"]})

    def _on_mode(self, data):
        self._mode = data["mode"]
        self._push_sse({"type": "mode", "value": data["mode"]})

    def _on_detection(self, data):
        self._push_sse({"type": "detection",
                        "bbox": data["bbox"],
                        "confidence": data["confidence"]})

    def _push_sse(self, payload: dict):
        msg = f"data: {json.dumps(payload)}\n\n"
        for q in list(self._sse_clients):
            q.put(msg)

    # ---------- heartbeat: balik ke AUTO bila UI hilang ----------
    def _heartbeat_watch(self):
        while self._running:
            if (self._mode == "manual" and
                    time.time() - self._last_heartbeat
                    > config.WEB_HEARTBEAT_TIMEOUT):
                logger.info("Heartbeat UI hilang — kembali ke AUTO.")
                self._bus.publish(events.SET_MODE, {"mode": "auto"})
            time.sleep(1.0)

    # ---------- server FastAPI ----------
    def _serve(self):
        import uvicorn
        from fastapi import FastAPI, Request
        from fastapi.responses import (
            StreamingResponse, HTMLResponse, JSONResponse)
        from pathlib import Path

        app = FastAPI()
        static_dir = Path(__file__).parent / "static"

        @app.get("/", response_class=HTMLResponse)
        def index():
            return (static_dir / "index.html").read_text()

        @app.get("/stream")
        def stream():
            def gen():
                placeholder = b""  # bisa diisi gambar "kamera tidak aktif"
                while self._running:
                    frame = self._latest_jpeg or placeholder
                    if frame:
                        yield (b"--frame\r\n"
                               b"Content-Type: image/jpeg\r\n\r\n"
                               + frame + b"\r\n")
                    time.sleep(0.05)   # ~20 fps maksimum
            return StreamingResponse(
                gen(),
                media_type="multipart/x-mixed-replace; boundary=frame")

        @app.get("/events")
        def events_sse():
            q: queue.Queue = queue.Queue()
            self._sse_clients.append(q)

            def gen():
                try:
                    while self._running:
                        yield q.get()
                finally:
                    self._sse_clients.remove(q)
            return StreamingResponse(gen(), media_type="text/event-stream")

        @app.post("/cmd/mode")
        async def set_mode(req: Request):
            body = await req.json()
            mode = body.get("mode", "auto")
            if mode == "manual":
                self._last_heartbeat = time.time()
            self._bus.publish(events.SET_MODE, {"mode": mode})
            return JSONResponse({"ok": True, "mode": mode})

        @app.post("/cmd/jog")
        async def jog(req: Request):
            body = await req.json()
            self._bus.publish(events.SERVO_JOG, {
                "d_yaw":   float(body.get("d_yaw", 0.0)),
                "d_pitch": float(body.get("d_pitch", 0.0)),
            })
            return JSONResponse({"ok": True})

        @app.post("/heartbeat")
        def heartbeat():
            self._last_heartbeat = time.time()
            return JSONResponse({"ok": True})

        uvicorn.run(app, host=self._host, port=self._port, log_level="warning")
```

### 11.4 Perubahan kecil di modul lain

Web menambah dua tanggung jawab kecil — tetap lewat event, inti tidak berubah.

**Orchestrator** menangani `set_mode` dan menegakkan jeda fusi saat MANUAL:

```python
# tambahan di Orchestrator.__init__
self._bus.subscribe(events.SET_MODE, self._on_set_mode)
self._mode = "auto"

def _on_set_mode(self, data):
    mode = data.get("mode", "auto")
    self._mode = mode
    if mode == "manual":
        self._transition(State.MANUAL)
    else:
        self._transition(State.IDLE)   # kembali siaga otomatis
    self._bus.publish(events.MODE_CHANGED, {"mode": mode})

# di _evaluate_fusion(), baris paling awal:
def _evaluate_fusion(self):
    if self._mode == "manual":
        return                         # fusi dijeda; event tetap ter-cache
    ...
```

**ServoActuator** menangani joystick inkremental (`servo_jog`) — menambah delta ke sudut sekarang lalu clamp:

```python
# tambahan di ServoActuator.__init__
self._bus.subscribe(events.SERVO_JOG, self._on_jog)
self._cur_yaw = config.YAW_NEUTRAL
self._cur_pitch = config.PITCH_NEUTRAL

def _on_jog(self, data):
    if not self._ready:
        return
    self._cur_yaw   = max(config.YAW_MIN,   min(config.YAW_MAX,
                          self._cur_yaw   + float(data["d_yaw"])))
    self._cur_pitch = max(config.PITCH_MIN, min(config.PITCH_MAX,
                          self._cur_pitch + float(data["d_pitch"])))
    with self._lock:
        drv.move_to_angle(self._port, self._pkt, drv.ID_X, self._cur_yaw)
        drv.move_to_angle(self._port, self._pkt, drv.ID_Y, self._cur_pitch)
```

Catatan: agar `servo_cmd` (tracking otomatis) dan `servo_jog` (manual) tidak saling menimpa posisi, keduanya sebaiknya berbagi state sudut yang sama di `ServoActuator`. Saat implementasi, satukan `_cur_yaw/_cur_pitch` dengan variabel yang dipakai `_on_cmd`.

### 11.5 Konfigurasi tambahan

```python
# tambahan untuk config.py
# ======================= WEB =======================
WEB_HOST              = "0.0.0.0"
WEB_PORT              = 8000
WEB_HEARTBEAT_TIMEOUT = 5.0   # detik; UI dianggap hilang -> balik ke AUTO
WEB_JOG_STEP_DEG      = 3.0   # derajat per input joystick (dipakai frontend)
```

### 11.6 Frontend (kerangka contoh)

`web/static/index.html` — contoh minimal: stream, status, toggle mode, joystick. Frontend final bisa Anda kembangkan sendiri; yang penting endpoint-nya tetap.

```html
<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <title>S.A.F.E Dashboard</title>
  <style>
    body { font-family: system-ui; margin: 2rem; }
    #stream { width: 640px; max-width: 100%; background:#111; border-radius:8px; }
    .row { display: flex; gap: 2rem; flex-wrap: wrap; align-items: flex-start; }
    .pad { display: grid; grid-template-columns: repeat(3, 56px);
           gap: 6px; margin-top: 1rem; }
    button { padding: 14px; font-size: 18px; border-radius: 8px; cursor: pointer; }
    .status { font-size: 14px; line-height: 1.8; }
    .badge { padding: 2px 10px; border-radius: 6px; background:#eee; }
  </style>
</head>
<body>
  <h1>S.A.F.E Dashboard</h1>
  <div class="row">
    <div>
      <img id="stream" src="/stream" alt="kamera tidak aktif">
    </div>
    <div>
      <div class="status">
        State : <span id="state" class="badge">-</span><br>
        Mode  : <span id="mode" class="badge">auto</span><br>
        Deteksi: <span id="det" class="badge">-</span>
      </div>

      <p>
        <button onclick="setMode('auto')">AUTO</button>
        <button onclick="setMode('manual')">MANUAL</button>
      </p>

      <!-- Joystick sederhana (manual saja) -->
      <div class="pad">
        <span></span>
        <button onclick="jog(0, -STEP)">▲</button>
        <span></span>
        <button onclick="jog(-STEP, 0)">◄</button>
        <button onclick="jog(0, 0)">■</button>
        <button onclick="jog(STEP, 0)">►</button>
        <span></span>
        <button onclick="jog(0, STEP)">▼</button>
        <span></span>
      </div>
    </div>
  </div>

<script>
const STEP = 3.0;                 // = WEB_JOG_STEP_DEG
let manual = false;

// --- terima status real-time via SSE ---
const es = new EventSource("/events");
es.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.type === "state") document.getElementById("state").textContent = m.value;
  if (m.type === "mode")  {
    document.getElementById("mode").textContent = m.value;
    manual = (m.value === "manual");
  }
  if (m.type === "detection")
    document.getElementById("det").textContent =
      "conf " + m.confidence.toFixed(2);
};

async function setMode(mode) {
  await fetch("/cmd/mode", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ mode })
  });
}

async function jog(d_yaw, d_pitch) {
  await fetch("/cmd/jog", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ d_yaw, d_pitch })
  });
}

// --- heartbeat: kabari server UI masih aktif (tiap 2 dtk saat manual) ---
setInterval(() => {
  if (manual) fetch("/heartbeat", { method: "POST" });
}, 2000);
</script>
</body>
</html>
```

### 11.7 Memasang di main.py

Satu blok tambahan, sisanya tak berubah:

```python
from web.web_bridge import WebBridge

# di build_system(), setelah modul lain dibuat:
web = WebBridge(bus, host=config.WEB_HOST, port=config.WEB_PORT)
modules.append(web)
```

### 11.8 Testing web

- **Tanpa hardware & tanpa YOLO**: jalankan sistem dengan `FakeDetector`. Buka `http://<ip-pi>:8000`. Status state berubah saat `FakeDetector` menyuntik api palsu. `/stream` menampilkan placeholder (belum ada `frame_update`).
- **Joystick**: toggle MANUAL, tekan tombol arah, amati log `servo_jog` (atau gerakan servo bila hardware terpasang).
- **Heartbeat**: masuk MANUAL, tutup tab browser, tunggu `WEB_HEARTBEAT_TIMEOUT` detik — sistem harus otomatis kembali ke AUTO (cek log `mode_changed`).
- **Stream nyata**: aktif otomatis begitu `YOLODetector` mem-publish `frame_update`.

---

## 12. Roadmap Integrasi

| Tahap | Pekerjaan | Status |
|---|---|---|
| 1 | Salin `IR.py`, `Servo.py`, `DAC.py` → `_*_driver.py` | Driver sudah ada |
| 2 | Implementasi `EventBus`, `interfaces`, `events`, `config` | Spesifikasi siap |
| 3 | Bungkus tiap driver dengan adapter modul | Spesifikasi siap |
| 4 | Implementasi `Orchestrator` + state machine | Spesifikasi siap |
| 5 | `FakeDetector` + test integrasi tanpa hardware | Spesifikasi siap |
| 6 | Hardware-in-the-loop per modul di Pi 5 | Menunggu rakitan |
| 7 | Latih YOLOv8 Nano, ekspor model | Belum mulai |
| 8 | Implementasi `YOLODetector`, ganti `FakeDetector` di `main.py` | Placeholder siap |
| 9 | Antarmuka web: `WebBridge` + dashboard (stream, status, joystick, mode AUTO/MANUAL) | Spesifikasi siap |
| 10 | Lapisan opsional lain: Telegram, logging CSV, PDF | Belum mulai |

Catatan: lapisan opsional (tahap 9–10) ditempel di *tepi* sistem — modul baru yang subscribe `state_changed` / `frame_update` / `extinguish_done`, tanpa menyentuh inti. Web (tahap 9) hanya butuh `YOLODetector` aktif agar stream kamera hidup; status, mode, dan joystick sudah berfungsi tanpa YOLO.

---

*Dokumen ini adalah blueprint arsitektur. Snippet kode adalah spesifikasi referensi, bukan implementasi final — sesuaikan saat pengembangan.*