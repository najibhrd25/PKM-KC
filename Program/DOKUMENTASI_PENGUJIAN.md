# Dokumentasi Program Pengujian S.A.F.E.

**S.A.F.E. (Smart Acoustic Fire Extinguisher)** — turret pemadam api akustik berbasis
Raspberry Pi. Dokumen ini merangkum seluruh program **pengujian**:

- **Pipeline deteksi + kontrol bertahap** (`train_yolo/step1..step5`) — dibangun bertingkat,
  tiap step menambah satu kemampuan di atas step sebelumnya.
- **Uji modul hardware individual** (`Program/Testing/`) — servo, sensor IR, DAC audio, dll.

Semua nilai konstanta di tiap program dibuat mudah diubah di bagian atas file (untuk tuning).

---

## Ringkasan Hardware

| Subsistem | Modul | Antarmuka | Pin / Alamat |
|---|---|---|---|
| Kamera | Pi Camera (CSI) | libcamera / Picamera2 | konektor CSI |
| Servo | Dynamixel MX-106 ×2 (yaw ID1, pitch ID2) | UART-RS485 | `/dev/ttyAMA0`, GPIO14/15, 12V |
| Sensor IR | 5× IR via 2× ADS1115 (ADC) | I2C | SDA=GPIO2, SCL=GPIO3, addr `0x48`+`0x49` |
| Audio/pemadam | DAC PCM5102A (I2S) | I2S | BCK=GPIO18, LCK=GPIO19, DIN=GPIO21, SCK=GND |

> Center/init servo = **180°** untuk yaw & pitch. Sensor IR **horizontal** (kiri→kanan),
> **ikut turret** (co-aligned dengan kamera).

---

# Bagian A — Pipeline Pengujian Bertahap (`train_yolo/`)

Setiap step dijalankan **dari folder `train_yolo/`** supaya `MODEL_PATH`
(`train-4/weights/best_ncnn_model`) valid. Semua step menyajikan **stream MJPEG**:
buka di browser/VLC `http://<ip-pi>:<port>/stream.mjpg`. Hentikan dengan **Ctrl+C**.

### Modul pustaka bersama
- **`camera_tracker.py`** — bukan step, tapi pustaka yang di-`import` oleh step2–5.
  Menyediakan: `compute_position()` (error posisi target ternormalisasi `err_x/err_y ∈ [-1,1]`,
  `err_px`), `pick_target()`, `draw_tracking_overlay()`, infrastruktur stream
  (`FrameBuffer`, `StreamingHandler`, `frame_buffer`), dan konstanta kamera
  (`MODEL_PATH`, `CONF`, `IMG_SIZE`, `FRAME_SIZE`, `PORT=8081`, `DETECT_EVERY=10`).

### Peta ketergantungan
```
camera_tracker.py ─┬────────────► step2_tracker_servo_test.py ──► Servo.py
                   ├────────────► step3_fusion_monitor.py ──────► IR.py
                   └──► step3 ──► step4_fusion_servo.py ────────► Servo.py + IR.py
                            └──► step5_fusion_scan.py ──────────► Servo.py + IR.py
```

---

## Step 1 — Stream Kamera + Deteksi YOLO
**File:** `step1_stream_webcam.py` · **Port:** `8080` · **Dependensi:** Picamera2, ultralytics, OpenCV

Program dasar: menangkap frame kamera, menjalankan YOLO (NCNN) tiap `DETECT_EVERY=6` frame,
menggambar bounding box + label + FPS, lalu menyiarkan sebagai MJPEG. Belum ada kontrol apa pun.

- **Tujuan:** memastikan kamera, model deteksi, dan streaming berjalan.
- **Jalankan:** `python step1_stream_webcam.py` → buka `http://<ip-pi>:8080/stream.mjpg`
- **Konstanta:** `MODEL_PATH`, `CONF=0.3`, `IMG_SIZE=640`, `FRAME_SIZE=(640,480)`, `DETECT_EVERY=6`.
- **Amati:** kotak deteksi "api" muncul saat api/target ditampilkan; FPS wajar.

## Step 2 — Tracker + Kontrol Servo (closed-loop)
**File:** `step2_tracker_servo_test.py` · **Port:** `8081` · **Dependensi:** + `Servo.py`

Menghubungkan error posisi kamera ke gerak servo: turret otomatis mengarahkan target ke
pusat frame memakai **kontrol proporsional akumulatif** (`yaw += err_x·gain`, dst.) dari
center 180°.

- **Tujuan:** validasi loop tertutup kamera→servo (aim).
- **Konstanta kunci:**
  - `YAW_CENTER/PITCH_CENTER=180`, batas `*_RANGE_PLUS/MINUS` (±45° → 135–225°).
  - `YAW_GAIN_DEG/PITCH_GAIN_DEG` (kekuatan koreksi), `YAW_SIGN/PITCH_SIGN` (`-1` bila menjauh).
  - `DEADZONE_PX`, `LOCK_PX`, `SERVO_SPEED`, `ENABLE_SERVO` (`False`=dry-run), `FRAME_ROTATION`.
