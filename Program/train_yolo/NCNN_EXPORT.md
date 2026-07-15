# Export Model ke NCNN (Percepatan Inferensi di Raspberry Pi)

Dokumen ini menjelaskan cara mempercepat inferensi YOLO di Raspberry Pi (CPU ARM,
tanpa GPU). Ulangi langkah ini setiap kali ada model baru hasil training
(`best.pt` baru) yang ingin dipakai di `stream_webcam.py`.

## Kenapa bukan `half=True` / FP16 langsung di PyTorch?

Precision half (`quantize=16` di predict, dulu bernama `half`) di backend
PyTorch CPU **hampir tidak memberi percepatan** karena CPU biasa (termasuk ARM)
tetap menghitung di FP32 secara internal — FP16 itu manfaatnya khusus untuk GPU.
Hasil benchmark di Pi ini (model `train-4/weights/best.pt`, dummy image 640x640):

| Metode | Waktu/inferensi | Speedup |
|---|---|---|
| PyTorch `.pt` FP32 | ~450 ms | baseline |
| PyTorch `.pt` `quantize=16` | ~428 ms | ~5% (diabaikan) |
| **NCNN FP16 (export)** | **~154 ms** | **~2.9x** |

NCNN adalah runtime inferensi Tencent yang punya kernel teroptimasi untuk ARM
(NEON), sehingga FP16 di sana benar-benar dieksekusi lebih cepat, bukan cuma
diemulasi seperti di PyTorch.

## Langkah export

1. Pastikan package `ncnn` terpasang di venv (sekali saja, tidak perlu diulang
   tiap training baru):
   ```bash
   cd "/home/safe/Smart-Acoustic-Fire-Extinguisher"
   .venv/bin/pip install ncnn
   ```

2. Export `best.pt` ke format NCNN dengan bobot FP16. Ganti path `best.pt` kalau
   model hasil training terbaru ada di folder `train-N` yang berbeda:
   ```bash
   cd "/home/safe/Smart-Acoustic-Fire-Extinguisher/train yolo"
   ../.venv/bin/python3 -c "
   from ultralytics import YOLO
   model = YOLO('train-4/weights/best.pt')
   path = model.export(format='ncnn', imgsz=640, quantize=16)
   print('EXPORTED TO:', path)
   "
   ```
   Proses ini butuh ~30-45 detik dan menghasilkan folder
   `train-4/weights/best_ncnn_model/` (berisi file `.param`, `.bin`, dan
   `metadata.yaml`). Catatan: `imgsz` harus sama dengan `imgsz` saat training
   (cek di `train-N/args.yaml`, kunci `imgsz:`).

3. Update `MODEL_PATH` di `stream_webcam.py` supaya menunjuk ke folder hasil
   export (bukan file `.pt`):
   ```python
   MODEL_PATH = 'train-4/weights/best_ncnn_model'
   ```

4. Jalankan `stream_webcam.py` seperti biasa — cara pakainya (`model.predict(...)`)
   sama persis untuk model NCNN maupun `.pt`, tidak ada kode lain yang perlu
   diubah.

## Cara benchmark ulang (kalau ingin verifikasi speedup di model/kondisi baru)

```bash
cd "/home/safe/Smart-Acoustic-Fire-Extinguisher/train yolo"
../.venv/bin/python3 -c "
from ultralytics import YOLO
import numpy as np, time

dummy = np.zeros((640, 640, 3), dtype='uint8')
model = YOLO('train-4/weights/best_ncnn_model')  # atau best.pt untuk baseline
model.predict(dummy, verbose=False)  # warmup, tidak dihitung

t0 = time.time()
for _ in range(8):
    model.predict(dummy, verbose=False)
t = (time.time() - t0) / 8
print(f'{t*1000:.1f} ms/inferensi (~{1/t:.1f} inferensi/detik)')
"
```

## Catatan / gotcha

- Warning `Unable to automatically guess model task` saat load model NCNN itu
  **aman diabaikan** — ultralytics tetap otomatis pakai `task=detect`.
- Model NCNN adalah **mesin inferensi berbeda**, bukan model baru — bobot dan
  akurasi deteksi persis sama dengan `best.pt`, cuma lebih cepat dieksekusi.
- Kalau retraining menghasilkan folder baru (`train-5`, dst.), ulangi langkah 2
  dan 3 di atas dengan path yang sesuai. Folder `best_ncnn_model/` lama tidak
  otomatis ter-update.
- Setting lain yang juga memengaruhi kecepatan/akurasi (bisa dituning bareng
  NCNN ini) ada di bagian atas `stream_webcam.py`:
  - `IMG_SIZE` — resolusi inferensi, harus sama dengan `imgsz` training.
  - `DETECT_EVERY` — jalankan YOLO tiap N frame, sisanya reuse box terakhir.
  - `CONF` — ambang confidence deteksi.
  - `FRAME_SIZE` — resolusi capture kamera, idealnya rasio aspek sama dengan
    dataset training (cek video sumber di `Program/Testing/Dataset/raw/`).
