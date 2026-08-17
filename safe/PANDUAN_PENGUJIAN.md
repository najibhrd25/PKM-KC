# Panduan Pengujian & Troubleshooting S.A.F.E.

Panduan praktis untuk menguji sistem terintegrasi di `safe/` — dari modul
terkecil sampai integrasi penuh — beserta pemecahan masalah tiap subsistem.
Baca `DOKUMENTASI_SISTEM.md` dulu untuk gambaran arsitektur.

> **Filosofi:** uji **dari bawah ke atas**. Pastikan tiap driver hardware mentah
> bekerja → uji logika tanpa hardware → uji tiap adapter lewat Event Bus →
> baru integrasi penuh. Jangan lompat ke sistem penuh sebelum lapisan bawah lolos.

```
        ┌─────────────────────────────┐
Level 4 │  Integrasi penuh (api nyata) │   paling akhir
        ├─────────────────────────────┤
Level 3 │  Adapter via Event Bus       │   inject event manual
        ├─────────────────────────────┤
Level 2 │  Logika tanpa hardware       │   FakeDetector + unit test
        ├─────────────────────────────┤
Level 1 │  Driver hardware individual  │   console __main__
        ├─────────────────────────────┤
Level 0 │  Cek lingkungan & dependensi │   paling awal
        └─────────────────────────────┘
```

---

## 0. Prasyarat & Cek Lingkungan

**Dependensi per subsistem:**

| Subsistem | Paket | Cek cepat |
|---|---|---|
| Deteksi | `ultralytics`, `opencv-python`, `picamera2` | `python3 -c "import ultralytics, cv2, picamera2"` |
| Servo | `dynamixel-sdk` | `python3 -c "import dynamixel_sdk"` |
| IR | `adafruit-circuitpython-ads1x15` | `python3 -c "import board, adafruit_ads1x15.ads1115"` |
| Audio | `sounddevice`, `numpy` | `python3 -c "import sounddevice, numpy"` |
| Web | `fastapi`, `uvicorn` | `python3 -c "import fastapi, uvicorn"` |

**Cek antarmuka hardware Pi:**
```bash
ls -l /dev/ttyAMA0          # UART servo (butuh dtparam=uart0=on)
i2cdetect -y 1              # harus muncul alamat 48 dan 49 (ADS1115)
aplay -l                    # harus muncul card sndrpihifiberry (PCM5102A)
libcamera-hello --list-cameras   # kamera CSI terdeteksi
```

**Cek kode (tanpa hardware) — jalankan dari dalam `safe/`:**
```bash
cd safe
python3 -m py_compile core/*.py *.py sensors/*.py detection/*.py \
        tracking/*.py actuation/*.py audio/*.py web/*.py && echo "COMPILE OK"
python3 -c "import main; b,o,m=main.build_system(True, True); \
        print([type(x).__name__ for x in m]); print('BUILD OK')"
```
`build_system` hanya meng-*konstruksi* modul (tidak menyentuh hardware), jadi aman
sebagai smoke-test wiring.

---

## Dua Alat Bantu Uji

Simpan kedua skrip ini di `safe/` — dipakai berulang di Level 2–4.

### `monitor_bus.py` — intip semua lalu-lintas event
```python
"""Bangun sistem + cetak SEMUA event yang lewat di bus. Ctrl+C untuk berhenti."""
import time, main
from core import events

bus, orch, mods = main.build_system(use_fake_detector=True, use_web=False)

# subscribe catch-all ke seluruh konstanta event
names = [v for k, v in vars(events).items() if k.isupper() and isinstance(v, str)]
for n in names:
    bus.subscribe(n, (lambda nm: (lambda d: print(f"  [{nm}] {d}")))(n))

bus.start(); orch.start()
for m in mods: m.start()
print(">>> monitor aktif. Ctrl+C untuk stop.")
try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    for m in reversed(mods): m.stop()
    orch.stop(); bus.stop()
```

