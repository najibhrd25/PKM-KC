#!/usr/bin/env bash
# take_video.sh — Rekam video dataset SAFE dari kamera Raspberry Pi.
#
# Rekam LANGSUNG ke file (tanpa streaming bersamaan) supaya hasilnya selalu
# utuh. Kalau perlu cek framing/posisi kamera dulu, jalankan preview.sh
# SEBELUM script ini (preview tidak menyimpan file, hanya live view).
#
# Jalankan LANGSUNG DI RASPBERRY PI. Membutuhkan rpicam-vid.
#
# Penggunaan:
#   ./take_video.sh <nama_skenario> [durasi_detik]
#
# Contoh:
#   ./take_video.sh api_jarak1m 60
#   ./take_video.sh api_gelap        # durasi default 30 detik
#
# Hasil rekaman disimpan di: Dataset/raw/<nama_skenario>.mjpeg

set -euo pipefail

NAME="${1:?Nama skenario wajib diisi. Contoh: ./take_video.sh api_jarak1m 60}"
DURATION_SEC="${2:-30}"
DURATION_MS=$((DURATION_SEC * 1000))

OUT_DIR="$(cd "$(dirname "$0")" && pwd)/raw"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/${NAME}.mjpeg"

if [ -f "$OUT_FILE" ]; then
    read -r -p "File '$OUT_FILE' sudah ada. Timpa? (y/n) " CONFIRM
    [ "$CONFIRM" = "y" ] || { echo "Dibatalkan."; exit 1; }
fi

echo "=== Rekam '$NAME' selama ${DURATION_SEC} detik ==="
echo "Output : $OUT_FILE"
echo ""

rpicam-vid -t "$DURATION_MS" --codec mjpeg --inline -o "$OUT_FILE" --nopreview

echo ""
echo "Selesai. Tersimpan: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
