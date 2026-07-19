import { create } from 'zustand';
import type { ActivityLogItem } from '@/data/types';

import {
  LIVE_SENSOR_SNAPSHOT,
  MANUAL_MODE_PASSWORD,
  STARTUP_TIMELINE_MS,
  initialStartupPhase,
} from '@/data/constants';
import type { StartupPhase, SystemState } from '@/data/types';
import { setSafeMode, sendHeartbeat, getEventsUrl } from '@/lib/safeApi';

export type { StartupPhase, SystemState };

let startupTimers: ReturnType<typeof setTimeout>[] = [];
let heartbeatInterval: ReturnType<typeof setInterval> | null = null;
let inactivityTimer: ReturnType<typeof setTimeout> | null = null;
let eventSource: EventSource | null = null;

const HEARTBEAT_INTERVAL_MS = 2000;
const INACTIVITY_TIMEOUT_MS = 10000;

function clearTimers() {
  startupTimers.forEach(clearTimeout);
  startupTimers = [];
  if (heartbeatInterval) clearInterval(heartbeatInterval);
  if (inactivityTimer) clearTimeout(inactivityTimer);
  heartbeatInterval = null;
  inactivityTimer = null;
}

interface SystemStore {
  state: SystemState;
  isManual: boolean;
  startupPhase: StartupPhase;
  temperature: number;
  waveform: string;
  frequency: number;
  amplitude: number;
  duration: number;
  activityLogs: ActivityLogItem[];
  setWaveform: (w: string) => void;
  setFrequency: (f: number) => void;
  setAmplitude: (a: number) => void;
  setDuration: (d: number) => void;
  appendLog: (log: ActivityLogItem) => void;
  pingActivity: () => void;
  powerOn: () => void;
  powerOff: () => void;
  activateManual: () => void;
  deactivateManual: () => void;
  authPassword: (password: string) => boolean;
  _runStartupSequence: () => void;
  _initSSE: () => void;
  _closeSSE: () => void;
}

let lastHeartbeatTime = 0;

