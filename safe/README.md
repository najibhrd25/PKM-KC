# S.A.F.E. — Ringkasan Sistem

**Smart Acoustic Fire Extinguisher** — turret pemadam api akustik berbasis
Raspberry Pi: IR + kamera mendeteksi api → turret 2-sumbu membidik →
gelombang 30–60 Hz memadamkan.

Dokumen ini adalah **rangkuman cepat**. Detail lengkap:

| Dokumen | Isi |
|---|---|
| [DOKUMENTASI_SISTEM.md](DOKUMENTASI_SISTEM.md) | Arsitektur penuh, peta modul, katalog event, state machine |
| [INTEGRATION.md](INTEGRATION.md) | Cara program lain berkomunikasi (Event Bus & HTTP) |
| [PANDUAN_PENGUJIAN.md](PANDUAN_PENGUJIAN.md) | Pengujian bertahap + troubleshooting |

---

## 📁 Struktur Folder

```
safe/
├── main.py              ← titik masuk: rakit & jalankan semua modul
├── orchestrator.py      ← otak: fusi sensor + state machine
├── core/                ← infrastruktur: event bus, config, event, state
├── sensors/             ← IR (5 sensor via 2× ADS1115, I2C 0x48+0x49)
├── detection/           ← kamera+YOLO (yolo_detector) / simulasi (fake_detector)
├── tracking/            ← tracker (bidik target) + scanner (sapu saat idle)
├── actuation/           ← servo Dynamixel MX-106 (yaw ID1, pitch ID2, baud 57600)
├── audio/               ← DAC PCM5102A (gelombang pemadam)
└── web/                 ← dashboard http://<ip-pi>:8000
```

**Pola tiap subsistem:** `_xxx_driver.py` (bicara ke hardware, punya console uji
`__main__` mandiri) dibungkus **adapter** yang hanya bicara lewat **Event Bus** —
tidak ada modul yang saling memanggil langsung.

---

## ▶️ Cara Menjalankan

```bash
cd /home/safe/Smart-Acoustic-Fire-Extinguisher/safe
python3 main.py          # Ctrl+C untuk berhenti (shutdown aman)
```

Mode diatur **satu baris** di `main.py` → fungsi `main()`:

```python
build_system(use_fake_detector=True, use_web=True)
```

| Flag | Efek |
|---|---|
| `use_fake_detector=True` | Deteksi disimulasikan (tanpa kamera) — uji logika |
| `use_fake_detector=False` | **Produksi**: kamera + YOLO nyata |
| `use_web=True` | Dashboard di `http://<ip-pi>:8000` (butuh `fastapi`+`uvicorn`) |

Dashboard (mode MANUAL): joystick virtual servo, tombol Home / Torque OFF /
posisi absolut, kontrol audio/DAC lengkap (waveform, frekuensi, amplitudo,
durasi — dibatasi keras oleh `AMPLITUDE_MAX_SAFE` & `AUDIO_MAX_DURATION`),
indikator status real-time, panel sensor IR (tegangan 5 sensor + arah panas),
dan panel log kejadian. Detail: `INTEGRATION.md`; kontrak API web lengkap
untuk integrasi UI kustom: `web/DOKUMENTASI_WEB.md`.

Uji hardware satu-per-satu (tanpa sistem penuh):

```bash
python3 sensors/_ir_driver.py        # baca 5 sensor IR
python3 actuation/_servo_driver.py   # kontrol manual: <id> <sudut>
python3 audio/_dac_driver.py         # generator pulsa vortex ring
```

---

## ⚙️ Config & Sebab-Akibat (`core/config.py`)

Semua parameter di satu file. Tanda: 🔒 = batas keamanan, jangan dilonggarkan sembarangan.

