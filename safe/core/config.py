"""
config.py — Parameter terpusat S.A.F.E

Semua angka yang bisa diubah saat tuning ada di sini, supaya tidak
tersebar di banyak file. Nilai bertanda KALIBRASI wajib disetel ulang
setelah perakitan fisik.
"""

# ======================= HOT RELOAD =======================
# File ini dipantau ConfigWatcher; menyimpannya langsung memperbarui nilai di
# program yang sedang berjalan, tanpa restart. Yang TIDAK ikut berubah karena
# hanya dipakai sekali saat startup (watcher akan memberi WARNING):
#   SERVO_SPEED, SERVO_MAX_HZ, MODEL_PATH, FRAME_SIZE, DETECT_MODE,
#   WEB_HOST, WEB_PORT
CONFIG_HOT_RELOAD = True    # False -> perubahan baru berlaku setelah restart
CONFIG_POLL_SEC   = 10.0    # detik antar pengecekan perubahan file

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
DETECT_EVERY = 5           # jalankan YOLO tiap N frame, sisanya pakai box terakhir
FRAME_ROTATION = None       # None / cv2.ROTATE_90_CLOCKWISE / cv2.ROTATE_180 / dst.

# ======================= MODE DETEKSI =======================
# Menentukan sensor mana yang dipakai untuk KEPUTUSAN (semua modul tetap jalan,
# jadi dashboard selalu punya video stream + bar IR apa pun modenya).
#   "fusion" -> butuh IR DAN kamera (default, paling aman)
#   "camera" -> hanya YOLO; IR diabaikan untuk keputusan
#   "ir"     -> hanya IR; kamera diabaikan untuk keputusan
DETECT_MODE = "camera"
VALID_DETECT_MODES = ("fusion", "camera", "ir")

# Parameter tracking mode "ir" (yaw saja; array IR tidak punya info pitch)
IR_TRACK_YAW_GAIN = 8.0     # deg jog yaw per unit ir_x saat TRACKING        [TUNING]
IR_TRACK_TOL      = 0.15    # |ir_x| di bawah ini dianggap sudah terpusat    [TUNING]
IR_LOCK_COUNT     = 3       # siklus berturut terpusat sebelum TARGET_LOCKED [TUNING]
IR_JOG_HZ         = 5.0     # batas laju jog dari IR (anti servo tersentak)  [TUNING]

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
YAW_MIN     = 120.0
YAW_MAX     = 240.0
YAW_NEUTRAL = 180.0         # [KALIBRASI]

# Pitch (ID 2): 135-225°, netral 180°
PITCH_MIN     = 190
PITCH_MAX     =  210
PITCH_NEUTRAL = 180.0       # [KALIBRASI]

# Arah putar fisik. Seluruh sistem (kamera, IR, joystick) memakai konvensi
# "sudut naik = turret ke kanan / ke bawah". Bila pemasangan servo membuat arah
# nyatanya terbalik, set True — sudut dicerminkan terhadap netral tepat sebelum
# dikirim ke servo, jadi SATU flag ini membenarkan semua sumber sekaligus.
# Jangan mengompensasi lewat IR_REVERSE atau tanda *_GAIN_DEG: itu hanya
# memperbaiki satu jalur dan membuat cek `agree` mode fusion selalu gagal.
YAW_INVERT    = True        # [KALIBRASI]
PITCH_INVERT  = False       # [KALIBRASI]

# Posisi istirahat pitch saat shutdown, dituju SEBELUM torque pitch dilepas
# supaya turret turun terkendali, bukan jatuh. SENGAJA di luar PITCH_MIN/MAX
# (itu batas operasi, ini posisi parkir) — tidak kena clamp operasional.
PITCH_PARK_DEG = 100.0      # [KALIBRASI]

# Gain tracking proporsional: berapa derajat koreksi pada error penuh (±1)
YAW_GAIN_DEG   = 5.0       # [TUNING]
PITCH_GAIN_DEG = 2.0       # [TUNING]