### `inject.py` — suntik event manual ke sistem
```python
"""Suntik event dari terminal untuk uji reaksi modul (hardware-in-the-loop).
Contoh: menyalakan tracking tanpa kamera, memicu audio, dsb."""
import time, main
from core import events

bus, orch, mods = main.build_system(use_fake_detector=True, use_web=False)
bus.subscribe(events.STATE_CHANGED, lambda d: print("STATE:", d))
bus.start(); orch.start()
for m in mods: m.start()

# --- contoh: paksa siklus deteksi tanpa kamera ---
for i in range(1, 6):                       # 5 sensor, sensor 4 "panas"
    bus.publish(events.IR_READING, {"sensor_id": i, "raw": 3000 if i == 4 else 100,
                "voltage": 2.0 if i == 4 else 0.1, "triggered": i == 4})
time.sleep(0.5)
bus.publish(events.FIRE_DETECTED, {"bbox": [320, 240, 80, 100],
            "confidence": 0.91, "frame_w": 640, "frame_h": 480})
time.sleep(0.5)
bus.publish(events.TARGET_LOCKED, {"error_px": 10.0})
time.sleep(2)

for m in reversed(mods): m.stop()
orch.stop(); bus.stop()
```
> ⚠️ `inject.py` menjalankan **modul asli** — jika `ServoActuator`/`DACAudio` start
> sukses, servo akan **bergerak** dan audio akan **berbunyi**. Untuk uji logika murni,
> lihat Level 2 (jangan start modul hardware).

---

## Level 1 — Uji Driver Hardware Individual

Tiap driver punya console `__main__` mandiri. **Jangan** jalankan dua program yang
membuka perangkat sama (`/dev/ttyAMA0` atau kamera) bersamaan.

### IR — `python3 sensors/_ir_driver.py`
- **Harus:** tabel `raw` & `voltage` 5 sensor ter-update tiap 0.5 dtk.
- **Uji:** dekatkan sumber panas → `raw` sensor terkait naik tajam.
- **Amati untuk kalibrasi:** sensor mana naik saat api di **kiri** vs **kanan**
  (dipakai menyetel `IR_REVERSE`).

### Servo — `python3 actuation/_servo_driver.py`
- **Harus:** "Port dibuka", "Baudrate diset", lalu scan menemukan `[1, 2]`.
- **Uji:** ketik `1 180` lalu `2 180` (posisi tengah), lalu `1 135` / `1 225` (batas).
- **Format:** `<id> <sudut 0-360>`, `exit` untuk keluar.

### DAC — `python3 audio/_dac_driver.py`
- **Harus:** daftar audio device muncul (cari `snd_rpi_hifiberry_dac` = index 0).
- **Uji:** `f 45` lalu `a 0.3` lalu Enter → dengar pulsa 45 Hz. **Mulai amplitudo kecil.**
- **Perintah:** `f <hz>`, `a <amp>`, `n <siklus>`, `p`/Enter (picu), `exit`.

---

## Level 2 — Uji Logika Tanpa Hardware

### 2a. Jalankan sistem dengan FakeDetector
```bash
python3 main.py    # default use_fake_detector=True
```
- **Harus (log):** `FakeDetector aktif` → setelah 3 dtk `fire_detected` → orchestrator
  `STATE: idle -> pre_alarm -> tracking`.
- Di mesin **tanpa hardware IR/servo**, `IRSensorArray.start()`/`ServoActuator.start()`
  akan gagal (butuh `board`/`dynamixel_sdk`). Untuk murni menguji **otak**, pakai 2b.

### 2b. Unit test orchestrator (fusi + state machine)
Uji siklus penuh dan fallback ir-seek **tanpa modul hardware apa pun** (hanya
`core/` + `orchestrator.py`). Pola tervalidasi:
```python
import time
from core import config
config.AUDIO_MAX_DURATION = 0.5; config.EVAL_RECHECK_DELAY = 0.2
config.AUDIO_COOLDOWN = 0.5
from core.event_bus import EventBus
from core import events
from orchestrator import Orchestrator

states = []
bus = EventBus(); orch = Orchestrator(bus)
bus.subscribe(events.STATE_CHANGED, lambda d: states.append(d["new"]))
bus.start(); orch.start()

for i in range(1, 6):
    bus.publish(events.IR_READING, {"sensor_id": i, "raw": 3000 if i == 4 else 100,
                "voltage": 2.0 if i == 4 else 0.1, "triggered": i == 4})
time.sleep(0.3)
bus.publish(events.FIRE_DETECTED, {"bbox": [320,240,80,100], "confidence": 0.91,
            "frame_w": 640, "frame_h": 480})
time.sleep(0.3)
bus.publish(events.TARGET_LOCKED, {"error_px": 10.0})
time.sleep(0.3)
bus.publish(events.FIRE_CLEARED, {})
time.sleep(1.8)
orch.stop(); bus.stop()
print(states)
# Harapan: ['pre_alarm','tracking','extinguishing','evaluating','cooldown','idle']
```

