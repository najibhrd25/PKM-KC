'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  LIVE_SENSOR_SNAPSHOT,
  MANUAL_MODE_PASSWORD,
  STARTUP_TIMELINE_MS,
  initialStartupPhase,
} from '@/core/system/constants';
import type { StartupPhase, SystemState } from '@/core/system/types';

export type { StartupPhase, SystemState };

interface SystemStore {
  state: SystemState;
  isManual: boolean;
  startupPhase: StartupPhase;
  temperature: number;
  frequency: number;
  powerOn: () => void;
  powerOff: () => void;
  activateManual: () => void;
  deactivateManual: () => void;
  authPassword: (password: string) => boolean;
  _runStartupSequence: () => void;
}

export const useSystemState = create<SystemStore>()(
  persist(
    (set, get) => ({
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

        console.log('[S.A.F.E.] MANUAL_MODE activated - RPi auto-suppression OFF');
        console.log('[S.A.F.E.] Active modules: YOLO Vision, Camera Feed');
        console.log('[S.A.F.E.] Disabled modules: Auto-suppression, Auto-servo');
      },

      deactivateManual: () => {
        const { state } = get();
        if (state !== 'MANUAL_MODE') return;

        set({
          state: 'AUTO_MODE',
          isManual: false,
        });

        console.log('[S.A.F.E.] AUTO_MODE re-activated - full auto-suppression ON');
      },

      authPassword: (password: string) => {
        if (password === MANUAL_MODE_PASSWORD) {
          get().activateManual();
          return true;
        }
        return false;
      },

      _runStartupSequence: () => {
        setTimeout(() => {
          set((s) => ({
            startupPhase: { ...s.startupPhase, audioPlayed: true },
          }));
        }, STARTUP_TIMELINE_MS.audio);

        setTimeout(() => {
          set((s) => ({
            startupPhase: { ...s.startupPhase, filterRemoved: true },
          }));
        }, STARTUP_TIMELINE_MS.filter);

        setTimeout(() => {
          set((s) => ({
            startupPhase: { ...s.startupPhase, cameraVisible: true },
          }));
        }, STARTUP_TIMELINE_MS.camera);

        setTimeout(() => {
          set((s) => ({
            startupPhase: { ...s.startupPhase, numbersRolled: true },
            ...LIVE_SENSOR_SNAPSHOT,
          }));
        }, STARTUP_TIMELINE_MS.sensors);

        setTimeout(() => {
          set((s) => ({
            startupPhase: { ...s.startupPhase, logsInitialized: true },
          }));
        }, STARTUP_TIMELINE_MS.logs);

        setTimeout(() => {
          set({ state: 'AUTO_MODE' });
        }, STARTUP_TIMELINE_MS.autoMode);
      },
    }),
  {
    name: 'safe-system-storage',
  }
));
