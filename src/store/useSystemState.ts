import { create } from 'zustand';

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

export const useSystemState = create<SystemStore>()((set, get) => ({
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
  },

  deactivateManual: () => {
    const { state } = get();
    if (state !== 'MANUAL_MODE') return;

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
    setTimeout(() => {
      set((system) => ({
        startupPhase: { ...system.startupPhase, audioPlayed: true },
      }));
    }, STARTUP_TIMELINE_MS.audio);

    setTimeout(() => {
      set((system) => ({
        startupPhase: { ...system.startupPhase, filterRemoved: true },
      }));
    }, STARTUP_TIMELINE_MS.filter);

    setTimeout(() => {
      set((system) => ({
        startupPhase: { ...system.startupPhase, cameraVisible: true },
      }));
    }, STARTUP_TIMELINE_MS.camera);

    setTimeout(() => {
      set((system) => ({
        startupPhase: { ...system.startupPhase, numbersRolled: true },
        ...LIVE_SENSOR_SNAPSHOT,
      }));
    }, STARTUP_TIMELINE_MS.sensors);

    setTimeout(() => {
      set((system) => ({
        startupPhase: { ...system.startupPhase, logsInitialized: true },
      }));
    }, STARTUP_TIMELINE_MS.logs);

    setTimeout(() => {
      set({ state: 'AUTO_MODE' });
    }, STARTUP_TIMELINE_MS.autoMode);
  },
}));
