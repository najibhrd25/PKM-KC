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
#   ./take_video.sh <nama_skenario> [durasi_detik] [width] [height] [fps]
#
# Contoh:
#   ./take_video.sh api_jarak1m 60
#   ./take_video.sh api_gelap        # durasi default 30 detik
#   ./take_video.sh api_hd 60 1920 1080 30
#
# Resolusi & fps maksimum yang didukung sensor ov5647
# (cek: rpicam-hello --list-cameras):
#   640x480 (default, maks 62.5 fps) | 1296x972 (maks 46.3 fps)
#   1920x1080 (maks 32.8 fps)        | 2592x1944 (maks 15.6 fps)
#
# Hasil rekaman disimpan di: Dataset/raw/<nama_skenario>.mjpeg

set -euo pipefail

NAME="${1:?Nama skenario wajib diisi. Contoh: ./take_video.sh api_jarak1m 60}"
DURATION_SEC="${2:-30}"
WIDTH="${3:-640}"
HEIGHT="${4:-480}"
FPS="${5:-30}"
DURATION_MS=$((DURATION_SEC * 1000))

OUT_DIR="$(cd "$(dirname "$0")" && pwd)/raw"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/${NAME}.mjpeg"

if [ -f "$OUT_FILE" ]; then
    read -r -p "File '$OUT_FILE' sudah ada. Timpa? (y/n) " CONFIRM
    [ "$CONFIRM" = "y" ] || { echo "Dibatalkan."; exit 1; }
fi

echo "=== Rekam '$NAME' selama ${DURATION_SEC} detik (${WIDTH}x${HEIGHT} @ ${FPS}fps) ==="
echo "Output : $OUT_FILE"
echo ""

rpicam-vid -t "$DURATION_MS" --codec mjpeg --inline -o "$OUT_FILE" --nopreview \
    --width "$WIDTH" --height "$HEIGHT" --framerate "$FPS"

echo ""
echo "Selesai. Tersimpan: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
