'use client';

import { useEffect } from 'react';

import type { StartupPhase } from '@/core/system/types';

export function useStartupAudio(startupPhase: StartupPhase) {
  useEffect(() => {
    if (!startupPhase.audioPlayed) return;

    const audio = new Audio('/startup.mp3');
    audio.volume = 0.3;
    audio.play().catch(() => {
      // Browser autoplay can block this until the user interacts.
    });
  }, [startupPhase.audioPlayed]);
}

