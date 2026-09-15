import { useCallback, useEffect, useRef, useState } from 'react';
import type { JoystickPosition } from '@/data/types';
import { sendServoPosition } from '@/lib/safeApi';
import { useSystemState } from '@/store/useSystemState';

const MAX_RADIUS = 38;
const JOG_THROTTLE_MS = 100;

function clampToCircle(x: number, y: number): JoystickPosition {
  const distance = Math.sqrt(x * x + y * y);
  if (distance <= MAX_RADIUS) {
    return { x, y };
  }

  return {
    x: (x / distance) * MAX_RADIUS,
    y: (y / distance) * MAX_RADIUS,
  };
}

export function useJoystick(enabled: boolean) {
  const [position, setPosition] = useState<JoystickPosition>({ x: 0, y: 0 });
  const posRef = useRef<JoystickPosition>({ x: 0, y: 0 });
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const draggingRef = useRef(false);
  const startRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  const startJogLoop = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      if (!enabled || !draggingRef.current) return;
      const { x, y } = posRef.current;
      const joyNX = x / MAX_RADIUS;
      const joyNY = y / MAX_RADIUS;
      if (Math.abs(joyNX) < 0.05 && Math.abs(joyNY) < 0.05) return;
      sendServoPosition({ x, y }).catch(() => {});
    }, JOG_THROTTLE_MS);
  }, [enabled]);

  const stopJogLoop = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!enabled) return;
      useSystemState.getState().pingActivity();
      draggingRef.current = true;
      startRef.current = { x: e.clientX, y: e.clientY };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      startJogLoop();
    },
    [enabled, startJogLoop],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!enabled || !draggingRef.current) return;
      useSystemState.getState().pingActivity();
      const dx = e.clientX - startRef.current.x;
      const dy = e.clientY - startRef.current.y;
      const clamped = clampToCircle(dx, dy);
      posRef.current = clamped;
      setPosition(clamped);
    },
    [enabled],
  );

  const handlePointerUp = useCallback(() => {
    if (draggingRef.current) {
      useSystemState.getState().pingActivity();
    }
    draggingRef.current = false;
    posRef.current = { x: 0, y: 0 };
    setPosition({ x: 0, y: 0 });
    stopJogLoop();
  }, [stopJogLoop]);

  return {
    position,
    pointerHandlers: {
      onPointerDown: handlePointerDown,
      onPointerMove: handlePointerMove,
      onPointerUp: handlePointerUp,
      onPointerCancel: handlePointerUp,
    },
  };
}
