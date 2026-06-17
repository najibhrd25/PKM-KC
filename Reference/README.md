# S.A.F.E — Paket Dokumentasi Arsitektur

Tiga berkas dalam paket ini:

| Berkas | Isi |
|---|---|
| `ARCHITECTURE.md` | Dokumen utama: filosofi desain, Event Bus, struktur folder, kontrak event, state machine, interface tiap modul, alur eksekusi, dependency injection, strategi testing, dan roadmap. **Baca ini lebih dulu.** |
| `config_reference.py` | Contoh `config.py` — semua parameter tuning & keamanan terpusat. Salin ke `safe/core/config.py`. |
| `orchestrator_reference.py` | Implementasi referensi lengkap Orchestrator (otak sistem). Salin ke `safe/orchestrator.py`. |
| `web_bridge_reference.py` | Implementasi referensi `WebBridge` (antarmuka web opsional: stream, status, joystick, mode). Salin ke `safe/web/web_bridge.py`. |

## Cara Memulai

1. Baca `ARCHITECTURE.md` bagian 1–5 untuk memahami konsep (Event Bus, kontrak event, state machine).
2. Buat struktur folder sesuai bagian 3.
3. Salin `IR.py`, `Servo.py`, `DAC.py` lama menjadi `_ir_driver.py`, `_servo_driver.py`, `_dac_driver.py` **tanpa mengubah logikanya**.
4. Implementasikan `core/` (event_bus, interfaces, events, state_machine, config) — spesifikasinya ada di bagian 2, 4, 5, 6.1.
5. Bungkus tiap driver dengan adapter (bagian 6.2–6.6).
6. Salin `orchestrator_reference.py` dan `config_reference.py`.
7. Rakit di `main.py` (bagian 8), jalankan dengan `FakeDetector`.
8. Uji bertahap sesuai strategi testing (bagian 9).

## Prinsip yang Tidak Boleh Dilanggar

- **Modul tidak saling memanggil langsung** — selalu lewat Event Bus.
- **Kontrak event stabil** — `FakeDetector` dan `YOLODetector` mengeluarkan payload identik, sehingga bisa ditukar tanpa menyentuh modul lain.
- **Batas keamanan audio** (`AMPLITUDE_MAX_SAFE`, `AUDIO_MAX_DURATION`, cooldown) ditegakkan di kode, bukan opsional.
- **Driver lama tidak diubah** — hanya dibungkus adapter.

## Status YOLO

Modul deteksi sengaja dikosongkan. `FakeDetector` mengisi perannya untuk testing penuh tanpa kamera/api. Saat model siap, implementasikan `YOLODetector` dengan kontrak yang sama lalu ganti satu baris di `main.py`.