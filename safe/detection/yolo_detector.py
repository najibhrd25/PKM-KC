"""
YOLODetector — deteksi api nyata via Pi Camera + YOLO (NCNN).

Di-port dari Program/train_yolo/camera_tracker.py (capture_loop) ke dalam
kontrak BaseDetector. Kontraknya IDENTIK dengan FakeDetector:

    publish events.FIRE_DETECTED  { bbox: [cx, cy, w, h], confidence: float,
                                    frame_w: int, frame_h: int }
    publish events.FIRE_CLEARED   {}   saat api hilang dari frame.

Tambahan (untuk dashboard web): publish events.FRAME_UPDATE { jpeg: bytes }
berisi frame beranotasi. Karena kontrak deteksi identik, mengganti
FakeDetector -> YOLODetector di main.py tidak mengubah modul lain.

Catatan: modul inilah satu-satunya pemilik kamera (CSI). Jangan jalankan
program lain yang membuka kamera bersamaan.
"""
import time
import threading
import logging

from core.interfaces import BaseDetector
from core import events, config

logger = logging.getLogger(__name__)


class YOLODetector(BaseDetector):
    def __init__(self, event_bus, model_path=None):
        self._bus = event_bus
        self._model_path = model_path or config.MODEL_PATH
        self._running = False
        self._thread = None
        self._model = None
        self._picam2 = None
        self._fire_present = False   # untuk mendeteksi transisi api hilang

    # ======================= LIFECYCLE =======================
    def start(self):
        # Import berat ditunda ke start() supaya modul bisa di-import di mesin
        # non-Pi (mis. saat unit test) tanpa menyeret ultralytics/picamera2.
        from ultralytics import YOLO
        from picamera2 import Picamera2

        logger.info("Memuat model YOLO: %s", self._model_path)
        self._model = YOLO(self._model_path)

        self._picam2 = Picamera2()
        cam_config = self._picam2.create_preview_configuration(
            main={"format": "BGR888", "size": config.FRAME_SIZE}
        )
        self._picam2.configure(cam_config)
        self._picam2.start()
        time.sleep(1)

        self._running = True
        self._thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._thread.start()
        logger.info("YOLODetector aktif (kamera + inferensi).")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._picam2:
            self._picam2.stop()

    # ======================= LOOP INFERENSI =======================
    def _inference_loop(self):
        import cv2

        last_boxes = []
        frame_idx = 0
        prev_time = time.time()
        fps = 0.0

        while self._running:
            frame = self._picam2.capture_array()
            if config.FRAME_ROTATION is not None:
                frame = cv2.rotate(frame, config.FRAME_ROTATION)
            fh, fw = frame.shape[:2]

            if frame_idx % config.DETECT_EVERY == 0:
                results = self._model.predict(
                    frame, conf=config.DETECT_CONF,
                    imgsz=config.IMG_SIZE, verbose=False)
                last_boxes = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf_val = float(box.conf[0])
                    cls_name = self._model.names[int(box.cls[0])]
                    last_boxes.append((x1, y1, x2, y2, conf_val, cls_name))

                target = self._pick_target(last_boxes)
                self._publish_detection(target, fw, fh)

            # gambar overlay + FPS lalu siarkan ke WebBridge
            annotated = self._draw(frame, last_boxes)
            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                fps = fps * 0.9 + (1.0 / dt) * 0.1
            cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            ok, jpeg = cv2.imencode(".jpg", annotated)
            if ok:
                self._bus.publish(events.FRAME_UPDATE, {"jpeg": jpeg.tobytes()})

            frame_idx += 1

    # ======================= HELPER =======================
    @staticmethod
    def _pick_target(boxes):
        """Box dengan confidence tertinggi (index 4). None bila kosong."""
        if not boxes:
            return None
        return max(boxes, key=lambda b: b[4])

    def _publish_detection(self, target, fw, fh):
        """Terbitkan FIRE_DETECTED (tiap detect-frame) / FIRE_CLEARED (sekali)."""
        if target is not None:
            x1, y1, x2, y2, conf_val, _ = target
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            w = x2 - x1
            h = y2 - y1
            self._bus.publish(events.FIRE_DETECTED, {
                "bbox": [cx, cy, w, h],
                "confidence": conf_val,
                "frame_w": fw,
                "frame_h": fh,
            })
            self._fire_present = True
        elif self._fire_present:
            # transisi ada -> hilang: beritahu sekali
            self._bus.publish(events.FIRE_CLEARED, {})
            self._fire_present = False

    def _draw(self, frame, boxes):
        """Overlay ringan: crosshair + kotak (target merah, lain hijau)."""
        import cv2
        from tracking.tracker import aim_point
        fh, fw = frame.shape[:2]

        # crosshair di TITIK BIDIK (pusat + AIM_OFFSET), bukan selalu pusat frame
        ax, ay = aim_point(fw, fh)
        cx0, cy0 = int(ax), int(ay)
        cv2.line(frame, (cx0 - 15, cy0), (cx0 + 15, cy0), (255, 255, 255), 1)
        cv2.line(frame, (cx0, cy0 - 15), (cx0, cy0 + 15), (255, 255, 255), 1)

        # bila digeser, tandai pusat frame samar-samar sebagai acuan kalibrasi
        if (cx0, cy0) != (fw // 2, fh // 2):
            cv2.drawMarker(frame, (fw // 2, fh // 2), (120, 120, 120),
                           cv2.MARKER_TILTED_CROSS, 10, 1)

        target = self._pick_target(boxes)
        for box in boxes:
            x1, y1, x2, y2, conf_val, name = box
            color = (0, 0, 255) if box is target else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{name} {conf_val:.2f}", (x1, max(y1 - 5, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame
