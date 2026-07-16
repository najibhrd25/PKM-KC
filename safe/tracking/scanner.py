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

        self._bus.subscribe(events.STATE_CHANGED, self._on_state)

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

    def _scan_loop(self):
        prev = time.time()
        while self._running:
            now = time.time()
            dt = now - prev
            prev = now

            if (self._state == State.IDLE.value and self._idle_since is not None
                    and now - self._idle_since >= config.SCAN_GRACE_SEC):
                self._yaw += self._yaw_dir * config.SCAN_YAW_DPS * dt
                if self._yaw >= config.YAW_MAX:
                    self._yaw = config.YAW_MAX
                    self._yaw_dir = -1
                    self._step_pitch()
                elif self._yaw <= config.YAW_MIN:
                    self._yaw = config.YAW_MIN
                    self._yaw_dir = 1
                    self._step_pitch()
                self._bus.publish(events.SERVO_CMD, {
                    "yaw_deg": self._yaw,
                    "pitch_deg": self._pitch,
                })

            time.sleep(1.0 / config.SERVO_MAX_HZ)

    def _step_pitch(self):
        self._pitch += self._pitch_dir * config.SCAN_PITCH_STEP
        if self._pitch >= config.PITCH_MAX:
            self._pitch = config.PITCH_MAX
            self._pitch_dir = -1
        elif self._pitch <= config.PITCH_MIN:
            self._pitch = config.PITCH_MIN
            self._pitch_dir = 1
