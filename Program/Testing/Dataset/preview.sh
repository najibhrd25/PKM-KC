#!/usr/bin/env bash
# preview.sh — Live preview kamera Raspberry Pi via VLC, TANPA menyimpan file.
#
# Jalankan SEBELUM take_video.sh untuk cek framing/posisi kamera dulu.
# Tekan Ctrl+C di sini saat sudah puas dengan framing, lalu jalankan
# take_video.sh untuk rekaman sesungguhnya.
#
# Penggunaan:
#   ./preview.sh [width] [height] [fps]
#
# Contoh:
#   ./preview.sh             # default 640x480 @ 30fps
#   ./preview.sh 1920 1080 30
#
# Di laptop, buka VLC:
#   Media > Open Network Stream > tcp/mjpeg://<IP_PI>:8888

set -euo pipefail

WIDTH="${1:-640}"
HEIGHT="${2:-480}"
FPS="${3:-30}"
PORT=8888

echo "=== Preview kamera (tanpa rekam) — ${WIDTH}x${HEIGHT} @ ${FPS}fps ==="
echo "Buka VLC -> tcp/mjpeg://<IP_PI>:${PORT}"
echo "Tekan Ctrl+C untuk berhenti."
echo ""

rpicam-vid -t 0 --codec mjpeg --inline --listen -o "tcp://0.0.0.0:${PORT}" --nopreview \
    --width "$WIDTH" --height "$HEIGHT" --framerate "$FPS"


# # Default: 640x480 @ 30fps
# ./take_video.sh api_jarak1m 60

# # Custom resolusi + fps (urutan: nama, durasi, width, height, fps)
# ./take_video.sh api_hd 60 1920 1080 30

# # Preview juga bisa diatur sama
# ./preview.sh 1920 1080 30
