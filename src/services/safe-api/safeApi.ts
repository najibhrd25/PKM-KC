import type { JoystickPosition } from '@/features/mission-control/types';

export interface SetModePayload {
  auto: boolean;
}

export interface TriggerPayload {
  action: 'shoot';
  frequency: number;
}

export async function setSafeMode(_payload: SetModePayload) {
  // TODO: POST to Raspberry Pi when the device endpoint is available.
}

export async function sendServoPosition(_position: JoystickPosition) {
  // TODO: POST joystick coordinates to Raspberry Pi.
}

export async function triggerAcousticPulse(_payload: TriggerPayload) {
  // TODO: POST shoot command to Raspberry Pi.
}

