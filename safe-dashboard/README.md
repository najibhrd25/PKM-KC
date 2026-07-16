# S.A.F.E. Web Dashboard (Vite PWA)

Dashboard berbasis web (Progressive Web App) untuk monitoring dan kontrol sistem pemadam kebakaran akustik pintar **S.A.F.E.** (Smart Acoustic Fire Extinguisher).

---

## 🔌 Panduan Koneksi API & Integrasi Raspberry Pi

Semua komunikasi data antara dashboard ini dengan Raspberry Pi dipusatkan pada satu file utama. Berikut adalah panduan singkat jika Anda ingin menghubungkan atau memodifikasi integrasi API:

### 1. File Konfigurasi API Utama
Konfigurasi alamat IP dan endpoint API didefinisikan di:
* 🔗 **[safeApi.ts](file:///Users/macbookpro/Documents/PKM%20NO%20MERCY/safe-dashboard/src/services/safe-api/safeApi.ts)**

Di dalam berkas tersebut, cari baris berikut untuk mengganti IP Raspberry Pi agar sesuai dengan jaringan Wi-Fi lokal Anda:
```typescript
export const RASPBERRY_PI_IP = '192.168.1.15'; // Ganti dengan IP Raspberry Pi Anda
const BASE_URL = `http://${RASPBERRY_PI_IP}:8000`;
```

### 2. File Penggunaan API di Komponen UI
Jika Anda ingin melihat bagaimana fungsi API dipanggil untuk mengontrol perangkat keras, periksa file-file berikut:
* **Kendali Joystick (Servo)**: Posisi koordinat joystick dikirim ke API `/cmd/jog` melalui hook **[useJoystick.ts](file:///Users/macbookpro/Documents/PKM%20NO%20MERCY/safe-dashboard/src/features/mission-control/hooks/useJoystick.ts)**.
* **Kendali Mode & Status**: Mengubah mode AUTO/MANUAL serta mengirim `/heartbeat` berkala dikelola di global store **[useSystemState.ts](file:///Users/macbookpro/Documents/PKM%20NO%20MERCY/safe-dashboard/src/store/useSystemState.ts)**.
* **Aksi Tembak & Monitor Kamera**: Aksi penembakan akustik manual (`/cmd/shoot`) dan MJPEG camera stream (`/stream`) diintegrasikan di screen utama **[MissionControlScreen.tsx](file:///Users/macbookpro/Documents/PKM%20NO%20MERCY/safe-dashboard/src/features/mission-control/screens/MissionControlScreen.tsx)** dan komponen **[VideoPanel.tsx](file:///Users/macbookpro/Documents/PKM%20NO%20MERCY/safe-dashboard/src/features/mission-control/components/VideoPanel.tsx)**.

### 3. Skema Endpoint Raspberry Pi (FastAPI)
Dashboard ini menembak endpoint-endpoint berikut di sisi Raspberry Pi (dapat Anda sesuaikan di berkas **[web_bridge.py](file:///Users/macbookpro/Documents/PKM%20NO%20MERCY/Smart-Acoustic-Fire-Extinguisher/safe/web/web_bridge.py)** pada repo Pi):
* `POST /cmd/mode` : Mengubah mode sistem (`{ "mode": "auto" | "manual" }`).
* `POST /cmd/jog` : Mengirim pergerakan servo (`{ "d_yaw": float, "d_pitch": float }`).
* `POST /cmd/shoot` : Memicu tembakan akustik (`{ "frequency": number }`).
* `POST /heartbeat` : Ping pengaman dari dashboard tiap 2 detik ketika mode MANUAL aktif.
* `GET /stream` : Stream MJPEG real-time dari kamera Pi.
* `GET /events` : Stream status sensor real-time menggunakan Server-Sent Events (SSE).

---

## 🚀 Cara Menjalankan Project

### 1. Install Dependensi
```bash
pnpm install
```

### 2. Jalankan Mode Development (Local Server)
```bash
pnpm run dev
```
Setelah berjalan, buka browser di alamat yang tertera (biasanya `http://localhost:5173`).

### 3. Build untuk Produksi (PWA Siap Distribusi)
```bash
pnpm run build
```
Hasil build akan tersimpan di dalam folder `dist/` dan siap dideploy ke server static mana pun.
