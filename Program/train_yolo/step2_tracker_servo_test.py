"""
Program Uji Integrasi Tracker Kamera + Servo (closed-loop) - Raspberry Pi
=========================================================================

Menyambungkan camera_tracker.py (deteksi YOLO + error posisi) ke servo
Dynamixel MX-106 (Program/Testing/Servo.py) memakai kontrol proporsional
akumulatif, sehingga turret otomatis mengarahkan target ke pusat frame.

    Yaw   = servo ID 1 (kiri/kanan)
    Pitch = servo ID 2 (atas/bawah)
    Titik tengah / init = 180 derajat untuk masing-masing.

Cara pakai (jalankan dari folder train_yolo/ supaya MODEL_PATH relatif valid):
    python tracker_servo_test.py

Buka stream di browser / VLC: http://<ip-pi>:8081/stream.mjpg
Tekan Ctrl+C untuk berhenti (servo balik ke center, torque dimatikan).

Alur uji yang disarankan:
    1. Set ENABLE_SERVO = False dulu -> pastikan deteksi & nilai yaw_cmd/pitch_cmd
       masuk akal tanpa menggerakkan hardware.
    2. Set ENABLE_SERVO = True, limit kecil (±45°), gain kecil -> amati turret
       MENDEKATKAN target ke crosshair. Kalau MENJAUH, balik YAW_SIGN/PITCH_SIGN.
"""

import os
import sys
import time
from http.server import ThreadingHTTPServer
from threading import Thread

import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

# --- Reuse fungsi tracker (dijalankan dari train_yolo/, jadi import langsung) ---
import camera_tracker as ct

# --- Reuse driver servo dari Program/Testing/Servo.py ---
_SERVO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Testing"
)
sys.path.insert(0, os.path.abspath(_SERVO_DIR))
import Servo as servo  # noqa: E402  (import setelah sys.path disisipkan)


# ======================= KONSTANTA BISA-ATUR =======================
YAW_ID = 2
PITCH_ID = 1

YAW_CENTER = 180.0      # sudut init / titik tengah yaw
PITCH_CENTER = 180.0    # sudut init / titik tengah pitch

# Batas gerak per sumbu (derajat dari center), + dan - terpisah.
# Atur sesuai ruang gerak mekanik yang aman.
YAW_RANGE_PLUS = 30.0    # yaw boleh naik s/d YAW_CENTER + 30
YAW_RANGE_MINUS = 30.0   # yaw boleh turun s/d YAW_CENTER - 30
PITCH_RANGE_PLUS = 15.0
PITCH_RANGE_MINUS = 15.0

# Gain proporsional: berapa derajat koreksi pada error penuh (±1) per iterasi.
YAW_GAIN_DEG = 10.0
PITCH_GAIN_DEG = 8.0

# Arah koreksi (tergantung pemasangan mekanik). Kalau turret MENJAUH dari
# target saat diuji, balik nilai yang bersangkutan ke -1.
YAW_SIGN = -1
PITCH_SIGN = +1

# Titik acuan bidik pada frame, sebagai fraksi (0..1). 0.5/0.5 = pusat frame.
# Nosel berada DI BAWAH sumbu kamera -> untuk mengarahkan nosel ke api,
# target perlu "diparkir" di bawah pusat frame. Naikkan AIM_Y_FRAC (mis.
# 0.60-0.70) sampai semburan tepat mengenai api. AIM_X_FRAC untuk offset
# kiri/kanan bila nosel juga bergeser horizontal.
AIM_X_FRAC = 0.50
AIM_Y_FRAC = 0.70

DEADZONE_PX = 8.0     # error piksel di bawah ini diabaikan (anti jitter)
LOCK_PX = 30.0        # dianggap "terkunci" kalau err_px <= ini
SERVO_SPEED = 100     # moving speed saat move_to_angle
ENABLE_SERVO = True   # False = dry-run (uji visi tanpa menggerakkan servo)

# Rotasi hasil tangkapan kamera. Pilih salah satu:
#   None                            -> tanpa rotasi
#   cv2.ROTATE_90_CLOCKWISE         -> putar 90° searah jarum jam
#   cv2.ROTATE_90_COUNTERCLOCKWISE  -> putar 90° berlawanan
#   cv2.ROTATE_180                  -> putar 180° (kamera terpasang terbalik)
# Untuk 90/270 lebar & tinggi otomatis tertukar; deteksi tetap konsisten.
FRAME_ROTATION = None

# Batas absolut hasil hitung (jangan diubah manual, atur lewat RANGE di atas).
YAW_MIN = YAW_CENTER - YAW_RANGE_MINUS
YAW_MAX = YAW_CENTER + YAW_RANGE_PLUS
PITCH_MIN = PITCH_CENTER - PITCH_RANGE_MINUS
PITCH_MAX = PITCH_CENTER + PITCH_RANGE_PLUS


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


