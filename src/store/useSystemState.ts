'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type SystemState = 'OFF_STATE' | 'STARTUP_SEQUENCE' | 'AUTO_MODE' | 'MANUAL_MODE';

export interface StartupPhase {
  audioPlayed: boolean;
  filterRemoved: boolean;
  cameraVisible: boolean;
  numbersRolled: boolean;
  logsInitialized: boolean;
}

interface SystemStore {
  // Core state
  state: SystemState;
  isManual: boolean;
  
  // Startup sequence tracking
  startupPhase: StartupPhase;
  
  // Sensor data (dummy for now)
  temperature: number;
  frequency: number;
  
  // Actions
  powerOn: () => void;
  powerOff: () => void;
  activateManual: () => void;
  deactivateManual: () => void;
  
  // Auth
  authPassword: (password: string) => boolean;
  
  // Internal
  _runStartupSequence: () => void;
}

const CORRECT_PASSWORD = 'ITS2024';

const initialStartupPhase: StartupPhase = {
  audioPlayed: false,
  filterRemoved: false,
  cameraVisible: false,
  numbersRolled: false,
  logsInitialized: false,
};

export const useSystemState = create<SystemStore>()(
  persist(
    (set, get) => ({
      // Initial state: system OFF
      state: 'OFF_STATE',
  isManual: false,
  startupPhase: { ...initialStartupPhase },
  temperature: 0,
  frequency: 0,

  powerOn: () => {
    const { state } = get();
    if (state !== 'OFF_STATE') return;
    
    set({ state: 'STARTUP_SEQUENCE' });
    get()._runStartupSequence();
  },

  powerOff: () => {
    set({
      state: 'OFF_STATE',
      isManual: false,
      startupPhase: { ...initialStartupPhase },
      temperature: 0,
      frequency: 0,
    });
  },

  activateManual: () => {
    const { state } = get();
    if (state !== 'AUTO_MODE') return;
    
    set({
      state: 'MANUAL_MODE',
      isManual: true,
    });
    
    // In production: POST /api/mode { auto: false } to RPi
    // For now just console log
    console.log('[S.A.F.E.] MANUAL_MODE activated — RPi auto-suppression OFF');
    console.log('[S.A.F.E.] Active modules: YOLO Vision ✓, Camera Feed ✓');
    console.log('[S.A.F.E.] Disabled modules: Auto-suppression ✗, Auto-servo ✗');
  },

  deactivateManual: () => {
    const { state } = get();
    if (state !== 'MANUAL_MODE') return;
    
    set({
      state: 'AUTO_MODE',
      isManual: false,
    });
    
    console.log('[S.A.F.E.] AUTO_MODE re-activated — full auto-suppression ON');
  },

  authPassword: (password: string) => {
    if (password === CORRECT_PASSWORD) {
      get().activateManual();
      return true;
    }
    return false;
  },

  _runStartupSequence: () => {
    // T+0ms: Play startup audio
    setTimeout(() => {
      set((s) => ({
        startupPhase: { ...s.startupPhase, audioPlayed: true },
      }));
      // Audio would play here in browser
      try {
        const audio = new Audio('/startup.mp3');
        audio.volume = 0.3;
        audio.play().catch(() => {
          // Audio autoplay blocked — that's fine
        });
      } catch {
        // No audio available
      }
    }, 0);

    // T+500ms: Remove grayscale/blur filter
    setTimeout(() => {
      set((s) => ({
        startupPhase: { ...s.startupPhase, filterRemoved: true },
      }));
    }, 500);

    // T+1000ms: Camera fade-in
    setTimeout(() => {
      set((s) => ({
        startupPhase: { ...s.startupPhase, cameraVisible: true },
      }));
    }, 1000);

    // T+1500ms: Rolling numbers animation
    setTimeout(() => {
      set((s) => ({
        startupPhase: { ...s.startupPhase, numbersRolled: true },
        temperature: 32,
        frequency: 45,
      }));
    }, 1500);

    // T+1800ms: Logs initialized
    setTimeout(() => {
      set((s) => ({
        startupPhase: { ...s.startupPhase, logsInitialized: true },
      }));
    }, 1800);

    // T+2000ms: Transition to AUTO_MODE
    setTimeout(() => {
      set({ state: 'AUTO_MODE' });
    }, 2000);
  },
}),
  {
    name: 'safe-system-storage',
  }
));
