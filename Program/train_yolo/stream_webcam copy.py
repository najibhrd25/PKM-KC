import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Condition, Thread

import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

MODEL_PATH = 'v2/model_final_v5/weights/best_ncnn_model'
CONF = 0.3
IMG_SIZE = 640
FRAME_SIZE = (640, 480)  # 16:9, sesuai rasio dataset training (bukan 4:3)
PORT = 8080
DETECT_EVERY = 10  # jalankan YOLO tiap N frame, sisanya pakai box terakhir


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


def draw_boxes(frame, boxes):
    for x1, y1, x2, y2, conf, name in boxes:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f'{name} {conf:.2f}'
        cv2.putText(frame, label, (x1, max(y1 - 5, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return frame


def capture_loop(model):
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={'format': 'BGR888', 'size': FRAME_SIZE}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)

    last_boxes = []
    frame_idx = 0
    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            frame = picam2.capture_array()

            if frame_idx % DETECT_EVERY == 0:
                results = model.predict(frame, conf=CONF, imgsz=IMG_SIZE, verbose=False)
                last_boxes = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf_val = float(box.conf[0])
                    cls_name = model.names[int(box.cls[0])]
                    last_boxes.append((x1, y1, x2, y2, conf_val, cls_name))

            annotated = draw_boxes(frame, last_boxes)

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
    print('Memuat Otak S.A.F.E. Versi Nano...')
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
