"""
Bootstrap S.A.F.E — merakit semua modul dan menyuntikkannya ke Orchestrator.

Jalankan dari DALAM folder safe/:
    cd safe && python3 main.py

Flag control (build_system):
    use_fake_detector : True  -> FakeDetector (testing tanpa kamera/api)
                        False -> YOLODetector (produksi; butuh model siap)
    use_web           : True  -> pasang WebBridge (butuh fastapi + uvicorn)
                        False -> sistem berjalan tanpa antarmuka web

Ganti FakeDetector -> YOLODetector cukup lewat flag; modul lain tidak berubah.
"""
import logging
import signal
import time

from core.event_bus import EventBus
from core import config
from orchestrator import Orchestrator

from sensors.ir_sensor import IRSensorArray
from detection.fake_detector import FakeDetector
from detection.yolo_detector import YOLODetector
from tracking.tracker import TrackingLogic
from actuation.servo_actuator import ServoActuator
from audio.dac_audio import DACAudio

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

logger = logging.getLogger("safe.main")


def build_system(use_fake_detector=True, use_web=False):
    """Rakit Event Bus, Orchestrator, dan seluruh modul sesuai flag.

    Return: (bus, orchestrator, modules)
    """
    bus = EventBus()

    detector = FakeDetector(bus) if use_fake_detector else YOLODetector(bus)

    modules = [
        IRSensorArray(bus),
        detector,
        TrackingLogic(bus),
        ServoActuator(bus),
        DACAudio(bus),
    ]

    # --- Titik-ekstensi tahap 9: antarmuka web (opsional) ---
    # Diaktifkan dengan use_web=True. Butuh dependency fastapi + uvicorn dan
    # modul safe/web/web_bridge.py (lihat Reference/WebBridgeReference.py).
    if use_web:
        from web.web_bridge import WebBridge
        modules.append(WebBridge(bus, host=config.WEB_HOST, port=config.WEB_PORT))

    orchestrator = Orchestrator(bus)
    return bus, orchestrator, modules


def main():
    bus, orchestrator, modules = build_system(use_fake_detector=True, use_web=True)

    bus.start()
    orchestrator.start()
    for m in modules:
        if m:
            m.start()

    logger.info("S.A.F.E berjalan. Ctrl+C untuk berhenti.")

    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    try:
        while not stop["flag"]:
            time.sleep(0.5)
    finally:
        for m in reversed(modules):
            if m:
                m.stop()
        orchestrator.stop()
        bus.stop()
        logger.info("S.A.F.E dimatikan dengan aman.")


if __name__ == "__main__":
    main()