- **Uji:** mulai `ENABLE_SERVO=False` (cek `yaw_cmd/pitch_cmd` di stream) → lalu `True`.
  Jika turret menjauh dari target, balik `*_SIGN`.

## Step 3 — Fusi Sensor Kamera + IR (monitor, tanpa servo)
**File:** `step3_fusion_monitor.py` · **Port:** `8081` · **Dependensi:** + `IR.py`

Menggabungkan deteksi api kamera dengan panas 5 sensor IR. **Belum menggerakkan servo** —
tahap validasi logika fusi. Fungsi inti `fuse()` menghasilkan (di-reuse step4 & step5):

- **AND-gate:** api nyata hanya bila IR panas **dan** kamera yakin (`conf ≥ 0.70`).
- **Cek arah:** posisi target kamera (`cam_x`) vs arah IR (`ir_x`, centroid berbobot).
  Dianggap **setuju** bila sisi sama (`cam_x·ir_x ≥ 0`) atau selisih ≤ `AGREE_TOL`.
- **Skor gabungan (`fused`):** `W_IR·ir_conf + W_CAM·cam_conf`, dipenalti bila arah tak setuju.
- **Fallback:** bila kamera hilang target tapi IR panas → sarankan arah (KIRI/KANAN).
- **Keputusan:** `fire_confirmed = AND-gate ∧ fused ≥ FUSED_THRESHOLD`.
- **Konstanta kunci:** `YOLO_CONF_THRESHOLD=0.70`, `IR_CONF_SCALE` (tuning), `AGREE_TOL`,
  `FUSED_THRESHOLD`, **`IR_REVERSE`** (balik peta sisi IR bila urutan sensor mirror thd kamera).
- **Amati (panel kanan atas stream):** bar IR, `ir_x`, `cam_x`, `agree`, `fused`, dan
  **API TERKONFIRMASI** saat cocok. Kalibrasi `IR_REVERSE` dulu (api kiri harus `ir_x<0`).

## Step 4 — Fusi + Kontrol Servo
**File:** `step4_fusion_servo.py` · **Port:** `8081` · **Dependensi:** + step3 + `Servo.py`

Menggabungkan fusi (step3) dengan kontrol servo (step2). Kebijakan:

- Servo **melacak begitu kamera melihat api** (tidak menunggu konfirmasi fusi).
- Fusi menentukan status **SIAP TEMBAK** = `fire_confirmed` **dan** target terkunci (`err_px ≤ LOCK_PX`).
- **Fallback IR:** kamera hilang target + IR panas → yaw digeser pelan ke arah IR (`FALLBACK_YAW_GAIN`).
- **Cakupan:** hanya aim + status. **Belum** memicu audio/pemadam.
- **Overlay:** tracking + panel fusi + `yaw/pitch [mode]` + banner **SIAP TEMBAK**.

## Step 5 — Tracker + Scanning otomatis
**File:** `step5_fusion_scan.py` · **Port:** `8081` · **Dependensi:** + step3 + `Servo.py`

Melengkapi step4 dengan perilaku **saat tidak ada api sama sekali**: turret menyapu area
dengan pola **raster zig-zag (boustrophedon)**. Mesin-status (prioritas atas→bawah):

| Mode | Pemicu | Aksi servo |
|---|---|---|
| `track` | kamera lihat api | closed-loop aim ke center |
| `ir-seek` | kamera hilang, IR panas | yaw pelan ke arah IR |
| `grace` | tak ada deteksi < `SCAN_GRACE_SEC` (3 dtk) | tahan posisi |
| `scan` | tak ada deteksi > grace | raster sweep mulus |

- **Pola raster:** yaw menyapu 135°↔225° (`yaw += arah·SCAN_YAW_DPS·dt`), pitch melangkah
  `SCAN_PITCH_STEP` tiap yaw capai ujung lalu memantul di batas.
- **Optimasi bus (penting):** perintah goal dikirim via **`GroupSyncWrite` (TX-only, tanpa
  tunggu status)**, kecepatan servo di-set **sekali** di setup, dan **rate-limit** ke
  `SERVO_MAX_HZ` (50 Hz). Ini mencegah I/O serial mem-block loop deteksi (sumber lag).
- **Konstanta kunci:** `SCAN_YAW_DPS`, `SCAN_PITCH_STEP`, `SCAN_GRACE_SEC`, `SERVO_MAX_HZ`.
- **Amati:** setelah 3 dtk tanpa deteksi → banner **SCANNING**; taruh api di tepi → turret
  menemukan lalu mengunci (`track`).

---

# Bagian B — Uji Modul Hardware (`Program/Testing/`)

Program mandiri untuk menguji tiap modul secara terpisah. Umumnya interaktif (ketik perintah).

## `Servo.py` — Kontrol Dynamixel MX-106 (Protocol 1.0)
Driver + program interaktif servo. Buka `/dev/ttyAMA0` (baud **57600**), scan ID di bus,
lalu kontrol posisi manual.

