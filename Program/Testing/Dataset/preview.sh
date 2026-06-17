#!/usr/bin/env bash
# preview.sh — Live preview kamera Raspberry Pi via VLC, TANPA menyimpan file.
#
# Jalankan SEBELUM take_video.sh untuk cek framing/posisi kamera dulu.
# Tekan Ctrl+C di sini saat sudah puas dengan framing, lalu jalankan
# take_video.sh untuk rekaman sesungguhnya.
#
# Penggunaan:
#   ./preview.sh
#
# Di laptop, buka VLC:
#   Media > Open Network Stream > tcp/mjpeg://<IP_PI>:8888

set -euo pipefail

PORT=8888

echo "=== Preview kamera (tanpa rekam) ==="
echo "Buka VLC -> tcp/mjpeg://<IP_PI>:${PORT}"
echo "Tekan Ctrl+C untuk berhenti."
echo ""

rpicam-vid -t 0 --codec mjpeg --inline --listen -o "tcp://0.0.0.0:${PORT}" --nopreview
