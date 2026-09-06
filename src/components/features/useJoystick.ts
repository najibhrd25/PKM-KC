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
  const lastSentRef = useRef<number>(0);
  const draggingRef = useRef(false);
  const startRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Kirim posisi joystick ke Raspberry Pi saat bergerak (throttled)
  useEffect(() => {
    if (!enabled) return;
    if (position.x === 0 && position.y === 0) return;

    const now = Date.now();
    if (now - lastSentRef.current < JOG_THROTTLE_MS) return;

    lastSentRef.current = now;
    sendServoPosition(position).catch(() => {});
  }, [enabled, position]);

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!enabled) return;
      // Reset 10s inactivity countdown
      useSystemState.getState().pingActivity();
      draggingRef.current = true;
      startRef.current = { x: e.clientX, y: e.clientY };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [enabled],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!enabled || !draggingRef.current) return;
      // Reset 10s inactivity countdown while actively dragging
      useSystemState.getState().pingActivity();
      const dx = e.clientX - startRef.current.x;
      const dy = e.clientY - startRef.current.y;
      setPosition(clampToCircle(dx, dy));
    },
    [enabled],
  );

  const handlePointerUp = useCallback(() => {
    if (draggingRef.current) {
      useSystemState.getState().pingActivity();
    }
    draggingRef.current = false;
    setPosition({ x: 0, y: 0 });
  }, []);

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
