"""
YOLODetector — PLACEHOLDER. Diisi setelah model .pt / ONNX siap.

Kontrak yang HARUS dipenuhi (sama persis dengan FakeDetector):
    publish events.FIRE_DETECTED dengan payload:
        { bbox: [cx, cy, w, h], confidence: float,
          frame_w: int, frame_h: int }
    publish events.FIRE_CLEARED saat api hilang dari frame.

Karena kontraknya identik, mengganti FakeDetector -> YOLODetector
di main.py TIDAK mengubah modul lain sama sekali.
"""
import logging

from core.interfaces import BaseDetector
# from ultralytics import YOLO     # diaktifkan saat implementasi
# import cv2

logger = logging.getLogger(__name__)


class YOLODetector(BaseDetector):
    def __init__(self, event_bus, model_path="models/safe_fire.pt"):
        self._bus = event_bus
        self._model_path = model_path
        # TODO: self._model = YOLO(model_path)
        # TODO: self._cap = cv2.VideoCapture(0)

    def start(self):
        raise NotImplementedError(
            "YOLODetector belum diimplementasikan. "
            "Gunakan FakeDetector untuk sementara."
        )

    def stop(self):
        pass

    # def _inference_loop(self):
    #     while self._running:
    #         ok, frame = self._cap.read()
    #         results = self._model(frame, verbose=False)
    #         ...  # ekstrak bbox + confidence, lalu publish FIRE_DETECTED
    #         # untuk stream web (tahap 9): publish FRAME_UPDATE {jpeg}
    #         # annotated = results[0].plot()
    #         # ok, buf = cv2.imencode(".jpg", annotated)
    #         # if ok:
    #         #     self._bus.publish(events.FRAME_UPDATE, {"jpeg": buf.tobytes()})
