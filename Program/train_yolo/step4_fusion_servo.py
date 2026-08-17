"""
Step 4 - Integrasi Fusi Sensor + Kontrol Servo (closed-loop) - Raspberry Pi
===========================================================================

Menggabungkan:
    - Step 3 (step3_fusion_monitor.py): fusi kamera (YOLO) + 5 sensor IR.
    - Step 2 (kontrol servo closed-loop): turret mengarahkan target ke center.

Kebijakan (dikonfirmasi user):
    1. AIM: servo MELACAK begitu kamera melihat api (tidak menunggu konfirmasi
       fusi). Fusi menentukan status "TERKUNCI & SIAP TEMBAK".
    2. CAKUPAN: hanya aim + status. BELUM memicu audio/pemadam (DAC.py).
    3. FALLBACK: bila kamera kehilangan target tapi IR masih panas, yaw digeser
       PELAN ke arah sensor IR terpanas untuk menemukan kembali api.

    Yaw = servo ID 1, Pitch = servo ID 2, center/init 180 derajat.

Cara pakai (jalankan dari folder train_yolo/):
    python step4_fusion_servo.py
Stream: http://<ip-pi>:8081/stream.mjpg   |   Ctrl+C untuk berhenti.
"""

import os
import sys
import time
from http.server import ThreadingHTTPServer
from threading import Thread

import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

# --- Reuse tracker + logika fusi step3 (dijalankan dari train_yolo/) ---
import camera_tracker as ct
import step3_fusion_monitor as fusion   # fuse(), get_latest_ir(), ir_poll_loop(), draw_fusion_overlay()

# --- Reuse driver servo dari Program/Testing/Servo.py ---
_SERVO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Testing"
)
sys.path.insert(0, os.path.abspath(_SERVO_DIR))
import Servo as servo  # noqa: E402


# ======================= KONSTANTA SERVO (bisa-atur) =======================
YAW_ID = 1
PITCH_ID = 2
YAW_CENTER = 180.0
PITCH_CENTER = 180.0

# Batas gerak per sumbu (derajat dari center), + dan - terpisah.
YAW_RANGE_PLUS = 45.0
YAW_RANGE_MINUS = 45.0
PITCH_RANGE_PLUS = 45.0
PITCH_RANGE_MINUS = 45.0

YAW_GAIN_DEG = 10.0        # koreksi per error penuh (±1) dari kamera
PITCH_GAIN_DEG = 8.0
YAW_SIGN = +1             # balik ke -1 kalau turret menjauh dari target
PITCH_SIGN = +1
FALLBACK_YAW_GAIN = 4.0   # derajat per ir_x penuh saat fallback (IR memandu, pelan)

DEADZONE_PX = 8.0        # error piksel di bawah ini diabaikan (anti jitter)
LOCK_PX = 30.0          # err_px <= ini dianggap "terkunci" (dari config.TARGET_LOCK_PX)
SERVO_SPEED = 100
ENABLE_SERVO = True     # False = dry-run (uji tanpa menggerakkan servo)
FRAME_ROTATION = None   # None / cv2.ROTATE_90_CLOCKWISE / cv2.ROTATE_180 / dst.

# Batas absolut hasil hitung.
YAW_MIN = YAW_CENTER - YAW_RANGE_MINUS
YAW_MAX = YAW_CENTER + YAW_RANGE_PLUS
PITCH_MIN = PITCH_CENTER - PITCH_RANGE_MINUS
PITCH_MAX = PITCH_CENTER + PITCH_RANGE_PLUS


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


# ======================= SERVO =======================
def setup_servo():
    if not ENABLE_SERVO:
        print("[SERVO] ENABLE_SERVO=False -> dry-run, servo tidak digerakkan.")
        return None, None
    port, pkt = servo.init_dynamixel()
    for sid in (YAW_ID, PITCH_ID):
        servo.set_torque(port, pkt, sid, 1)
        servo.set_joint_mode(port, pkt, sid)
    servo.move_to_angle(port, pkt, YAW_ID, YAW_CENTER, SERVO_SPEED)
    servo.move_to_angle(port, pkt, PITCH_ID, PITCH_CENTER, SERVO_SPEED)
    time.sleep(1.0)
    print(f"[SERVO] Siap di center yaw={YAW_CENTER:.0f} pitch={PITCH_CENTER:.0f}")
    return port, pkt