# Titik bidik dalam frame, relatif terhadap pusat (piksel). Default 0,0 = pusat.
# Crosshair di video stream digambar di titik ini, jadi bisa disetel sambil
# melihat dashboard.
#
# PENTING — arah fisiknya kebalikan dari arah crosshair:
#   AIM_OFFSET_Y_PX > 0  -> crosshair TURUN di frame
#                        -> api disetir ke bawah pusat
#                        -> turret membidik LEBIH TINGGI dari tengah api
#   AIM_OFFSET_Y_PX < 0  -> crosshair NAIK di frame
#                        -> turret membidik LEBIH RENDAH (mis. ke pangkal api)
AIM_OFFSET_X_PX = -15       # + = crosshair ke kanan   [KALIBRASI]
AIM_OFFSET_Y_PX = 60       # + = crosshair ke bawah   [KALIBRASI]

# Ambang "terkunci": jarak piksel dari titik bidik yang dianggap cukup terpusat
TARGET_LOCK_PX = 20.0       # [TUNING]

# Sapuan melingkar kecil saat audio menyala (state EXTINGUISHING), supaya
# semburan mengenai area di sekitar api, bukan satu titik saja. Offset
# ditambahkan DI ATAS solusi tracking, jadi tetap mengikuti api bila bergeser.
DITHER_ENABLED    = True    # False -> turret diam di titik kunci
DITHER_RADIUS_DEG = 0.5     # jari-jari lingkaran, yaw & pitch (derajat) [TUNING]
DITHER_PERIOD_SEC = 2.0     # detik per satu putaran penuh               [TUNING]
DITHER_HZ         = 20.0    # laju kirim servo_cmd saat menyapu          [TUNING]

# Pengiriman goal ke bus Dynamixel (GroupSyncWrite TX-only)
SERVO_SPEED    = 10        # profil kecepatan internal servo (di-set sekali)
SERVO_MAX_HZ   = 50.0       # batas laju kirim goal (anti bus-flood) [TUNING]

# ======================= SCANNING (saat IDLE, tak ada api) =======================
SCAN_YAW_DPS    = 10.0      # kecepatan sapuan yaw (deg/detik)              [TUNING]
SCAN_PITCH_STEP = 15.0      # langkah pitch tiap yaw menyentuh ujung        [TUNING]
SCAN_GRACE_SEC  = 3.0       # detik di IDLE tanpa aktivitas sebelum menyapu

# IR sebagai PEMANDU sapuan saja — sama sekali tidak ikut memutuskan pemadaman.
# Berguna dipasangkan dengan DETECT_MODE="camera": keputusan tetap murni YOLO,
# tapi saat IDLE turret diarahkan ke sumber panas alih-alih menyapu buta, jadi
# kamera lebih cepat menemukan api.
# Hanya berlaku di state IDLE; begitu api terlihat, Scanner berhenti seperti biasa.
IR_SCAN_GUIDE    = False     # False -> raster zig-zag biasa, IR diabaikan penuh
IR_SCAN_GAIN_DPS = 15.0     # deg/detik saat mengarah ke panas  [TUNING]
IR_SCAN_TOL      = 0.15     # |ir_x| di bawah ini -> sudah menghadap, diam menunggu
IR_HINT_STALE_SEC = 2.0     # tanpa petunjuk selama ini -> kembali menyapu biasa
# Batas menyerah. Tanpa ini, sumber panas yang bertahan tapi bukan api (matahari,
# solder, sensor yang biasnya menyimpang) memarkir turret permanen dan sapuan
# tidak pernah jalan. Setelah menyerah, petunjuk IR diabaikan selama REARM
# sehingga ruangan tetap tersapu.
IR_GUIDE_DWELL_SEC = 8.0    # maks. mengikuti satu petunjuk sebelum menyerah [TUNING]
IR_GUIDE_REARM_SEC = 30.0   # jeda sebelum IR boleh memandu lagi             [TUNING]

# ======================= AUDIO (PCM5102A) =======================
AUDIO_DEFAULT_FREQ  = 30.0  # Hz, tengah rentang 30-60 Hz
AMPLITUDE_MAX_SAFE  = 1 # batas keras amplitudo (limiting perangkat lunak) [SAFETY]
AUDIO_MAX_DURATION  = 15.0  # detik; operasi tunggal tidak boleh lebih [SAFETY]
AUDIO_COOLDOWN      = 10.0  # detik jeda wajib setelah operasi [SAFETY]

