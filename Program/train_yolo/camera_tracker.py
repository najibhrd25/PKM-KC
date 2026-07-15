import math
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Condition, Thread

import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

MODEL_PATH = 'train-4/weights/best_ncnn_model'
CONF = 0.3
IMG_SIZE = 640
FRAME_SIZE = (640, 480)  # 16:9, sesuai rasio dataset training (bukan 4:3)
PORT = 8081
DETECT_EVERY = 10  # jalankan YOLO tiap N frame, sisanya pakai box terakhir

# Nilai berikut disalin dari safe/core/config.py supaya konsisten dengan
# TrackingLogic saat nanti diintegrasikan ke servo sungguhan.
YAW_GAIN_DEG = 25.0
PITCH_GAIN_DEG = 20.0
YAW_NEUTRAL = 90.0
PITCH_NEUTRAL = 70.0


class FrameBuffer:
    def __init__(self):
        self.jpeg = None
        self.condition = Condition()

    def update(self, jpeg_bytes):
        with self.condition:
            self.jpeg = jpeg_bytes
            self.condition.notify_all()


frame_buffer = FrameBuffer()


class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/stream.mjpg':
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('Age', '0')
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()
        try:
            while True:
                with frame_buffer.condition:
                    frame_buffer.condition.wait()
                    jpeg = frame_buffer.jpeg
                self.wfile.write(b'--FRAME\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                self.wfile.write(f'Content-Length: {len(jpeg)}\r\n\r\n'.encode())
                self.wfile.write(jpeg)
                self.wfile.write(b'\r\n')
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        pass


def pick_target(boxes):
    """Pilih box dengan confidence tertinggi. None kalau tidak ada box."""
    if not boxes:
        return None
    return max(boxes, key=lambda b: b[4])


def compute_position(box, frame_w, frame_h):
    """Ukur posisi box relatif terhadap titik tengah frame.

    Rumus identik dengan TrackingLogic._on_detection di
    safe/tracking/tracker.py, supaya konsisten saat nanti diintegrasikan.
    Bedanya di sini yaw/pitch adalah estimasi sesaat dari posisi netral,
    bukan akumulasi (tidak ada state servo fisik di script ini).
    """
    x1, y1, x2, y2, conf, cls_name = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    dx = cx - frame_w / 2
    dy = cy - frame_h / 2

    err_x = dx / (frame_w / 2)
    err_y = dy / (frame_h / 2)

    err_px = math.hypot(dx, dy)

    yaw_est_deg = YAW_NEUTRAL + err_x * YAW_GAIN_DEG
    pitch_est_deg = PITCH_NEUTRAL + err_y * PITCH_GAIN_DEG

    return {
        'cx': cx, 'cy': cy,
        'dx': dx, 'dy': dy,
        'err_x': err_x, 'err_y': err_y,
        'err_px': err_px,
        'yaw_est_deg': yaw_est_deg,
        'pitch_est_deg': pitch_est_deg,
        'cls_name': cls_name,
        'conf': conf,
    }


def draw_tracking_overlay(frame, boxes, target_box, position):
    fh, fw = frame.shape[:2]
    center = (fw // 2, fh // 2)

    # crosshair di titik tengah frame
    cv2.line(frame, (center[0] - 15, center[1]), (center[0] + 15, center[1]), (255, 255, 255), 1)
    cv2.line(frame, (center[0], center[1] - 15), (center[0], center[1] + 15), (255, 255, 255), 1)

    for box in boxes:
        x1, y1, x2, y2, conf, name = box
        is_target = box is target_box
        color = (0, 0, 255) if is_target else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f'{name} {conf:.2f}', (x1, max(y1 - 5, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    if position is None:
        cv2.putText(frame, 'NO TARGET', (10, fh - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame

    target_point = (int(position['cx']), int(position['cy']))
    cv2.line(frame, center, target_point, (0, 165, 255), 2)
    cv2.circle(frame, target_point, 5, (0, 0, 255), -1)

    lines = [
        f"dx,dy: {position['dx']:+.0f}px, {position['dy']:+.0f}px",
        f"err_x,err_y: {position['err_x']:+.2f}, {position['err_y']:+.2f}",
        f"err_px: {position['err_px']:.1f}",
        f"yaw_est,pitch_est: {position['yaw_est_deg']:.1f}deg, {position['pitch_est_deg']:.1f}deg",
    ]
    y0 = fh - 20 - (len(lines) - 1) * 20
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (10, y0 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

    return frame


def capture_loop(model):
    picam2 = Picamera2()
    cam_config = picam2.create_preview_configuration(
        main={'format': 'BGR888', 'size': FRAME_SIZE}
    )
    picam2.configure(cam_config)
    picam2.start()
    time.sleep(1)

    last_boxes = []
    frame_idx = 0
    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            frame = picam2.capture_array()
            fh, fw = frame.shape[:2]

            if frame_idx % DETECT_EVERY == 0:
                results = model.predict(frame, conf=CONF, imgsz=IMG_SIZE, verbose=False)
                last_boxes = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf_val = float(box.conf[0])
                    cls_name = model.names[int(box.cls[0])]
                    last_boxes.append((x1, y1, x2, y2, conf_val, cls_name))

                target_box = pick_target(last_boxes)
                position = compute_position(target_box, fw, fh) if target_box else None
                if position:
                    print(f"[{time.strftime('%H:%M:%S')}] target={position['cls_name']} "
                          f"conf={position['conf']:.2f} dx={position['dx']:+.0f} dy={position['dy']:+.0f} "
                          f"err_px={position['err_px']:.1f} "
                          f"yaw_est={position['yaw_est_deg']:.1f} pitch_est={position['pitch_est_deg']:.1f}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] NO TARGET")
            else:
                target_box = pick_target(last_boxes)
                position = compute_position(target_box, fw, fh) if target_box else None

            annotated = draw_tracking_overlay(frame, last_boxes, target_box, position)

            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                fps = fps * 0.9 + (1.0 / dt) * 0.1  # exponential moving average
            cv2.putText(annotated, f'FPS: {fps:.1f}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

            ok, jpeg = cv2.imencode('.jpg', annotated)
            if ok:
                frame_buffer.update(jpeg.tobytes())
            frame_idx += 1
    finally:
        picam2.stop()


def main():
    print('Memuat Otak S.A.F.E. Versi Nano (Camera Tracker)...')
    model = YOLO(MODEL_PATH)

    capture_thread = Thread(target=capture_loop, args=(model,), daemon=True)
    capture_thread.start()

    server = ThreadingHTTPServer(('0.0.0.0', PORT), StreamingHandler)
    print(f'Stream siap. Buka di VLC / browser: http://<ip-pi>:{PORT}/stream.mjpg')
    print('Tekan Ctrl+C untuk berhenti.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