### 2b-bis. Unit test per `DETECT_MODE`
Sama seperti 2b tapi `Orchestrator(bus, detect_mode=...)`. Hanya butuh `core/` +
`orchestrator.py`, jadi jalan di mesin mana pun.

```python
def sweep(bus, raws):                       # satu sapuan penuh 5 kanal
    for i, r in enumerate(raws, 1):
        bus.publish(events.IR_READING, {"sensor_id": i, "raw": r,
                    "voltage": r/1000, "triggered": False})
    time.sleep(0.12)

HOT_LEFT   = [3000, 10, 11, 10, 13]         # ir_x = -1.0
HOT_CENTER = [10, 12, 3000, 10, 13]         # ir_x =  0.0
COLD       = [10, 12, 11, 10, 13]
```

| Mode | Aksi | Harapan `states` |
|---|---|---|
| `camera` | sapuan `HOT_LEFT` saja | `[]` — IR diabaikan, tak ada `servo_jog` |
| `camera` | `fire_detected` conf `0.5` | `[]` — di bawah `YOLO_CONF_THRESHOLD` |
| `camera` | `fire_detected` conf `0.9` | `['tracking']` — **langsung**, tanpa `pre_alarm` |
| `ir` | `fire_detected` conf `0.99` | `[]` — kamera diabaikan |
| `ir` | sapuan `HOT_LEFT` | `['tracking']`; `track_start` **tidak** terbit |
| `ir` | sapuan `HOT_LEFT` kedua | `servo_jog` `d_yaw < 0`, `d_pitch == 0`, state tetap `tracking` |
| `ir` | ≥3 sapuan `HOT_CENTER` | `[...,'extinguishing']` + `audio_cmd` |
| `ir` | sapuan `COLD` saat tracking | `[...,'idle']` |
| `ir` | `COLD` selama pemadaman | `['tracking','extinguishing','evaluating','cooldown','idle']` |
| `fusion` | seperti 2b | tidak berubah dari sebelumnya (regresi) |
| `"kamera"` (typo) | konstruksi Orchestrator | `WARNING ... tidak dikenal -> pakai 'fusion'` |

Dua hal yang mudah salah dan wajib ikut dicek:
- **Tidak ada state berkedip** di mode `ir` saat titik panas berpindah sensor.
  Kalau muncul `idle` di tengah `tracking`, keputusan tidak lagi dibatasi ke akhir
  sapuan (`sensor_id == N_IR`) dan `servo_home` akan merusak bidikan.
- **`track_start` tidak boleh terbit** di mode `ir`. Kalau terbit, `TrackingLogic`
  ikut menulis `servo_cmd` dan bentrok dengan jog IR.

### 2c. Unit test Scanner
Set `config.SCAN_GRACE_SEC` kecil, cek Scanner mem-publish `servo_cmd` menyapu naik
dari netral saat IDLE, dan **berhenti** saat `state_changed` ke non-IDLE.

---

## Level 3 — Uji Adapter via Event Bus

Uji tiap adapter merespons event dengan benar. Pakai `monitor_bus.py` /
`inject.py`. Contoh cek per subsistem:

| Uji | Publish | Reaksi yang benar |
|---|---|---|
| Servo bergerak | `servo_cmd {yaw_deg:200, pitch_deg:165}` | kedua servo pindah, tidak ada error di log |
| Servo home | `servo_home {}` | kembali ke 180°/180° |
| Servo jog | `servo_jog {d_yaw:5, d_pitch:0}` | yaw bertambah 5° dari posisi terakhir |
| Audio | `audio_cmd {freq:45, amplitude:0.3, duration:1.0}` | bunyi 1 dtk, lalu senyap |
| Audio stop | `audio_stop {}` saat berbunyi | suara langsung berhenti |
| IR live | (start `IRSensorArray`) | aliran `ir_reading` per sensor tiap 0.2 dtk |

> **Uji clamp keamanan audio:** kirim `audio_cmd {amplitude:5.0, duration:999}`.
> DACAudio **harus** memutar dengan amp ≤ `0.855` dan durasi ≤ `30` dtk (di-clamp,
> bukan nilai mentah).

---

## Level 4 — Uji Integrasi Penuh (api nyata)

Urutan disarankan (bertahap, satu variabel per langkah):

1. **Deteksi saja** — `use_fake_detector=False`, `use_web=True`, buka
   `http://<ip-pi>:8000/`. Nyalakan/tunjukkan api → kotak "api" muncul di `/stream`,
   log `fire_detected` mengalir; jauhkan api → `fire_cleared`.
2. **Tracking** — biarkan servo aktif. Api nyata → turret memusat (closed-loop) →
   log `target_locked`. Jika turret **menjauh** dari target, lihat troubleshooting servo.

   **Kalibrasi arah putar dulu, sebelum yang lain.** Masuk MANUAL, tekan joystick
   kanan lalu bawah. Turret harus ikut ke kanan/bawah; kalau tidak, set
   `YAW_INVERT`/`PITCH_INVERT = True` dan restart. Konvensi sistem: *sudut naik =
   kanan/bawah*, dipakai kamera, IR, dan joystick sekaligus — jadi kalau
   joystick benar, ketiganya benar. Detail: DOKUMENTASI §8b.
3. **Fusi** — kalibrasi `IR_REVERSE` (api kiri harus `ir_x<0`); pastikan `pre_alarm`
   → `tracking` hanya saat IR panas **dan** kamera yakin.
4. **Pemadaman** — target terkunci → `extinguishing` (`audio_cmd`). **Uji di area aman,
   amplitudo terkendali.** Setelah `AUDIO_MAX_DURATION` → `evaluating` → `cooldown`.
5. **Scanning** — tanpa api > `SCAN_GRACE_SEC` (3 dtk) → turret menyapu raster;
   taruh api di tepi → berpindah ke `tracking`.

### Uji per `DETECT_MODE` di hardware
Ganti `DETECT_MODE` di `core/config.py` (atau argumen `build_system`), **restart**,
dan pastikan log boot menyebut mode yang benar: `Orchestrator berjalan. Deteksi: ...`.

Untuk langkah 1–2 tiap mode, set sementara `config.AMPLITUDE_MAX_SAFE = 0` supaya
turret tetap bergerak tanpa audio menyala.

- **`fusion` (regresi — lulus dulu sebelum yang lain).** Ulangi langkah 1–5 di atas.
  Urutan state harus persis seperti sebelum ada flag ini.
- **`camera`.** Tutup/lepas sensor IR sehingga tidak pernah panas. Tunjukkan api:
  1. `idle -> tracking` **langsung**, tanpa `pre_alarm`.
  2. Turret memusat seperti biasa (`TrackingLogic`), lalu `target_locked`.
  3. Panas tanpa api (mis. solder) **tidak** memicu apa pun.
- **`ir`.** Tutup lensa kamera dan pastikan tak ada `fire_detected` di log.
  Dekatkan sumber panas di sisi **kiri** array:
  1. `idle -> tracking`.
  2. Yaw bergeser ke arah panas dengan **halus** — bukan langsung mentok ke
     135°/225°. Kalau mentok, turunkan `IR_JOG_HZ`/`IR_TRACK_YAW_GAIN`.
  3. Pitch **tidak boleh** berubah (array IR tidak punya info elevasi).
  4. Badge state **tidak berkedip** ke `idle` saat titik panas berpindah sensor.
  5. Setelah terpusat `IR_LOCK_COUNT` sapuan → `tracking -> extinguishing`.
  6. Jauhkan sumber panas → `evaluating -> cooldown -> idle` (tanpa `fire_cleared`
     kamera sama sekali — status padam murni dari IR).

  Kalibrasi `IR_REVERSE` lebih kritis di mode ini daripada di `fusion`: kalau
  terbalik, turret akan menjauh dari sumber panas sampai mentok batas yaw.

---

## Uji Dashboard Web

```python
# di main.py:
build_system(use_fake_detector=False, use_web=True)
```
Buka `http://<ip-pi>:8000/`, lalu:
- **Stream:** video live tampil (dengan YOLODetector; kosong bila FakeDetector).
- **Badge state/mode:** berubah mengikuti `state_changed` via SSE.
- **Badge "Logika deteksi":** menampilkan mode aktif dari `GET /config`
  (`IR + kamera` / `kamera saja` / `IR saja`). Read-only — ganti mode = restart.
  Stream video dan bar IR harus tetap hidup di **semua** mode.
