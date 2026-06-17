"""
IRSensorArray — bungkus driver IR.py menjadi modul Event Bus.
Driver asli (_ir_driver.py = IR.py) tidak diubah.
"""
import threading
import logging

from core.interfaces import BaseSensor
from core import events, config
from sensors import _ir_driver   # = IR.py lama

logger = logging.getLogger(__name__)


class IRSensorArray(BaseSensor):
    def __init__(self, event_bus):
        self._bus = event_bus
        self._running = False
        self._thread = None
        self._channels = None

    def start(self):
        self._channels = _ir_driver.init_sensors()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("IRSensorArray berjalan (%d sensor).", len(self._channels))

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _poll_loop(self):
        while self._running:
            readings = _ir_driver.read_all_sensors(self._channels)
            for i, data in enumerate(readings, start=1):
                self._bus.publish(events.IR_READING, {
                    "sensor_id": i,
                    "voltage": data["voltage"],
                    "triggered": data["voltage"] >= config.IR_THRESHOLD_V,
                })
            _ir_driver.time.sleep(config.IR_READ_INTERVAL)
