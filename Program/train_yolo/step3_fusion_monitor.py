"""
Monitor Fusi Sensor: Kamera (YOLO) + 5 Sensor IR - Raspberry Pi
================================================================

Program prototipe MANDIRI (belum menggerakkan servo) untuk memvalidasi logika
fusi antara deteksi api dari kamera (camera_tracker.py / YOLO) dan deteksi
panas dari 5 sensor IR (Program/Testing/IR.py).

Empat peran fusi (semua aktif):
    a) Konfirmasi AND-gate : api NYATA hanya bila IR panas DAN kamera deteksi
                             (confidence >= ambang) -> tekan alarm palsu.
    b) Cek arah setuju     : bandingkan arah IR terpanas vs posisi target kamera;
                             juga memilih box yang paling searah IR bila deteksi >1.
    c) Fallback IR         : bila kamera hilang target tapi IR panas, sarankan
                             arah (kiri/kanan) untuk pandu yaw servo nanti.
    d) Skor gabungan       : satu skor keyakinan (bobot IR + confidence YOLO),
                             dipenalti bila arah tidak setuju.

Asumsi hardware (dikonfirmasi):
    - 5 sensor IR horizontal kiri->kanan (sektor yaw).
    - IR array IKUT turret (co-aligned dengan kamera): saat turret tepat mengarah
      ke api, IR tengah (IR3) paling panas & kamera err_x ~ 0.

Cara pakai (jalankan dari folder train_yolo/ supaya MODEL_PATH relatif valid):
    python fusion_monitor.py

Stream status fusi: http://<ip-pi>:8081/stream.mjpg
Tekan Ctrl+C untuk berhenti.
"""

import os
import sys
import time
from http.server import ThreadingHTTPServer
from threading import Lock, Thread

import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

# --- Reuse fungsi tracker (dijalankan dari train_yolo/, jadi import langsung) ---
import camera_tracker as ct

# --- Reuse driver IR dari Program/Testing/IR.py ---
_IR_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Testing"
)
sys.path.insert(0, os.path.abspath(_IR_DIR))
import IR  # noqa: E402  (import setelah sys.path disisipkan)


# ======================= KONSTANTA BISA-ATUR =======================
YOLO_CONF_THRESHOLD = 0.60            # ambang confidence kamera (dari config.py)
IR_DIFF_THRESHOLD = IR.DIFF_THRESHOLD  # ambang "panas" diferensial (dari IR.py)
IR_CONF_SCALE = 3000.0               # skala normalisasi selisih raw -> 0..1  [TUNING]
AGREE_TOL = 0.4                      # |cam_x - ir_x| <= ini dianggap arah setuju
W_IR, W_CAM = 0.5, 0.5              # bobot skor gabungan
DISAGREE_PENALTY = 0.5              # faktor skor bila arah IR vs kamera tak setuju
FUSED_THRESHOLD = 0.6              # ambang keputusan "API TERKONFIRMASI"
IR_REVERSE = True                # True bila urutan sensor terbalik terhadap err_x kamera
IR_READ_INTERVAL = 0.1            # detik antar pembacaan IR

# Posisi horizontal ternormalisasi tiap sensor (index 0..4): (i-2)/2 -> [-1..+1]
N_IR = 6
_IR_POS = [(i - (N_IR - 1) / 2) / ((N_IR - 1) / 2) for i in range(N_IR)]  # -1,-0.5,0,0.5,1


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _ir_pos(index):
    """Posisi ternormalisasi sensor ke-index, hormati IR_REVERSE."""
    pos = _IR_POS[index]
    return -pos if IR_REVERSE else pos


# ======================= STATE BERSAMA (IR) =======================
_ir_lock = Lock()
_latest_ir = []  # list dict {raw, voltage} dari read_all_sensors; kosong sebelum ada data


def ir_poll_loop():
    """Thread daemon: baca 5 sensor IR terus-menerus, simpan ke _latest_ir."""
    global _latest_ir
    channels = IR.init_sensors()
    print(f"[IR] {len(channels)} sensor siap.")
    while True:
        readings = IR.read_all_sensors(channels)
        with _ir_lock:
            _latest_ir = readings
        time.sleep(IR_READ_INTERVAL)


