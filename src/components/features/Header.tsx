import { Home } from 'lucide-react';
import safeLogo from '@/assets/safe-logo.svg';
import { StatusPill } from '@/components/ui/StatusPill';

interface HeaderProps {
  state: string;
  isManual: boolean;
  onPowerPress: () => void;
  onHomePress: () => void;
}

export function Header({ state, isManual, onPowerPress, onHomePress }: HeaderProps) {
  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';

  // Logika blinking (kelip-kelip):
  // 1. AUTO MODE: selalu kelip-kelip.
  // 2. MANUAL MODE: mati secara default (di-handle oleh TacticalControls saat ada interaksi joystick untuk kelip). 
  // Disini kita set true jika AUTO MODE.
  const isPulsing = !isOff && !isStarting && !isManual;

  return (
    <div className="flex w-full flex-row items-center justify-between px-4 py-2.5">
      <div className="flex flex-row items-center gap-2.5">
        <img src={safeLogo} alt="S.A.F.E. Logo" className="h-[54px] w-[54px] object-contain" />
        <div>
          <p className="text-lg font-black tracking-[-0.5px] text-foreground leading-none mb-1">
            S.A.F.E.
          </p>
          <StatusPill
            label={isOff ? 'OFFLINE' : isStarting ? 'STARTING' : 'ONLINE'}
            tone={isOff ? 'idle' : 'active'}
            isPulsing={isPulsing}
          />
        </div>
      </div>

      <div className="flex flex-row items-center gap-2">
        <button
          type="button"
          aria-label="Home Servo"
          className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-full border transition-transform active:scale-[0.96] active:opacity-75 ${
            isOff
              ? 'border-border/30 opacity-40'
              : 'border-border bg-surface-high'
          }`}
          onClick={onHomePress}
          disabled={isOff || isStarting}
        >
          <Home className="h-4.5 w-4.5 text-muted" />
        </button>

        <button
          type="button"
          aria-label={isOff ? 'Power on system' : 'Power off system'}
          className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-full border transition-transform active:scale-[0.96] active:opacity-75 ${
            isOff
              ? 'border-danger opacity-70'
              : 'border-danger-soft bg-danger'
          }`}
          onClick={onPowerPress}
        >
          <span className="font-mono text-[11px] font-extrabold text-white">
            {isOff ? 'ON' : 'OFF'}
          </span>
        </button>
      </div>
    </div>
  );
}