- **Fungsi reuse:** `init_dynamixel()`, `set_torque()`, `set_joint_mode()`/`set_wheel_mode()`,
  `move_to_angle(port,pkt,id,sudut,speed)`, `read_angle()`, `angle_to_position()`,
  `GroupSyncWrite` (dipakai step5 untuk kirim goal 2 servo sekaligus).
- **Mode:** *joint* (kontrol sudut 0–360°) & *wheel* (rotasi kontinu, kecepatan+arah).
- **Jalankan:** `python Servo.py` → ketik `<id> <sudut>`, contoh `1 90`. `exit` untuk keluar.
- **Wiring:** GPIO14(TXD)/GPIO15(RXD) → modul RS485 → bus Dynamixel; MX-106 disuplai 12V terpisah.

## `IR.py` — Pembacaan 5 Sensor IR (2× ADS1115)
Baca 5 kanal IR via I2C, deteksi api **diferensial**: sensor terpanas dianggap "api" hanya
bila menonjol dari rata-rata sensor lain ≥ `DIFF_THRESHOLD` (tahan drift, tidak pakai ambang absolut).

- **Fungsi reuse (dipakai step3–5):** `init_sensors()`, `read_all_sensors()` → list `{raw, voltage}`,
  `render_bar()`. Konstanta `DIFF_THRESHOLD`, `RAW_MAX`.
- **Alamat:** board `0x48` = IR1–4 (A0–A3), board `0x49` = IR5 (A0).
- **Jalankan:** `python IR.py` → visualisasi bar 5 sensor + status "API di IR n".

## `DAC.py` — Uji DAC PCM5102A + Generator Sinyal
Menghasilkan berbagai gelombang audio ke DAC I2S. Fokus interaktif: **pulsa vortex ring**
untuk uji dorongan akustik pemadaman.

- **Generator:** `generate_sine/square/sawtooth/triangle/sweep/white_noise`, dan
  `generate_pulse()` (n siklus, `inverted`, `half_cycle`). Semua diberi fade anti-klik.
- **Playback:** `play(signal)` via `sounddevice` (device index 0 = PCM5102A).
- **Jalankan:** `python DAC.py` → perintah: `f <hz>`, `a <amp>`, `n <siklus>`, `w sine|square`,
  `i` (invert), `h` (half-cycle), `p`/Enter (trigger pulsa), `exit`.
- **Setup:** `dtoverlay=hifiberry-dac` di config, `pip install sounddevice numpy`.

## `PlaySound.py` — Pemutaran File MP3
Memutar file audio (default `tolong_BPxrsyS.mp3`) via PCM5102A, dengan kontrol volume,
kecepatan (mempengaruhi pitch), pengulangan, dan polaritas.

- **Fungsi:** `load_sound()` (mp3→float32 via pydub), `play_sound(amplitude, speed, repeat, inverted)`.
- **Jalankan:** `python PlaySound.py` → perintah: `a <vol>`, `s <speed>`, `r <repeat>`,
  `i` (invert), `p`/Enter (mainkan), `exit`.
- **Setup:** `sudo apt install ffmpeg`, `pip install pydub numpy sounddevice`.

## `RxMonitor.py` — Diagnostik Jalur RX Dynamixel
Alat **debug wiring**: membaca `/dev/ttyAMA0` mentah (hex+ASCII) tanpa parsing protokol,
untuk mengisolasi masalah "TX jalan tapi tidak ada balasan" dari servo.

- **Jalankan:** `python RxMonitor.py` (terminal 1) + jalankan `Servo.py` (terminal 2) agar ada
  aktivitas bus. Baud **1000000**.
- **Interpretasi:** tidak ada byte → curigai GND/DI-RO tertukar/RO putus; byte acak → curigai
  baudrate/level sinyal/polaritas A-B.

---

## Catatan Umum & Tuning

- **Konflik perangkat:** jangan jalankan dua program yang sama-sama membuka **kamera** atau
  **`/dev/ttyAMA0`** bersamaan. Kamera (CSI) vs IR (I2C) vs servo (UART) tidak saling bentrok.
- **Dry-run dulu:** untuk step2/4/5 set `ENABLE_SERVO=False` guna memvalidasi visi/logika
  tanpa menggerakkan hardware.
- **Urutan kalibrasi yang disarankan:**
  1. `IR.py` & `Servo.py` — pastikan tiap modul mentah bekerja.
  2. Step1 → Step2 (arah `*_SIGN`) → Step3 (kalibrasi `IR_REVERSE`, `AGREE_TOL`, `FUSED_THRESHOLD`).
  3. Step4 (SIAP TEMBAK) → Step5 (`SCAN_YAW_DPS`, `SERVO_MAX_HZ`).
- **Lag saat scanning:** dikendalikan `SERVO_MAX_HZ` (laju kirim) & `SERVO_SPEED` (profil
  kecepatan internal servo) — **bukan** `SCAN_YAW_DPS`. Kecilkan `SERVO_SPEED` untuk sapuan
  pelan tanpa menambah beban bus.
- **Langkah berikutnya (belum ada):** memicu audio/pemadam (`DAC.py`) saat **SIAP TEMBAK**,
  lengkap dengan durasi & cooldown keamanan.
