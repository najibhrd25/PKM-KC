import { useMemo, useState } from 'react';
import { GestureResponderEvent, PanResponder } from 'react-native';

import type { JoystickPosition } from '@/features/mission-control/types';

const MAX_RADIUS = 38;

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

  const responder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => enabled,
        onMoveShouldSetPanResponder: () => enabled,
        onPanResponderMove: (_event: GestureResponderEvent, gesture) => {
          if (!enabled) return;
          setPosition(clampToCircle(gesture.dx, gesture.dy));
        },
        onPanResponderRelease: () => {
          setPosition({ x: 0, y: 0 });
        },
        onPanResponderTerminate: () => {
          setPosition({ x: 0, y: 0 });
        },
      }),
    [enabled],
  );

  return {
    position,
    panHandlers: responder.panHandlers,
  };
}