def shutdown_servo(port, pkt):
    if not ENABLE_SERVO or port is None:
        return
    print("\n[SERVO] Kembali ke center & matikan torque...")
    servo.move_to_angle(port, pkt, YAW_ID, YAW_CENTER, SERVO_SPEED)
    servo.move_to_angle(port, pkt, PITCH_ID, PITCH_CENTER, SERVO_SPEED)
    time.sleep(0.8)
    for sid in (YAW_ID, PITCH_ID):
        servo.set_torque(port, pkt, sid, 0)
    port.closePort()


def _move(port, pkt, sid, angle):
    if ENABLE_SERVO and port is not None:
        servo.move_to_angle(port, pkt, sid, angle, SERVO_SPEED)


# ======================= TAMPILAN =======================
def draw_servo_overlay(frame, yaw, pitch, mode, ready):
    cv2.putText(frame, f"yaw={yaw:.1f} pitch={pitch:.1f} [{mode}]", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    if ready:
        fh, fw = frame.shape[:2]
        text = "SIAP TEMBAK"
        (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 3)
        cv2.putText(frame, text, ((fw - tw) // 2, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
    return frame


# ======================= LOOP GABUNGAN =======================
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
    mode = "hold"   # bertahan antar-frame deteksi

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

            # ---- Fusi (reuse step3) ----
            status = fusion.fuse(fusion.get_latest_ir(), last_boxes, fw, fh)
            target_box = status["target_box"]
            position = ct.compute_position(target_box, fw, fh) if target_box else None

            # ---- Kontrol servo (hanya di frame deteksi, agar bus tidak dibanjiri) ----
            locked = False
            if is_detect_frame:
                mode = "hold"
                if position is not None:
                    # AIM: lacak begitu kamera lihat api (tanpa menunggu fusi).
                    mode = "track"
                    err_px = position["err_px"]
                    if err_px > DEADZONE_PX:
                        yaw += YAW_SIGN * position["err_x"] * YAW_GAIN_DEG
                        pitch += PITCH_SIGN * position["err_y"] * PITCH_GAIN_DEG
                        yaw = _clamp(yaw, YAW_MIN, YAW_MAX)
                        pitch = _clamp(pitch, PITCH_MIN, PITCH_MAX)
                        _move(port, pkt, YAW_ID, yaw)
                        _move(port, pkt, PITCH_ID, pitch)
                    locked = err_px <= LOCK_PX
                elif status["ir_hot"] and status["ir_x"] is not None:
                    # FALLBACK: kamera hilang target, IR panas -> geser yaw pelan ke arah IR.
                    mode = "ir-seek"
                    yaw += YAW_SIGN * status["ir_x"] * FALLBACK_YAW_GAIN
                    yaw = _clamp(yaw, YAW_MIN, YAW_MAX)
                    _move(port, pkt, YAW_ID, yaw)

                ready = status["fire_confirmed"] and locked
                fallback = f" ir->{status['fallback_dir']}" if status["fallback_dir"] else ""
                print(f"[{time.strftime('%H:%M:%S')}] mode={mode} "
                      f"cam={int(status['cam_present'])} conf={status['cam_conf']:.2f} "
                      f"ir_hot={int(status['ir_hot'])} agree={status['agree']} "
                      f"fused={status['fused']:.2f} lock={int(locked)} yaw={yaw:.1f} pitch={pitch:.1f} "
                      f"=> {'SIAP TEMBAK' if ready else 'aim'}{fallback}")

            ready = status["fire_confirmed"] and (position is not None and position["err_px"] <= LOCK_PX)

            # ---- Overlay: tracking (step2/ct) + panel fusi (step3) + status servo ----
            annotated = ct.draw_tracking_overlay(frame, last_boxes, target_box, position)
            annotated = fusion.draw_fusion_overlay(annotated, status)
            annotated = draw_servo_overlay(annotated, yaw, pitch, mode, ready)

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
    print("Memuat Otak S.A.F.E. Versi Nano (Step 4: Fusi + Servo)...")
    model = YOLO(ct.MODEL_PATH)

    port, pkt = setup_servo()

    Thread(target=fusion.ir_poll_loop, daemon=True).start()
    Thread(target=control_loop, args=(model, port, pkt), daemon=True).start()

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
