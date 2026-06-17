#!/usr/bin/env bash
# take_video.sh — Rekam video dataset SAFE dari kamera Raspberry Pi,
# dengan preview live via VLC di laptop selagi merekam.
#
# Jalankan LANGSUNG DI RASPBERRY PI (folder ini, atau folder mana pun
# selama path tujuan disesuaikan). Membutuhkan rpicam-vid dan nc (netcat).
#
# Penggunaan:
#   ./take_video.sh <nama_skenario> [durasi_detik]
#
# Contoh:
#   ./take_video.sh api_jarak1m 60
#   ./take_video.sh api_gelap        # durasi default 30 detik
#
# Preview saat rekam (dari laptop, buka VLC):
#   Media > Open Network Stream > tcp/mjpeg://<IP_PI>:8888
#
# Hasil rekaman disimpan di: Dataset/raw/<nama_skenario>.mjpeg

set -euo pipefail

NAME="${1:?Nama skenario wajib diisi. Contoh: ./take_video.sh api_jarak1m 60}"
DURATION_SEC="${2:-30}"
DURATION_MS=$((DURATION_SEC * 1000))
PORT=8888

OUT_DIR="$(cd "$(dirname "$0")" && pwd)/raw"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/${NAME}.mjpeg"

if [ -f "$OUT_FILE" ]; then
    read -r -p "File '$OUT_FILE' sudah ada. Timpa? (y/n) " CONFIRM
    [ "$CONFIRM" = "y" ] || { echo "Dibatalkan."; exit 1; }
fi

echo "=== Rekam '$NAME' selama ${DURATION_SEC} detik ==="
echo "Preview : buka VLC -> tcp/mjpeg://<IP_PI>:${PORT}"
echo "Output  : $OUT_FILE"
echo ""

rpicam-vid -t "$DURATION_MS" --codec mjpeg --inline -o - \
    | tee "$OUT_FILE" \
    | nc -l -p "$PORT"

echo ""
echo "Selesai. Tersimpan: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
