"""
TrackingLogic — ubah posisi bounding box di frame menjadi sudut servo
absolut (yaw, pitch), lalu publish servo_cmd.

Pendekatan: proportional centering. Error piksel dari pusat frame
dipetakan ke koreksi sudut. Sudut absolut = netral + koreksi terakumulasi.

Saat EXTINGUISHING, sebuah offset melingkar kecil (DITHER_*) ditambahkan di
atas solusi tracking supaya semburan menyapu area di sekitar api. Offset itu
diterbitkan lewat jalur servo_cmd yang SAMA, jadi tetap hanya ada satu penulis
posisi servo — tidak ada dua modul yang saling menimpa.
"""
import math
import time
import logging
import threading

from core.interfaces import BaseModule
from core.state_machine import State
from core import events, config

logger = logging.getLogger(__name__)


def aim_point(frame_w, frame_h):
    """Titik bidik dalam frame (px): pusat + AIM_OFFSET, dijaga di dalam frame.

    Satu-satunya definisi titik bidik — dipakai TrackingLogic untuk menghitung
    error DAN YOLODetector untuk menggambar crosshair, supaya apa yang terlihat
    di dashboard persis titik yang dikejar servo.
    """
    aim_x = frame_w / 2 + config.AIM_OFFSET_X_PX
    aim_y = frame_h / 2 + config.AIM_OFFSET_Y_PX
    return (max(0.0, min(frame_w - 1.0, aim_x)),
            max(0.0, min(frame_h - 1.0, aim_y)))


class TrackingLogic(BaseModule):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._active = False
        self._yaw = config.YAW_NEUTRAL
        self._pitch = config.PITCH_NEUTRAL
        self._bus.subscribe(events.TRACK_START, self._on_start)
        self._bus.subscribe(events.TRACK_STOP, self._on_stop)
        self._bus.subscribe(events.FIRE_DETECTED, self._on_detection)
        self._bus.subscribe(events.SERVO_STATE, self._on_servo_state)
        self._bus.subscribe(events.STATE_CHANGED, self._on_state)

        self._dither_since = None     # kapan sapuan melingkar dimulai
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._dither_loop, daemon=True)
        self._thread.start()
        logger.info("TrackingLogic siap (sapuan melingkar: %s).",
                    "aktif" if config.DITHER_ENABLED else "nonaktif")

    def stop(self):
        self._running = False
        self._active = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _on_state(self, data):
        """Sapuan melingkar hanya saat audio menyala."""
        if data.get("new") == State.EXTINGUISHING.value:
            self._dither_since = time.time()
        else:
            self._dither_since = None

    def _on_servo_state(self, data):
        """Ikuti posisi aktual turret selama TIDAK aktif.

        Selama IDLE, Scanner yang menggerakkan turret. Tanpa mengikutinya,
        koreksi pertama saat TRACK_START akan dihitung dari netral dan turret
        meloncat balik ke tengah — target langsung keluar frame.
        """
        if self._active:
            return          # saat aktif, modul ini yang memegang nilainya
        self._yaw = float(data.get("yaw_deg", self._yaw))
        self._pitch = float(data.get("pitch_deg", self._pitch))

    def _on_start(self, data):
        # SENGAJA tidak reset ke netral: lanjutkan dari posisi turret sekarang
        # (mis. hasil sapuan Scanner), yang di-cache lewat _on_servo_state.
        self._active = True
        self._on_detection(data)

    def _on_stop(self, data):
        self._active = False

    def _on_detection(self, data):
        """Konversi bbox -> koreksi sudut -> servo_cmd."""
        if not self._active:
            return
        cx, cy, _, _ = data["bbox"]
        fw, fh = data["frame_w"], data["frame_h"]

        # titik bidik: pusat frame + offset kalibrasi (lihat config)
        aim_x, aim_y = aim_point(fw, fh)

        # error piksel dari titik bidik, dinormalisasi ke [-1, 1]
        err_x = (cx - aim_x) / (fw / 2)
        err_y = (cy - aim_y) / (fh / 2)

        # koreksi proporsional (gain dari config)
        self._yaw   += err_x * config.YAW_GAIN_DEG
        self._pitch += err_y * config.PITCH_GAIN_DEG

        # clamp ke batas fisik
        self._yaw   = max(config.YAW_MIN,   min(config.YAW_MAX,   self._yaw))
        self._pitch = max(config.PITCH_MIN, min(config.PITCH_MAX, self._pitch))

        self._emit()

        # beri tahu Orchestrator kalau sudah cukup terpusat pada titik bidik
        err_px = ((cx - aim_x) ** 2 + (cy - aim_y) ** 2) ** 0.5
        if err_px <= config.TARGET_LOCK_PX:
            self._bus.publish(events.TARGET_LOCKED, {"error_px": err_px})

    # ======================= SAPUAN MELINGKAR =======================
    def _dither_offset(self):
        """(d_yaw, d_pitch) pola lingkaran; (0, 0) bila sedang tidak menyapu."""
        if (not config.DITHER_ENABLED or self._dither_since is None
                or config.DITHER_PERIOD_SEC <= 0):
            return 0.0, 0.0
        phase = (2 * math.pi * (time.time() - self._dither_since)
                 / config.DITHER_PERIOD_SEC)
        return (config.DITHER_RADIUS_DEG * math.cos(phase),
                config.DITHER_RADIUS_DEG * math.sin(phase))

    def _emit(self):
        """Satu-satunya penerbit servo_cmd modul ini: solusi tracking + dither."""
        d_yaw, d_pitch = self._dither_offset()
        self._bus.publish(events.SERVO_CMD, {
            "yaw_deg":   self._clamp(self._yaw + d_yaw,
                                     config.YAW_MIN, config.YAW_MAX),
            "pitch_deg": self._clamp(self._pitch + d_pitch,
                                     config.PITCH_MIN, config.PITCH_MAX),
        })

    def _dither_loop(self):
        """Jaga lingkaran tetap mulus di antara deteksi YOLO yang jarang (~2-3 Hz)."""
        while self._running:
            if self._active and self._dither_since is not None:
                self._emit()
            time.sleep(1.0 / max(config.DITHER_HZ, 1.0))

    @staticmethod
    def _clamp(value, lo, hi):
        return max(lo, min(hi, value))
