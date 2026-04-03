# 🛡️ S.A.F.E. (Smart Acoustic Fire Extinguisher) - Technical Specification
**Project PKM-KC - Informatics Engineering, ITS 2024**

Dokumen ini adalah acuan utama untuk pembangunan sistem Dashboard IoT S.A.F.E. menggunakan **Next.js (App Router)**. Fokus utama adalah pada presisi logika *State Management*, keamanan akses manual, dan estetika "Iron Man Startup".

---

## 🎨 Visual Identity & Theme
- **Primary Background:** `#000000` (Pitch Black).
- **Primary Accent:** `#DC2626` (Crimson Red).
- **Secondary Accent:** `#FFFFFF` (Pure White) & `#9CA3AF` (Muted Gray).
- **Typography:** Monospaced (JetBrains Mono / Roboto Mono) untuk data; Sans-serif (Inter/Geist) untuk UI.
- **UI Style:** Ultra-minimalist, Borderless (gunakan subtle shadows/inner glow untuk depth), Glassmorphism pada Modals.

---

## 🕹️ System State Machine (Logic Utama)

Sistem harus menangani 4 state utama yang dikelola melalui State Global (Context/Zustand):

1. **`OFF_STATE` (Cold Standby):**
   - Seluruh UI menggunakan CSS: `filter: grayscale(100%) opacity(40%) blur(1px);`.
   - Pointer events pada semua komponen adalah `none` (kecuali Power Button).
   - Teks sensor menampilkan `--` atau `NULL`.
   - Power Button di Header berdenyut (*pulse*) merah redup.

2. **`STARTUP_SEQUENCE` (The Iron Man Wake-up):**
   - Dipicu setelah User mengonfirmasi "YES" pada Power Toggle.
   - **Sequence (Staggered 500ms):**
     - `T+0ms`: Trigger audio `startup.mp3` (mechanical tek-tek-tek sound).
     - `T+500ms`: Filter Grayscale & Blur bertransisi ke `none` (0.8s duration).
     - `T+1000ms`: Camera Viewport *fade-in* (Placeholder: `/public/camera.jpg`).
     - `T+1500ms`: Angka Suhu & Hz melakukan animasi *rolling-numbers* hingga angka real-time.
     - `T+2000ms`: Logs memunculkan baris entri awal secara otomatis.

3. **`AUTO_MODE` (Sentinel Mode - Default):**
   - Sistem membaca data dari Pi 5 secara real-time.
   - Jika YOLO/IR mendeteksi api: UI berubah menjadi `Alert State` (Lampu header berkedip merah, Bounding box muncul).
   - Kontrol Manual (Joystick/Shoot) terkunci (Ikon Gembok Aktif).

4. **`MANUAL_MODE` (Maintenance Mode):**
   - Diaktifkan via Password (`ITS2024`).
   - Ikon Gembok terbuka.
   - **Logika Hardware:** Web mengirim `POST /api/mode` dengan payload `{ "auto": false }` ke Raspberry Pi.
   - User memegang kendali penuh atas Servo (via Joystick) dan Trigger Suara (via Shoot Button).

---

## 📱 Layout Specifications (Responsive Grid)

### A. Desktop View (Min-width: 1024px)
- **Top Navigation:** Logo (Left), Device Status [Online/Offline] (Center), Power Toggle (Right).
- **Main Layout (Grid 70/30):**
    - **Left Area:** Video Stream 16:9. Border-radius: 12px. Overlay: Bounding box merah dinamis + Target Reticle di tengah.
    - **Right Sidebar (Stack):**
        - `Sensor Card`: Real-time Temperature (Large font).
        - `Acoustic Card`: Active Frequency Display (30-60 Hz Meter).
        - `Tactical Card`: Joystick Bulat + Tombol "SHOOT" Merah di bawahnya.
- **Bottom Area:** Tabel Log Aktivitas (Full-width).

### B. Mobile View (Max-width: 1023px)
- **Header:** Sticky Navbar dengan Logo & Power Toggle.
- **Section 1 (Top):** Camera Feed **1:1 Aspect Ratio**. Full-width (Edge-to-edge).
- **Section 2 (Middle - Grid 2 Cols):**
    - `Col 1`: Sensor Info (Suhu & Hz tumpuk vertikal).
    - `Col 2`: Manual Controls (Joystick atas, Button "SHOOT" bawah - Ergonomis jempol kanan).
- **Section 3 (Bottom):** List Log Kejadian (Scrollable area).

---

## 🔒 Security & Interaction Flow

### Manual Control Authorization:
1. User menyentuh area Joystick/Shoot Button.
2. Muncul Modal Transparan: "AUTHORIZATION REQUIRED".
3. Input Password Field (Numeric/Text).
4. Jika sukses:
   - Kirim signal ke Pi 5.
   - State `isManual` = `true`.
   - Ikon Gembok pada UI berubah menjadi terbuka.

### Power Off Flow:
1. User menekan Power Button saat sistem ON.
2. Muncul Konfirmasi: "Shutdown All Systems?".
3. Jika "YES": Balik ke `OFF_STATE` (Grayscale filter aktif seketika).

---

## 📡 Data & API Contract

### Database (Supabase):
- **Table `logs`:** `id`, `created_at`, `event_type` (Fire/Check), `status`, `video_url`, `confidence`.

### API Endpoints (Next.js to Pi 5):
- `GET /api/stream`: Proxy ke MJPEG stream Raspberry Pi.
- `POST /api/servo`: Kirim koordinat `{ x: number, y: number }`.
- `POST /api/trigger`: Kirim command `{ action: "shoot", frequency: number }`.

---

## 📁 Required Assets in `/public`
- `camera-placeholder.jpg`: Gambar statis ruang panel listrik (untuk dev).
- `startup.mp3`: Sound effect mechanical/startup.
- `alert.mp3`: Sound effect saat api terdeteksi.

---
**"Built for Precision. Designed for Safety."**
**S.A.F.E. Team - 2024**