| Kelompok | Parameter (nilai kini) | Jika DINAIKKAN | Jika DITURUNKAN |
|---|---|---|---|
| **IR** | `IR_DIFF_THRESHOLD = 200` ⚠️ | kurang sensitif, tahan alarm palsu | mudah terpicu — **kini terlalu kecil** (lihat catatan) |
| | `IR_REVERSE = True` | — | balik bila arah kiri/kanan IR terbalik terhadap kamera |
| | `IR_THRESHOLD_V = 1.5` | sensor butuh lebih panas utk "triggered" | lebih sensitif |
| **Deteksi** | `YOLO_CONF_THRESHOLD = 0.70` | butuh keyakinan tinggi utk aktivasi | responsif tapi rawan salah target |
| | `DETECT_CONF = 0.3` | box deteksi lebih sedikit/yakin | lebih banyak box lemah |
| | `DETECT_EVERY = 10` | FPS naik, reaksi melambat | deteksi rapat, beban CPU naik |
| **Fusi** | `FUSED_THRESHOLD = 0.6` | konfirmasi api makin ketat | makin longgar |
| | `AGREE_TOL = 0.4` | arah IR↔kamera mudah "setuju" | sering kena penalti skor |
| | `W_IR / W_CAM = 0.5/0.5` | condong percaya IR / kamera | sebaliknya |
| **Servo** | `YAW/PITCH: 135–225°, netral 180°` | jangkauan luas (awas batas mekanik!) | area jangkau sempit |
| | `YAW_GAIN_DEG = 25` | bidikan agresif → bisa overshoot/osilasi | halus tapi lambat mengunci |
| | `TARGET_LOCK_PX = 30` | cepat "terkunci" (kurang presisi) | menuntut presisi sebelum menembak |
| | `SERVO_MAX_HZ = 50` | gerak halus, bus serial padat | anti-lag, gerak agak patah |
| | `SERVO_SPEED = 100` | putaran servo cepat | sapuan pelan & tenang |
| **Scanning** | `SCAN_YAW_DPS = 30` | sapuan cepat (bisa lewatkan api kecil) | teliti tapi lambat |
| | `SCAN_GRACE_SEC = 3` | lama menunggu sebelum menyapu | cepat mulai menyapu |
| | `SCAN_PITCH_STEP = 10` | baris sapuan jarang | overlap rapat |
| **Audio** 🔒 | `AMPLITUDE_MAX_SAFE = 0.3` | dorongan akustik lebih kuat — risiko speaker | aman tapi daya padam berkurang |
| | `AUDIO_MAX_DURATION = 30` 🔒 | operasi tunggal lebih lama | siklus padam-evaluasi lebih pendek |
| | `AUDIO_COOLDOWN = 30` 🔒 | jeda antar operasi lebih lama | operasi bisa lebih rapat |
| | `AUDIO_DEFAULT_FREQ = 45` | — | tetap di rentang efektif 30–60 Hz |
| **Timing** | `PRE_ALARM_TIMEOUT = 10` | sabar menunggu konfirmasi kamera | cepat menyerah balik IDLE |
| | `EVAL_RECHECK_DELAY = 2` | evaluasi padam lebih lama | keputusan ulang lebih cepat |
| **Web** | `WEB_HEARTBEAT_TIMEOUT = 5` | mode MANUAL bertahan lebih lama tanpa UI | cepat balik AUTO bila tab tertutup |

### Rantai sebab-akibat inti

```
IR panas (IR_DIFF_THRESHOLD)
   → PRE_ALARM
kamera yakin (YOLO_CONF) ∧ skor fusi (FUSED_THRESHOLD)
   → TRACKING (bidik: gain YAW/PITCH_GAIN_DEG)
error ≤ TARGET_LOCK_PX
   → EXTINGUISHING (45 Hz × amp 0.3 × maks 30 dtk)
   → EVALUATING (cek padam)
   → COOLDOWN 30 dtk → IDLE
tanpa api > SCAN_GRACE_SEC → SCANNING (raster 135↔225°)
```

---

## ⚠️ Status Kalibrasi (hasil pengujian terakhir)

| Item | Status |
|---|---|
| Baud servo 57600 | ✅ terverifikasi ping, sudah dikoreksi di driver |
| Gerak servo + feedback posisi | ✅ akurat ±0.2° |
| Audio 45 Hz + pulsa vortex | ✅ terdengar |
| Logika state machine & clamp keamanan | ✅ lulus uji |
| **`IR_DIFF_THRESHOLD`** | ❌ **belum dikalibrasi** — baseline antar-sensor ±1900 > ambang 200, pre-alarm bisa terpicu sendiri. Jalankan kalibrasi api, atau set sementara ke `3000`. |
| Arah tracking (sign yaw/pitch) & `IR_REVERSE` | ⏳ diverifikasi saat uji api (Level 4) |