- **AUTO/MANUAL:** klik MANUAL → fusi berhenti (state `manual`), tombol jog aktif.
- **Jog:** panah menggerakkan servo (hanya di MANUAL).
- **Heartbeat:** tutup tab saat MANUAL → dalam `WEB_HEARTBEAT_TIMEOUT` (5 dtk) sistem
  balik AUTO otomatis (cek log `Heartbeat UI hilang`).

---

## Tabel Troubleshooting

### Servo (Dynamixel)
| Gejala | Kemungkinan penyebab | Solusi |
|---|---|---|
| "Gagal membuka port" | `/dev/ttyAMA0` tidak ada / dipakai | `dtparam=uart0=on` di config.txt, reboot; pastikan tak ada program lain buka port |
| Scan tidak menemukan ID | **baud tidak cocok** (driver `1000000` vs servo `57600`), wiring A/B tertukar, torque 12V mati | samakan `BAUDRATE`; cek RxMonitor (lihat di bawah); pastikan suplai 12V |
| TX jalan, servo diam | jalur RX (RO) putus / DI-RO tertukar | jalankan `RxMonitor.py`: byte kosong = curigai GND/RO |
| Servo bergerak **menjauh** target (kamera, IR, **dan** joystick manual) | arah putar fisik servo terbalik thd konvensi sistem | `YAW_INVERT` / `PITCH_INVERT = True`. **Jangan** balik tanda `*_GAIN_DEG` atau `IR_REVERSE` — lihat DOKUMENTASI §8b |
| Menjauh **hanya** saat tracking kamera, joystick manual benar | tanda gain kamera | balik tanda `YAW_GAIN_DEG` / `PITCH_GAIN_DEG` |
| Menjauh **hanya** saat pengarahan IR, kamera benar | urutan sensor IR mirror thd sumbu-x kamera | `IR_REVERSE = True` |
| Perintah yaw menggerakkan sumbu pitch (bukan terbalik, tapi **tertukar**) | `ID_X`/`ID_Y` tidak cocok dengan servo fisik | cek `python3 actuation/_servo_driver.py` → ketik `1 200`, lihat sumbu mana yang bergerak; sesuaikan `ID_X`/`ID_Y` |
| Gerakan patah/lag saat scanning | laju kirim terlalu tinggi | turunkan `SERVO_MAX_HZ` dan/atau `SERVO_SPEED` (bukan `SCAN_YAW_DPS`) |
| Servo mentok sebelum target | jangkauan config terlalu sempit | sesuaikan `YAW/PITCH_MIN/MAX` (default 135–225) |

### Kamera / Deteksi
| Gejala | Penyebab | Solusi |
|---|---|---|
| `YOLODetector` gagal di `start()` | model tidak ditemukan | perbaiki `MODEL_PATH` (default relatif `../Program/...`); salin model ke `safe/` |
| Import `picamera2`/`cv2` error | dependensi belum ada / bukan Pi | install; pastikan jalan di Raspberry Pi |
| Kotak deteksi tidak muncul | ambang terlalu ketat / model kurang cocok | turunkan `DETECT_CONF`; cek kelas model = "api" |
| FPS rendah / lag | inferensi berat | naikkan `DETECT_EVERY` (deteksi lebih jarang), pakai model NCNN |
| `/stream` kosong | pakai FakeDetector (bukan YOLO) | jalankan `use_fake_detector=False` |
| Kamera error "in use" | dibuka dua proses | hanya YOLODetector yang boleh buka kamera |

### Sensor IR
| Gejala | Penyebab | Solusi |
|---|---|---|
| `init_sensors` ImportError | `board`/adafruit belum ada | install `adafruit-circuitpython-ads1x15` |
| ADS1115 tidak terdeteksi | I2C mati / alamat salah | `i2cdetect -y 1` harus tampak `48` & `49`; cek `dtparam=i2c_arm=on` |
| Semua sensor nilainya sama/statis | wiring analog / catu sensor | cek VDD/GND sensor, pin A0–A3 |
| Arah IR terbalik (api kiri → `ir_x>0`) | urutan sensor mirror | balik `IR_REVERSE` |
| IR tidak pernah "panas" | ambang terlalu tinggi | turunkan `IR_DIFF_THRESHOLD` |
| Alarm palsu terus | ambang terlalu rendah / drift | naikkan `IR_DIFF_THRESHOLD` |