# Bentuk gelombang saat pemadaman OTOMATIS (state EXTINGUISHING).
#   "sine"/"square"/"sawtooth"/"triangle" -> nada kontinu selama duration
#   "pulse_train" -> rentetan pulsa, tiap pulsa dipisah hening PULSE_GAP_SEC
AUDIO_WAVEFORM  = "pulse_train"
PULSE_GAP_SEC   = 0.19       # detik hening antar pulsa              [TUNING]
PULSE_N_CYCLES  = 1         # jumlah siklus gelombang tiap pulsa    [TUNING]
# Bentuk DI DALAM tiap pulsa. Hanya "sine" | "square" yang didukung —
# nilai lain (sawtooth/triangle) tidak berlaku di mode pulsa.
PULSE_WAVEFORM  = "square"    # [TUNING]
VALID_PULSE_WAVEFORMS = ("sine", "square")

# Strategi percobaan ulang pemadaman. Tiap percobaan berlangsung
# AUDIO_MAX_DURATION; bila jatah percobaan habis dan api tetap menyala
# -> state ALARM (lihat di bawah).
#
#   True  -> tiap percobaan memakai frekuensi berikutnya dari AUDIO_FREQ_SEQUENCE.
#            Jumlah percobaan = panjang daftar.
#   False -> semua percobaan memakai AUDIO_DEFAULT_FREQ.
#            Jumlah percobaan = MAX_ATTEMPTS_FIXED.
FREQ_SEQUENCE_ENABLED = False
AUDIO_FREQ_SEQUENCE = (  25.0, 30, 35.0, 40.0 )   # Hz [TUNING]
MAX_ATTEMPTS_FIXED  = 3     # dipakai hanya bila FREQ_SEQUENCE_ENABLED = False

# ALARM: semua frekuensi gagal. Turret kembali netral, sirine berbunyi, lalu
# sistem kembali menyapu.
ALARM_ENABLED      = False
ALARM_DURATION     = 10.0   # detik sirine berbunyi                    [TUNING]
ALARM_FREQ_LOW     = 400.0  # Hz, nada terendah sirine                 [TUNING]
ALARM_FREQ_HIGH    = 1000.0 # Hz, nada tertinggi sirine                [TUNING]
ALARM_SWEEP_PERIOD = 1.0    # detik per satu siklus naik-turun         [TUNING]

# ======================= ORCHESTRATOR =======================
PRE_ALARM_TIMEOUT   = 10.0  # detik; jika tak ada konfirmasi visual, batal ke IDLE
EVAL_RECHECK_DELAY  = 3.0   # detik; jeda sebelum evaluasi api padam/belum

# Jeda penenang sebelum tracking dimulai. Saat api pertama terlihat, sistem
# masuk PRE_ALARM lebih dulu: sapuan Scanner berhenti dan turret dibiarkan
# tenang selama rentang ini, baru tracking mengambil alih.
TRACK_SETTLE_SEC    = 0.1   # detik [TUNING]

# Berapa lama kamera boleh tidak melihat api sebelum sistem menyerah dan
# kembali menyapu. Menahan kedipan deteksi YOLO (1-2 frame) agar tracking
# tidak batal hanya karena bbox sesaat hilang.
TRACK_LOST_SEC      = 10.0   # detik [TUNING]

# Jeda setelah target terkunci sebelum audio menyala. Target harus TETAP
# terkunci selama rentang ini; begitu sempat lepas, hitungan diulang dari nol.
# Gunanya memberi waktu turret benar-benar berhenti bergoyang, dan menolak
# satu bbox nyasar yang kebetulan lewat titik bidik.
#   0.0 -> menyala seketika saat terkunci (perilaku lama)
LOCK_SETTLE_SEC     = 1.0   # detik [TUNING]

# ======================= WEB (opsional) =======================
WEB_HOST              = "0.0.0.0"
WEB_PORT              = 8000
WEB_HEARTBEAT_TIMEOUT = 5.0   # detik; UI dianggap hilang -> balik ke AUTO
WEB_JOG_STEP_DEG      = 3.0   # derajat per input joystick (dipakai frontend)
