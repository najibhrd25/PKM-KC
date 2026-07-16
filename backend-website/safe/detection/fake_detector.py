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