# ======================= SERVO =======================
def setup_servo():
    """Buka port, aktifkan torque + joint mode, arahkan ke center.

    Return (port_handler, packet_handler) atau (None, None) saat dry-run.
    """
    if not ENABLE_SERVO:
        print("[SERVO] ENABLE_SERVO=False -> mode dry-run, servo tidak digerakkan.")
        return None, None

    port, pkt = servo.init_dynamixel()
    for sid in (YAW_ID, PITCH_ID):
        servo.set_torque(port, pkt, sid, 1)
        servo.set_joint_mode(port, pkt, sid)

    servo.move_to_angle(port, pkt, YAW_ID, YAW_CENTER, SERVO_SPEED)
    servo.move_to_angle(port, pkt, PITCH_ID, PITCH_CENTER, SERVO_SPEED)
    time.sleep(1.0)  # beri waktu servo sampai ke center
    print(f"[SERVO] Siap di center yaw={YAW_CENTER:.0f} pitch={PITCH_CENTER:.0f}")
    return port, pkt


def shutdown_servo(port, pkt):
    """Kembalikan servo ke center lalu matikan torque & tutup port."""
    if not ENABLE_SERVO or port is None:
        return
    print("\n[SERVO] Kembali ke center & matikan torque...")
    servo.move_to_angle(port, pkt, YAW_ID, YAW_CENTER, SERVO_SPEED)
    servo.move_to_angle(port, pkt, PITCH_ID, PITCH_CENTER, SERVO_SPEED)
    time.sleep(0.8)
    for sid in (YAW_ID, PITCH_ID):
        servo.set_torque(port, pkt, sid, 0)
    port.closePort()


# ======================= LOOP DETEKSI + KONTROL =======================
def control_loop(model, port, pkt):
    picam2 = Picamera2()
    cam_config = picam2.create_preview_configuration(
        main={"format": "BGR888", "size": ct.FRAME_SIZE}
    )
    picam2.configure(cam_config)
    picam2.start()
    time.sleep(1)

    yaw = YAW_CENTER
    pitch = PITCH_CENTER

    last_boxes = []
    frame_idx = 0
    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            frame = picam2.capture_array()
            if FRAME_ROTATION is not None:
                frame = cv2.rotate(frame, FRAME_ROTATION)
            fh, fw = frame.shape[:2]

            is_detect_frame = frame_idx % ct.DETECT_EVERY == 0
            if is_detect_frame:
                results = model.predict(frame, conf=ct.CONF, imgsz=ct.IMG_SIZE, verbose=False)
                last_boxes = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf_val = float(box.conf[0])
                    cls_name = model.names[int(box.cls[0])]
                    last_boxes.append((x1, y1, x2, y2, conf_val, cls_name))

            target_box = ct.pick_target(last_boxes)
            position = (ct.compute_position(target_box, fw, fh,
                                            AIM_X_FRAC, AIM_Y_FRAC)
                        if target_box else None)

            # Kirim perintah servo hanya di frame deteksi (agar bus tidak dibanjiri).
            if is_detect_frame:
                if position is not None:
                    err_px = position["err_px"]
                    if err_px > DEADZONE_PX:
                        yaw += YAW_SIGN * position["err_x"] * YAW_GAIN_DEG
                        pitch += PITCH_SIGN * position["err_y"] * PITCH_GAIN_DEG
                        yaw = _clamp(yaw, YAW_MIN, YAW_MAX)
                        pitch = _clamp(pitch, PITCH_MIN, PITCH_MAX)
                        if ENABLE_SERVO:
                            servo.move_to_angle(port, pkt, YAW_ID, yaw, SERVO_SPEED)
                            servo.move_to_angle(port, pkt, PITCH_ID, pitch, SERVO_SPEED)

                    locked = " LOCKED" if err_px <= LOCK_PX else ""
                    print(f"[{time.strftime('%H:%M:%S')}] target={position['cls_name']} "
                          f"conf={position['conf']:.2f} dx={position['dx']:+.0f} dy={position['dy']:+.0f} "
                          f"err_px={err_px:.1f} yaw_cmd={yaw:.1f} pitch_cmd={pitch:.1f}{locked}")
                else:
                    # Tanpa target: tahan posisi terakhir.
                    print(f"[{time.strftime('%H:%M:%S')}] NO TARGET (hold yaw={yaw:.1f} pitch={pitch:.1f})")

            # Overlay + stream (reuse penuh dari camera_tracker).
            annotated = ct.draw_tracking_overlay(frame, last_boxes, target_box, position)

            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                fps = fps * 0.9 + (1.0 / dt) * 0.1
            cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

            ok, jpeg = cv2.imencode(".jpg", annotated)
            if ok:
                ct.frame_buffer.update(jpeg.tobytes())
            frame_idx += 1
    finally:
        picam2.stop()


def main():
    print("Memuat Otak S.A.F.E. Versi Nano (Tracker + Servo Test)...")
    model = YOLO(ct.MODEL_PATH)

    port, pkt = setup_servo()

    control_thread = Thread(target=control_loop, args=(model, port, pkt), daemon=True)
    control_thread.start()

    server = ThreadingHTTPServer(("0.0.0.0", ct.PORT), ct.StreamingHandler)
    print(f"Stream siap: http://<ip-pi>:{ct.PORT}/stream.mjpg")
    print("Tekan Ctrl+C untuk berhenti.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_servo(port, pkt)


if __name__ == "__main__":
    main()
