"""
Scanner — sapuan raster otomatis saat sistem IDLE (tidak ada api).

Memenuhi perilaku "passive scanning" yang disebut arsitektur untuk state IDLE.
Di-port dari mode `scan` di Program/train_yolo/step5_fusion_scan.py: pola
raster zig-zag (boustrophedon) — yaw menyapu 135°<->225°, pitch melangkah tiap
yaw menyentuh ujung lalu memantul di batas.

Aktif HANYA saat state == IDLE dan sudah melewati SCAN_GRACE_SEC. Begitu state
lain (PRE_ALARM/TRACKING/...) masuk, sapuan berhenti sehingga tidak bentrok
dengan TrackingLogic. Perintah dikirim lewat SERVO_CMD (bus tunggal-penulis;
ServoActuator me-rate-limit pengiriman ke bus Dynamixel).
"""
import time
import threading
import logging

from core.interfaces import BaseModule
from core.state_machine import State
from core import events, config

logger = logging.getLogger(__name__)


class Scanner(BaseModule):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._running = False
        self._thread = None

        self._state = State.IDLE.value
        self._idle_since = None

        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._yaw_dir = 1     # +1 -> naik ke YAW_MAX, -1 -> turun ke YAW_MIN
        self._pitch_dir = 1

        self._ir_hot = False          # petunjuk arah panas dari Orchestrator
        self._ir_x = None
        self._hint_at = None
        self._guide_since = None          # kapan mulai mengikuti petunjuk ini
        self._guide_blocked_until = 0.0   # sampai kapan petunjuk IR diabaikan

        self._bus.subscribe(events.STATE_CHANGED, self._on_state)
        self._bus.subscribe(events.SCAN_HINT, self._on_hint)

    def start(self):
        # anggap boot dalam kondisi IDLE (orchestrator tidak menerbitkan
        # STATE_CHANGED untuk state awal)
        self._idle_since = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        logger.info("Scanner siap (raster sweep saat IDLE).")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _on_state(self, data):
        self._state = data.get("new")
        if self._state == State.IDLE.value:
            # mulai hitung grace; sapuan dimulai dari netral
            self._idle_since = time.time()
            self._yaw = config.YAW_NEUTRAL
            self._pitch = config.PITCH_NEUTRAL
            self._yaw_dir = 1
        else:
            self._idle_since = None   # keluar IDLE -> hentikan sapuan

    def _on_hint(self, data):
        """Petunjuk arah panas IR. Hanya memandu arah — tidak memutuskan apa pun."""
        self._ir_hot = bool(data.get("ir_hot"))
        self._ir_x = data.get("ir_x")
        self._hint_at = time.time()

    def _guided(self, now):
        """True bila petunjuk IR masih segar, menunjukkan panas, DAN belum menyerah.

        Batas menyerah wajib ada: panas yang bertahan tapi tak pernah
        dikonfirmasi kamera (matahari, solder, sensor menyimpang) akan memarkir
        turret permanen dan sapuan tidak pernah jalan. Sama berlakunya bila
        IR_REVERSE terbalik — turret berputar menjauh sampai mentok batas yaw.
        """
        segar = (config.IR_SCAN_GUIDE and self._ir_hot and self._ir_x is not None
                 and self._hint_at is not None
                 and now - self._hint_at <= config.IR_HINT_STALE_SEC)
        if not segar:
            self._guide_since = None
            return False

        if now < self._guide_blocked_until:
            return False            # baru saja menyerah pada panas ini

        if self._guide_since is None:
            self._guide_since = now
        elif now - self._guide_since > config.IR_GUIDE_DWELL_SEC:
            self._guide_since = None
            self._guide_blocked_until = now + config.IR_GUIDE_REARM_SEC
            logger.info("Panas IR tak dikonfirmasi kamera %.0f s — "
                        "lanjut menyapu, IR diabaikan %.0f s.",
                        config.IR_GUIDE_DWELL_SEC, config.IR_GUIDE_REARM_SEC)
            return False
        return True

    def _scan_loop(self):
        prev = time.time()
        while self._running:
            now = time.time()
            dt = now - prev
            prev = now

            if (self._state == State.IDLE.value and self._idle_since is not None
                    and now - self._idle_since >= config.SCAN_GRACE_SEC):
                if self._guided(now):
                    self._steer_to_ir(dt)
                else:
                    self._raster(dt)
                self._bus.publish(events.SERVO_CMD, {
                    "yaw_deg": self._yaw,
                    "pitch_deg": self._pitch,
                })

            time.sleep(1.0 / config.SERVO_MAX_HZ)

    def _steer_to_ir(self, dt):
        """Arahkan yaw ke sumber panas; raster dihentikan sementara.

        Begitu sudah menghadap (|ir_x| kecil), turret DIAM supaya kamera punya
        kesempatan mengenali api — itu tujuan seluruh pemanduan ini.
        Pitch tidak disentuh: array IR horizontal tidak memberi info elevasi.
        """
        if abs(self._ir_x) <= config.IR_SCAN_TOL:
            return
        self._yaw += self._ir_x * config.IR_SCAN_GAIN_DPS * dt
        self._yaw = max(config.YAW_MIN, min(config.YAW_MAX, self._yaw))

    def _raster(self, dt):
        """Sapuan zig-zag biasa: yaw menyapu, pitch melangkah di tiap ujung."""
        self._yaw += self._yaw_dir * config.SCAN_YAW_DPS * dt
        if self._yaw >= config.YAW_MAX:
            self._yaw = config.YAW_MAX
            self._yaw_dir = -1
            self._step_pitch()
        elif self._yaw <= config.YAW_MIN:
            self._yaw = config.YAW_MIN
            self._yaw_dir = 1
            self._step_pitch()

    def _step_pitch(self):
        self._pitch += self._pitch_dir * config.SCAN_PITCH_STEP
        if self._pitch >= config.PITCH_MAX:
            self._pitch = config.PITCH_MAX
            self._pitch_dir = -1
        elif self._pitch <= config.PITCH_MIN:
            self._pitch = config.PITCH_MIN
            self._pitch_dir = 1