def get_latest_ir():
    with _ir_lock:
        return list(_latest_ir)


# ======================= LOGIKA FUSI (murni, tanpa I/O) =======================
def fuse(ir_readings, boxes, frame_w, frame_h):
    """Gabungkan pembacaan IR + deteksi kamera menjadi status fusi.

    ir_readings : list dict {raw, voltage} (boleh kosong bila IR belum siap).
    boxes       : list box (x1,y1,x2,y2,conf,cls_name) dari YOLO.
    Return dict status lengkap.
    """
    status = {
        "ir_hot": False, "ir_x": None, "ir_conf": 0.0, "idx_max": None,
        "selisih": 0.0, "raws": [],
        "cam_present": False, "cam_conf": 0.0, "cam_x": None, "target_box": None,
        "agree": None, "fused": 0.0, "fire_confirmed": False,
        "fallback_dir": None,
    }

    # ---------- Sisi IR (replikasi logika diferensial IR.py) ----------
    if ir_readings:
        raws = [r["raw"] for r in ir_readings]
        status["raws"] = raws
        idx_max = raws.index(max(raws))
        others = raws[:idx_max] + raws[idx_max + 1:]
        avg_others = sum(others) / len(others) if others else 0.0
        selisih = raws[idx_max] - avg_others
        status["idx_max"] = idx_max
        status["selisih"] = selisih
        status["ir_hot"] = selisih >= IR_DIFF_THRESHOLD
        status["ir_conf"] = _clamp(selisih / IR_CONF_SCALE, 0.0, 1.0)

        # Arah IR: centroid berbobot (lebih halus dari sekadar sensor terpanas).
        mean_raw = sum(raws) / len(raws)
        weights = [max(0.0, r - mean_raw) for r in raws]
        wsum = sum(weights)
        if wsum > 0:
            status["ir_x"] = sum(_ir_pos(i) * w for i, w in enumerate(weights)) / wsum

    ir_x = status["ir_x"]

    # ---------- Sisi kamera ----------
    positions = [(b, ct.compute_position(b, frame_w, frame_h)) for b in boxes]
    target = None
    if positions:
        if ir_x is not None and len(positions) > 1:
            # Prioritas arah: pilih box yang err_x-nya paling dekat dengan arah IR.
            target = min(positions, key=lambda bp: abs(bp[1]["err_x"] - ir_x))
        else:
            # Selain itu: confidence tertinggi.
            target = max(positions, key=lambda bp: bp[1]["conf"])

    if target is not None:
        status["cam_present"] = True
        status["cam_conf"] = target[1]["conf"]
        status["cam_x"] = target[1]["err_x"]
        status["target_box"] = target[0]

    cam_x = status["cam_x"]

    # ---------- Cek arah setuju (tujuan b) ----------
    # IR array kasar (5 sensor), jadi cukup cek SISI yang sama (tanda sama),
    # atau dua-duanya dekat pusat (dalam AGREE_TOL). Tidak menuntut besaran identik.
    if ir_x is not None and cam_x is not None:
        status["agree"] = (cam_x * ir_x >= 0) or (abs(cam_x - ir_x) <= AGREE_TOL)

    # ---------- Skor gabungan (tujuan d) ----------
    fused = W_IR * status["ir_conf"] + W_CAM * status["cam_conf"]
    if status["agree"] is False:
        fused *= DISAGREE_PENALTY
    status["fused"] = _clamp(fused, 0.0, 1.0)

    # ---------- Konfirmasi AND-gate (tujuan a) + keputusan akhir ----------
    confirmed = (status["ir_hot"] and status["cam_present"]
                 and status["cam_conf"] >= YOLO_CONF_THRESHOLD)
    status["fire_confirmed"] = confirmed and status["fused"] >= FUSED_THRESHOLD

    # ---------- Fallback IR (tujuan c) ----------
    if not status["cam_present"] and status["ir_hot"] and ir_x is not None:
        if ir_x < -0.15:
            status["fallback_dir"] = "KIRI"
        elif ir_x > 0.15:
            status["fallback_dir"] = "KANAN"
        else:
            status["fallback_dir"] = "TENGAH"

    return status


