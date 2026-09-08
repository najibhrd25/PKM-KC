import type { JoystickPosition } from '@/data/types';

// ============================================================================
// S.A.F.E. Raspberry Pi API Client
// ============================================================================
// Semua komunikasi HTTP antara mobile dashboard dan Raspberry Pi terpusat
// di file ini. Ganti RASPBERRY_PI_IP saat pengetesan sesuai IP Pi di jaringan
// Wi-Fi yang sama.
// ============================================================================

export const RASPBERRY_PI_IP = '10.7.101.64'; // Ganti dengan IP Pi Anda
const BASE_URL = `http://${RASPBERRY_PI_IP}:8000`;

// Timeout default untuk setiap request (ms)
const REQUEST_TIMEOUT = 5000;

// ---------- Tipe payload ----------

export interface SetModePayload {
  auto: boolean;
}

export interface TriggerPayload {
  action: 'shoot';
  frequency: number;
  amplitude?: number;
  duration?: number;
  waveform?: string;
}

export interface ApiResponse {
  ok: boolean;
  [key: string]: unknown;
}

// ---------- Helper ----------

async function safeFetch(
  url: string,
  options?: RequestInit,
): Promise<ApiResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return (await response.json()) as ApiResponse;
  } catch (error: unknown) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.warn(`[SAFE-API] Timeout saat akses ${url}`);
      throw new Error('Request timeout — Raspberry Pi tidak merespons.');
    }
    console.error(`[SAFE-API] Gagal: ${url}`, error);
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * 1. SET MODE — Mengubah mode operasi (AUTO / MANUAL)
 *
 * Endpoint Pi: POST /cmd/mode
 * Payload:     { mode: "auto" | "manual" }
 */
export async function setSafeMode(payload: SetModePayload): Promise<ApiResponse> {
  const mode = payload.auto ? 'auto' : 'manual';
  return safeFetch(`${BASE_URL}/cmd/mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
}

/**
 * 2. SERVO JOG — Mengirim posisi joystick sebagai delta sudut servo
 *
 * Endpoint Pi: POST /cmd/jog
 * Payload:     { d_yaw: float, d_pitch: float }
 *
 * Koordinat joystick (x, y dalam piksel) dikonversi menjadi delta derajat.
 * Sensitivitas diatur oleh JOG_SENSITIVITY.
 */
const JOG_SENSITIVITY = 0.15;

export async function sendServoPosition(position: JoystickPosition): Promise<ApiResponse> {
  const d_yaw = position.x * JOG_SENSITIVITY;
  const d_pitch = -position.y * JOG_SENSITIVITY; // Inversi Y: atas = pitch naik

  return safeFetch(`${BASE_URL}/cmd/jog`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ d_yaw, d_pitch }),
  });
}

/**
 * 3. AUDIO CMD — Mengontrol pemancaran gelombang akustik
 *
 * Endpoint Pi: POST /cmd/audio
 * Payload:     { action: "play", freq: number, amplitude?: number, duration?: number, waveform?: string }
 */
export async function triggerAcousticPulse(payload: TriggerPayload): Promise<ApiResponse> {
  return safeFetch(`${BASE_URL}/cmd/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'play',
      freq: payload.frequency,
      amplitude: payload.amplitude,
      duration: payload.duration,
      waveform: payload.waveform,
    }),
  });
}

/**
 * STOP AUDIO — Menghentikan pemancaran gelombang akustik segera
 *
 * Endpoint Pi: POST /cmd/audio
 * Payload:     { action: "stop" }
 */
export async function stopAudio(): Promise<ApiResponse> {
  return safeFetch(`${BASE_URL}/cmd/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'stop' }),
  });
}

/**
 * SERVO HOME — Mengembalikan servo ke titik tengah (center)
 *
 * Endpoint Pi: POST /cmd/servo
 * Payload:     { action: "home" }
 */
export async function homeServo(): Promise<ApiResponse> {
  return safeFetch(`${BASE_URL}/cmd/servo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'home' }),
  });
}

/**
 * SERVO STOP (TORQUE OFF) — Mematikan torsi servo untuk keamanan
 *
 * Endpoint Pi: POST /cmd/servo
 * Payload:     { action: "torque_off" }
 */
export async function stopServo(): Promise<ApiResponse> {
  return safeFetch(`${BASE_URL}/cmd/servo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'torque_off' }),
  });
}

/**
 * 4. HEARTBEAT — Ping berkala untuk memberi tahu Pi bahwa UI masih aktif
 *
 * Endpoint Pi: POST /heartbeat
 *
 * Harus dikirim setiap 2-3 detik selama mode MANUAL aktif.
 * Jika Pi tidak menerima heartbeat selama WEB_HEARTBEAT_TIMEOUT (5 detik),
 * sistem otomatis kembali ke mode AUTO demi keamanan.
 */
export async function sendHeartbeat(): Promise<ApiResponse | undefined> {
  try {
    return await safeFetch(`${BASE_URL}/heartbeat`, {
      method: 'POST',
    });
  } catch {
    // Heartbeat gagal bukan error kritis — cukup di-log
    console.warn('[SAFE-API] Heartbeat gagal mencapai Raspberry Pi.');
    return undefined;
  }
}

/**
 * 5. STREAM URL — URL untuk MJPEG live camera stream
 *
 * Digunakan langsung sebagai source Image di VideoPanel.
 * Bukan fungsi fetch, hanya getter URL.
 */
export function getCameraStreamUrl(): string {
  return `${BASE_URL}/stream`;
}

/**
 * 6. SSE EVENTS URL — URL untuk Server-Sent Events (status real-time)
 *
 * Digunakan untuk membuat EventSource di client.
 */
export function getEventsUrl(): string {
  return `${BASE_URL}/events`;
}