### Audio (DAC)
| Gejala | Penyebab | Solusi |
|---|---|---|
| Tidak ada suara | overlay/device salah | `dtoverlay=hifiberry-dac`; cek `aplay -l`; `DEVICE=0` = hifiberry |
| Error device di `sd.play` | index device keliru | jalankan `list_devices()`, sesuaikan `DEVICE` |
| Suara pecah/distorsi | amplitudo terlalu besar | kecilkan amplitudo; ingat batas `AMPLITUDE_MAX_SAFE` |
| Audio tidak berhenti | — | `audio_stop` memanggil `sounddevice.stop()`; cek modul DACAudio ter-start |

### Fusi & State Machine
| Gejala | Penyebab | Solusi |
|---|---|---|
| Tidak pernah `tracking` | `fire_confirmed` gagal | cek: IR panas? `confidence≥YOLO_CONF_THRESHOLD`? `fused≥FUSED_THRESHOLD`? |
| Skor `fused` selalu rendah | arah IR↔kamera dianggap tak setuju → kena penalti | perbaiki `IR_REVERSE`; longgarkan `AGREE_TOL` |
| Langsung padam lalu ulang terus | `fire_cleared` tak pernah terbit | pastikan YOLODetector aktif (Fake tak kirim `fire_cleared`) |
| `pre_alarm` selalu timeout ke idle | kamera tak pernah konfirmasi | cek deteksi kamera; turunkan `YOLO_CONF_THRESHOLD` |
| Macet di `cooldown` | masih dalam jeda | tunggu `AUDIO_COOLDOWN` (30 dtk) |

### Scanning
| Gejala | Penyebab | Solusi |
|---|---|---|
| Turret tak menyapu saat idle | belum lewat grace / bukan state IDLE | tunggu `SCAN_GRACE_SEC`; pastikan tidak ada `ir_reading` panas |
| Menyapu tapi tersendat | laju kirim tinggi | turunkan `SERVO_MAX_HZ`/`SERVO_SPEED` |
| Scanning tak berhenti saat api muncul | `state_changed` tak sampai | pastikan orchestrator ter-start; Scanner subscribe `state_changed` |

### Web
| Gejala | Penyebab | Solusi |
|---|---|---|
| Server tak start | `fastapi`/`uvicorn` belum ada | `pip3 install fastapi uvicorn` |
| Port 8000 dipakai | proses lain | ubah `WEB_PORT`, atau matikan proses lama |
| Jog tak berefek | masih mode AUTO | dashboard hanya kirim jog di MANUAL; klik MANUAL dulu |
| Balik AUTO sendiri | heartbeat putus | wajar bila tab tertutup; jaga tab terbuka saat MANUAL |

---

## Alat Diagnostik Sistem

| Alat | Guna |
|---|---|
| `Program/Testing/RxMonitor.py` | baca mentah `/dev/ttyAMA0` (hex+ASCII) — isolasi masalah "TX jalan, RX diam" servo |
| `i2cdetect -y 1` | konfirmasi kedua ADS1115 (`48`,`49`) di bus I2C |
| `aplay -l` / `speaker-test` | konfirmasi PCM5102A terdaftar & keluar bunyi |
| `libcamera-hello` | konfirmasi kamera CSI |
| `dmesg | tail` | error kernel (UART/I2C/USB) |
| `monitor_bus.py` | lihat semua event mengalir real-time (debug logika) |

> **Interpretasi RxMonitor:** tidak ada byte → curigai GND / DI-RO tertukar / RO putus;
> byte acak → curigai baudrate / level sinyal / polaritas A-B.

---

## Kalibrasi Kritis (wajib sebelum andalkan sistem)

1. **`IR_REVERSE`** — api di **kiri** frame harus menghasilkan `ir_x < 0`.
   Uji dengan `monitor_bus.py` sambil menaruh api di sisi kiri/kanan.
2. **Arah servo** — turret harus **mendekat** ke target, bukan menjauh.
3. **`YAW/PITCH_NEUTRAL` = 180** — verifikasi 180° benar posisi tengah mekanik.
4. **`FUSED_THRESHOLD` / `YOLO_CONF_THRESHOLD`** — seimbangkan sensitivitas vs alarm palsu.
5. **Baud servo** — samakan `_servo_driver.py BAUDRATE` dengan setelan fisik servo.
6. **Batas audio [SAFETY]** — jangan longgarkan `AMPLITUDE_MAX_SAFE`,
   `AUDIO_MAX_DURATION`, `AUDIO_COOLDOWN` tanpa alasan teknis.