# ======================= TAMPILAN =======================
def _fmt(value, fmt="{:+.2f}"):
    return fmt.format(value) if value is not None else " --"


def print_status(status):
    idx = status["idx_max"]
    ir_label = f"IR{idx + 1}" if idx is not None else "IR?"
    decision = "FIRE-CONFIRMED" if status["fire_confirmed"] else "no-fire"
    fallback = f" fallback->{status['fallback_dir']}" if status["fallback_dir"] else ""
    print(f"[{time.strftime('%H:%M:%S')}] "
          f"{ir_label} selisih={status['selisih']:.0f} hot={int(status['ir_hot'])} "
          f"ir_x={_fmt(status['ir_x'])} | "
          f"cam={int(status['cam_present'])} conf={status['cam_conf']:.2f} cam_x={_fmt(status['cam_x'])} | "
          f"agree={status['agree']} fused={status['fused']:.2f} => {decision}{fallback}")


def draw_fusion_overlay(frame, status):
    """Tambahkan panel teks fusi di kanan atas frame."""
    fh, fw = frame.shape[:2]
    x0 = fw - 250
    green, red, yellow, white = (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 255, 255)

    # Bar mini tiap sensor IR (reuse render_bar dari IR.py, width kecil).
    lines = []
    for i, raw in enumerate(status["raws"]):
        mark = " <" if i == status["idx_max"] and status["ir_hot"] else ""
        lines.append((f"IR{i + 1} {IR.render_bar(raw, width=10)}{mark}", white))

    lines.append((f"ir_x  : {_fmt(status['ir_x'])}", white))
    lines.append((f"cam_x : {_fmt(status['cam_x'])} c={status['cam_conf']:.2f}", white))
    agree_color = green if status["agree"] else (red if status["agree"] is False else white)
    lines.append((f"agree : {status['agree']}", agree_color))
    lines.append((f"fused : {status['fused']:.2f}", yellow))
    if status["fire_confirmed"]:
        lines.append(("API TERKONFIRMASI", red))
    elif status["fallback_dir"]:
        lines.append((f"IR-only -> {status['fallback_dir']}", yellow))
    else:
        lines.append(("no-fire", green))

    for i, (text, color) in enumerate(lines):
        cv2.putText(frame, text, (x0, 25 + i * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    return frame


# ======================= LOOP KAMERA + FUSI =======================
def monitor_loop(model):
    picam2 = Picamera2()
    cam_config = picam2.create_preview_configuration(
        main={"format": "BGR888", "size": ct.FRAME_SIZE}
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

            is_detect_frame = frame_idx % ct.DETECT_EVERY == 0
            if is_detect_frame:
                results = model.predict(frame, conf=ct.CONF, imgsz=ct.IMG_SIZE, verbose=False)
                last_boxes = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf_val = float(box.conf[0])
                    cls_name = model.names[int(box.cls[0])]
                    last_boxes.append((x1, y1, x2, y2, conf_val, cls_name))

            status = fuse(get_latest_ir(), last_boxes, fw, fh)
            target_box = status["target_box"]
            position = ct.compute_position(target_box, fw, fh) if target_box else None

            if is_detect_frame:
                print_status(status)

            # Overlay tracking (reuse) + panel fusi.
            annotated = ct.draw_tracking_overlay(frame, last_boxes, target_box, position)
            annotated = draw_fusion_overlay(annotated, status)

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
    print("Memuat Otak S.A.F.E. Versi Nano (Fusion Monitor)...")
    model = YOLO(ct.MODEL_PATH)

    Thread(target=ir_poll_loop, daemon=True).start()
    Thread(target=monitor_loop, args=(model,), daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", ct.PORT), ct.StreamingHandler)
    print(f"Stream fusi siap: http://<ip-pi>:{ct.PORT}/stream.mjpg")
    print("Tekan Ctrl+C untuk berhenti.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