export const useSystemState = create<SystemStore>()((set, get) => ({
  state: 'AUTO_MODE',
  isManual: false,
  startupPhase: { ...initialStartupPhase, logsInitialized: true, cameraVisible: true, numbersRolled: true, filterRemoved: true, audioPlayed: true },
  temperature: 0,
  waveform: 'sine',
  frequency: 45,
  amplitude: 0.855,
  duration: 30,
  activityLogs: [],

  setWaveform: (w) => { set({ waveform: w }); get().pingActivity(); },
  setFrequency: (f) => { set({ frequency: f }); get().pingActivity(); },
  setAmplitude: (a) => { set({ amplitude: a }); get().pingActivity(); },
  setDuration: (d) => { set({ duration: d }); get().pingActivity(); },
  appendLog: (log) => set((state) => ({ activityLogs: [log, ...state.activityLogs].slice(0, 50) })),

  pingActivity: () => {
    const { isManual, deactivateManual } = get();
    if (!isManual) return;
    
    const now = Date.now();
    if (now - lastHeartbeatTime > HEARTBEAT_INTERVAL_MS) {
      sendHeartbeat().catch(() => {});
      lastHeartbeatTime = now;
    }

    if (inactivityTimer) clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(() => {
      deactivateManual();
    }, INACTIVITY_TIMEOUT_MS);
  },

  powerOn: () => {
    const { state, _initSSE } = get();
    if (state !== 'OFF_STATE') return;

    set({ state: 'STARTUP_SEQUENCE', activityLogs: [] });
    _initSSE();
    get()._runStartupSequence();
  },

  powerOff: () => {
    clearTimers();
    get()._closeSSE();

    setSafeMode({ auto: true }).catch(() => {});

    set({
      state: 'OFF_STATE',
      isManual: false,
      startupPhase: { ...initialStartupPhase },
      temperature: 0,
      waveform: 'sine',
      frequency: 45,
      amplitude: 0.855,
      duration: 30,
      activityLogs: [],
    });
  },

  activateManual: () => {
    const { state } = get();
    if (state !== 'AUTO_MODE') return;

    // Kirim perintah ke Pi untuk masuk mode manual
    setSafeMode({ auto: false }).catch((err) => {
      console.warn('[System] Gagal mengirim mode manual ke Pi:', err);
      // Tetap lanjut ke manual di sisi UI meski request gagal
      // (saat development tanpa Pi terhubung)
    });

    set({
      state: 'MANUAL_MODE',
      isManual: true,
    });

    // Start inactivity timer and send first heartbeat
    get().pingActivity();
  },

  deactivateManual: () => {
    const { state } = get();
    if (state !== 'MANUAL_MODE') return;

    if (heartbeatInterval) clearInterval(heartbeatInterval);
    if (inactivityTimer) clearTimeout(inactivityTimer);
    heartbeatInterval = null;
    inactivityTimer = null;

    // Kirim perintah ke Pi untuk kembali ke auto
    setSafeMode({ auto: true }).catch((err) => {
      console.warn('[System] Gagal mengirim mode auto ke Pi:', err);
    });

    set({
      state: 'AUTO_MODE',
      isManual: false,
    });
  },

  authPassword: (password: string) => {
    if (password === MANUAL_MODE_PASSWORD) {
      get().activateManual();
      return true;
    }
    return false;
  },

  _runStartupSequence: () => {
    clearTimers();

    const schedule = (callback: () => void, delay: number) => {
      startupTimers.push(
        setTimeout(() => {
          if (get().state === 'STARTUP_SEQUENCE') callback();
        }, delay),
      );
    };

    schedule(
      () =>
        set((system) => ({
          startupPhase: { ...system.startupPhase, audioPlayed: true },
        })),
      STARTUP_TIMELINE_MS.audio,
    );
    schedule(
      () =>
        set((system) => ({
          startupPhase: { ...system.startupPhase, filterRemoved: true },
        })),
      STARTUP_TIMELINE_MS.filter,
    );
    schedule(
      () =>
        set((system) => ({
          startupPhase: { ...system.startupPhase, cameraVisible: true },
        })),
      STARTUP_TIMELINE_MS.camera,
    );
    schedule(
      () =>
        set((system) => ({
          startupPhase: { ...system.startupPhase, numbersRolled: true },
          ...LIVE_SENSOR_SNAPSHOT,
        })),
      STARTUP_TIMELINE_MS.sensors,
    );
    schedule(
      () =>
        set((system) => ({
          startupPhase: { ...system.startupPhase, logsInitialized: true },
        })),
      STARTUP_TIMELINE_MS.logs,
    );
    schedule(() => {
      set({ state: 'AUTO_MODE' });
      startupTimers = [];
    }, STARTUP_TIMELINE_MS.autoMode);
  },

  _initSSE: () => {
    get()._closeSSE();
    eventSource = new EventSource(getEventsUrl());
    eventSource.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
        
        let logItem: ActivityLogItem | null = null;

        if (d.type === 'state') {
          // If we want to strictly sync state with Pi:
          // We can handle state changes here if needed, but currently we rely on local transitions for some parts
          logItem = {
            id: Date.now().toString() + Math.random(),
            time: timeStr,
            title: 'STATE CHANGED',
            detail: `System entered ${d.value.toUpperCase()} state`,
            tone: d.value === 'extinguishing' ? 'danger' : 'info'
          };
        } else if (d.type === 'mode') {
          set({ isManual: d.value === 'manual' });
          logItem = {
            id: Date.now().toString() + Math.random(),
            time: timeStr,
            title: 'MODE CHANGED',
            detail: `Switched to ${d.value.toUpperCase()} mode`,
            tone: 'info'
          };
        } else if (d.type === 'detection') {
          logItem = {
            id: Date.now().toString() + Math.random(),
            time: timeStr,
            title: 'FIRE DETECTED',
            detail: `Accuracy ${(d.confidence * 100).toFixed(1)}%`,
            tone: 'danger'
          };
        }

        if (logItem) {
          get().appendLog(logItem);
        }

      } catch (err) {
        console.warn('Error parsing SSE data', err);
      }
    };
  },

  _closeSSE: () => {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }
}));
