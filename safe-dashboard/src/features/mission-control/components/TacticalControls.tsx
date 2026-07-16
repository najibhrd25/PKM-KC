import { useState } from 'react';

import { AuthModal } from '@/features/mission-control/components/AuthModal';
import { useJoystick } from '@/features/mission-control/hooks/useJoystick';
import { AppButton } from '@/shared/components/AppButton';
import { Panel } from '@/shared/components/Panel';

interface TacticalControlsProps {
  isOff: boolean;
  isStarting: boolean;
  isManual: boolean;
  frequency: number;
  onAuthorize: (password: string) => boolean;
  onShoot: () => void;
}

export function TacticalControls({
  isOff,
  isStarting,
  isManual,
  frequency,
  onAuthorize,
  onShoot,
}: TacticalControlsProps) {
  const [authVisible, setAuthVisible] = useState(false);
  const enabled = !isOff && !isStarting && isManual;
  const { position, pointerHandlers } = useJoystick(enabled);

  function requestUnlock() {
    if (isOff || isStarting) return;
    setAuthVisible(true);
  }

  return (
    <Panel
      className={`flex min-w-0 flex-1 flex-col items-center justify-center gap-3 p-3 ${
        isOff ? 'opacity-[0.45]' : ''
      }`}
    >
      <div className="mb-2 flex w-full items-center justify-center">
        <span
          className={`text-center font-mono text-[9px] font-extrabold tracking-[1.4px] ${
            isManual ? 'text-success' : 'text-muted'
          }`}
        >
          {isManual ? 'MANUAL ACTIVE' : 'AUTO MODE'}
        </span>
      </div>

      {/* Joystick */}
      <div
        className={`relative flex h-[116px] w-[116px] items-center justify-center overflow-hidden rounded-full border bg-surface ${
          isManual ? 'border-danger-soft' : 'border-border'
        }`}
      >
        <div className="absolute h-[84px] w-[84px] rounded-full border border-dashed border-foreground/20" />
        <div
          {...pointerHandlers}
          className={`flex h-[54px] w-[54px] cursor-grab items-center justify-center rounded-full border select-none active:cursor-grabbing ${
            isManual
              ? 'border-danger-soft bg-danger'
              : 'border-border bg-surface-high'
          }`}
          style={{
            transform: `translate(${position.x}px, ${position.y}px)`,
            touchAction: 'none',
          }}
        >
          <div
            className={`h-2.5 w-2.5 rounded-full ${
              isManual ? 'bg-white' : 'bg-muted'
            }`}
          />
        </div>
      </div>

      {/* Recovery Mode Info */}
      <div className="w-full bg-surface p-3">
        <div className="flex flex-row items-center justify-between">
          <div>
            <span className="font-mono text-[8px] tracking-[1.2px] text-muted">
              RECOVERY MODE
            </span>
            <p
              className={`mt-[3px] font-mono text-[10px] font-black tracking-[1.2px] ${
                isManual ? 'text-danger-soft' : 'text-muted'
              }`}
            >
              {isOff ? 'OFFLINE' : isManual ? 'READY' : 'LOCKED'}
            </p>
          </div>
          <span className="font-mono text-[9px] tracking-wider text-muted">
            {isOff ? '-- Hz' : `${frequency} Hz`}
          </span>
        </div>
        <AppButton
          className="mt-3 w-full min-h-[42px]"
          disabled={isOff || isStarting}
          label={
            isOff
              ? 'OFFLINE'
              : isStarting
                ? 'INITIALIZING'
                : isManual
                  ? 'SHOOT'
                  : 'UNLOCK'
          }
          variant={isManual ? 'primary' : 'secondary'}
          onPress={isManual ? onShoot : requestUnlock}
        />
      </div>

      <AuthModal
        visible={authVisible}
        onClose={() => setAuthVisible(false)}
        onSubmit={onAuthorize}
      />
    </Panel>
  );
}
