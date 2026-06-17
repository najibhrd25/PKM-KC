"""
config.py — Parameter terpusat S.A.F.E

Semua angka yang bisa diubah saat tuning ada di sini, supaya tidak
tersebar di banyak file. Nilai bertanda KALIBRASI wajib disetel ulang
setelah perakitan fisik.
"""

# ======================= SENSOR IR =======================
IR_THRESHOLD_V   = 1.5     # volt; di atas ini sensor dianggap "panas"  [KALIBRASI]
IR_READ_INTERVAL = 0.2     # detik antar pembacaan

# ======================= DETEKSI YOLO =======================
YOLO_CONF_THRESHOLD = 0.70  # confidence minimum untuk aktivasi pemadaman

# ======================= SERVO (Dynamixel MX-106) =======================
# Yaw (ID 1): 0-180°, netral 90°
YAW_MIN     = 0.0
YAW_MAX     = 180.0
YAW_NEUTRAL = 90.0          # [KALIBRASI]

# Pitch (ID 2): 50-140°, netral 70° (20° atas / 70° bawah dari netral)
PITCH_MIN     = 50.0
PITCH_MAX     = 140.0
PITCH_NEUTRAL = 70.0        # [KALIBRASI]

# Gain tracking proporsional: berapa derajat koreksi pada error penuh (±1)
YAW_GAIN_DEG   = 25.0       # [TUNING]
PITCH_GAIN_DEG = 20.0       # [TUNING]

# Ambang "terkunci": jarak piksel dari pusat frame yang dianggap cukup terpusat
TARGET_LOCK_PX = 30.0       # [TUNING]

# ======================= AUDIO (PCM5102A) =======================
AUDIO_DEFAULT_FREQ  = 45.0  # Hz, tengah rentang 30-60 Hz
AMPLITUDE_MAX_SAFE  = 0.855 # batas keras amplitudo (limiting perangkat lunak) [SAFETY]
AUDIO_MAX_DURATION  = 30.0  # detik; operasi tunggal tidak boleh lebih [SAFETY]
AUDIO_COOLDOWN      = 30.0  # detik jeda wajib setelah operasi [SAFETY]

# ======================= ORCHESTRATOR =======================
PRE_ALARM_TIMEOUT   = 10.0  # detik; jika tak ada konfirmasi visual, batal ke IDLE
EVAL_RECHECK_DELAY  = 2.0   # detik; jeda sebelum evaluasi api padam/belum
