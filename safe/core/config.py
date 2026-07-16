"""
config.py — Parameter terpusat S.A.F.E

Semua angka yang bisa diubah saat tuning ada di sini, supaya tidak
tersebar di banyak file. Nilai bertanda KALIBRASI wajib disetel ulang
setelah perakitan fisik.
"""

# ======================= SENSOR IR =======================
IR_THRESHOLD_V   = 1.5     # volt; di atas ini sensor dianggap "panas"  [KALIBRASI]
IR_READ_INTERVAL = 0.1     # detik antar pembacaan (sapuan ~10 Hz)
N_IR             = 5       # jumlah kanal IR fisik (2x ADS1115: 4 + 1)

# Deteksi diferensial (sensor terpanas menonjol dari rata-rata sensor lain)
IR_DIFF_THRESHOLD = 200    # selisih raw min (max - avg_others) -> "panas"  [KALIBRASI]
IR_CONF_SCALE     = 3000.0 # normalisasi selisih raw -> confidence 0..1     [TUNING]
IR_REVERSE        = False    # balik peta sisi IR bila urutan sensor mirror thd kamera

# ======================= DETEKSI YOLO / KAMERA =======================
YOLO_CONF_THRESHOLD = 0.70  # confidence minimum untuk aktivasi pemadaman

MODEL_PATH   = "../Program/train_yolo/train-4/weights/best_ncnn_model"  # relatif thd safe/
DETECT_CONF  = 0.3          # ambang confidence saat predict() (lebih longgar dari aktivasi)
IMG_SIZE     = 640          # ukuran inferensi YOLO
FRAME_SIZE   = (640, 480)   # (lebar, tinggi) capture kamera
DETECT_EVERY = 10           # jalankan YOLO tiap N frame, sisanya pakai box terakhir
FRAME_ROTATION = None       # None / cv2.ROTATE_90_CLOCKWISE / cv2.ROTATE_180 / dst.

# ======================= FUSI IR <-> KAMERA =======================
AGREE_TOL       = 0.4       # |cam_x - ir_x| <= ini -> arah dianggap setuju
DISAGREE_PENALTY = 0.5      # faktor skor gabungan saat arah tak setuju
FUSED_THRESHOLD = 0.6       # skor gabungan min untuk konfirmasi api
W_IR            = 0.5       # bobot confidence IR pada skor gabungan
W_CAM           = 0.5       # bobot confidence kamera pada skor gabungan
FALLBACK_YAW_GAIN = 4.0     # deg jog yaw ke arah IR saat PRE_ALARM (kamera belum lihat)

# ======================= SERVO (Dynamixel MX-106) =======================
# Turret di-center 180° untuk yaw & pitch, jangkauan ±45° (teruji di step2/4/5).
# Yaw (ID 1): 135-225°, netral 180°
YAW_MIN     = 135.0
YAW_MAX     = 225.0
YAW_NEUTRAL = 180.0         # [KALIBRASI]

# Pitch (ID 2): 135-225°, netral 180°
PITCH_MIN     = 135.0
PITCH_MAX     = 225.0
PITCH_NEUTRAL = 180.0       # [KALIBRASI]

# Gain tracking proporsional: berapa derajat koreksi pada error penuh (±1)
YAW_GAIN_DEG   = 25.0       # [TUNING]
PITCH_GAIN_DEG = 20.0       # [TUNING]

# Ambang "terkunci": jarak piksel dari pusat frame yang dianggap cukup terpusat
TARGET_LOCK_PX = 30.0       # [TUNING]

# Pengiriman goal ke bus Dynamixel (GroupSyncWrite TX-only)
SERVO_SPEED    = 100        # profil kecepatan internal servo (di-set sekali)
SERVO_MAX_HZ   = 50.0       # batas laju kirim goal (anti bus-flood) [TUNING]

# ======================= SCANNING (saat IDLE, tak ada api) =======================
SCAN_YAW_DPS    = 30.0      # kecepatan sapuan yaw (deg/detik)              [TUNING]
SCAN_PITCH_STEP = 10.0      # langkah pitch tiap yaw menyentuh ujung        [TUNING]
SCAN_GRACE_SEC  = 3.0       # detik di IDLE tanpa aktivitas sebelum menyapu

# ======================= AUDIO (PCM5102A) =======================
AUDIO_DEFAULT_FREQ  = 45.0  # Hz, tengah rentang 30-60 Hz
AMPLITUDE_MAX_SAFE  = 2 # batas keras amplitudo (limiting perangkat lunak) [SAFETY]
AUDIO_MAX_DURATION  = 30.0  # detik; operasi tunggal tidak boleh lebih [SAFETY]
AUDIO_COOLDOWN      = 30.0  # detik jeda wajib setelah operasi [SAFETY]

# ======================= ORCHESTRATOR =======================
PRE_ALARM_TIMEOUT   = 10.0  # detik; jika tak ada konfirmasi visual, batal ke IDLE
EVAL_RECHECK_DELAY  = 1.0   # detik; jeda sebelum evaluasi api padam/belum

# ======================= WEB (opsional) =======================
WEB_HOST              = "0.0.0.0"
WEB_PORT              = 8000
WEB_HEARTBEAT_TIMEOUT = 5.0   # detik; UI dianggap hilang -> balik ke AUTO
WEB_JOG_STEP_DEG      = 3.0   # derajat per input joystick (dipakai frontend)