import type { ActivityLogItem, StartupPhase } from './types';

export const MANUAL_MODE_PASSWORD = 'ITS2024';

export const initialStartupPhase: StartupPhase = {
  audioPlayed: false,
  filterRemoved: false,
  cameraVisible: false,
  numbersRolled: false,
  logsInitialized: false,
};

export const STARTUP_TIMELINE_MS = {
  audio: 0,
  filter: 500,
  camera: 1000,
  sensors: 1500,
  logs: 1800,
  autoMode: 2000,
} as const;

export const LIVE_SENSOR_SNAPSHOT = {
  temperature: 32,
  frequency: 45,
} as const;

export const INITIAL_ACTIVITY_LOGS: ActivityLogItem[] = [
  {
    id: 'log-1',
    time: '15:32:45',
    title: 'ACOUSTIC PULSE ACTIVE',
    detail: 'Memancarkan gelombang resonansi 45 Hz terus menerus ke pusat api (Amplitudo 100%)',
    tone: 'danger',
  },
  {
    id: 'log-2',
    time: '15:32:38',
    title: 'KUNCI TARGET API (LOCKED)',
    detail: 'Servo mengunci koordinat api (Pan: 92.4°, Tilt: 44.1°), nozzle tepat menghadap api',
    tone: 'info',
  },
  {
    id: 'log-3',
    time: '15:32:30',
    title: 'TRACKING KAMERA REAL-TIME',
    detail: 'Tracking visual aktif mengikuti fluktuasi lidah api (Bounding box ID: 1)',
    tone: 'info',
  },
  {
    id: 'log-4',
    time: '15:32:20',
    title: 'API TERDETEKSI (CONFIRMED)',
    detail: 'Deteksi api terkonfirmasi oleh model AI (Confidence 95.4%, Titik X: 142, Y: 98)',
    tone: 'danger',
  },
  {
    id: 'log-5',
    time: '15:32:12',
    title: 'SENSOR IR MENDETEKSI PANAS',
    detail: 'Diferensial sensor IR mendeteksi anomali suhu tinggi di sektor tengah',
    tone: 'danger',
  },
  {
    id: 'log-6',
    time: '15:31:50',
    title: 'SISTEM STANDBY MONITORING',
    detail: 'Kamera visual dan array sensor IR aktif melakukan pemindaian area',
    tone: 'info',
  },
];


