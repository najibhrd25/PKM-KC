import { ReactNode } from 'react';
import { Panel } from '@/shared/components/Panel';

export function SensorCard({ children }: { children: ReactNode }) {
  return (
    <Panel className="flex flex-1 flex-col p-4 py-5 justify-between">
      <div className="flex flex-col gap-3 flex-1 justify-center">{children}</div>
    </Panel>
  );
}

interface ControlInputProps {
  label: string;
  value: number;
  unit: string;
  onChange: (val: number) => void;
  disabled?: boolean;
}

export function ControlInput({ label, value, unit, onChange, disabled }: ControlInputProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded border p-2.5 transition-colors ${
        disabled
          ? 'border-border/30 opacity-50'
          : 'border-border focus-within:border-danger-soft focus-within:bg-danger/5'
      }`}
    >
      <span className="font-mono text-[9px] text-muted mb-1.5 uppercase tracking-wider">{label}</span>
      <div className="flex flex-row items-center justify-center gap-1 w-full">
        <input
          type="text"
          inputMode="decimal"
          autoComplete="off"
          value={value}
          onChange={(e) => {
            const val = e.target.value;
            if (val === '' || !isNaN(Number(val))) {
              onChange(Number(val));
            }
          }}
          disabled={disabled}
          className="w-16 bg-transparent text-center font-mono text-[12px] font-bold text-foreground outline-none"
        />
        <span className="font-mono text-[9px] text-muted">{unit}</span>
      </div>
    </div>
  );
}

interface ControlSelectProps {
  label: string;
  value: string;
  options: string[];
  onChange: (val: string) => void;
  disabled?: boolean;
}

export function ControlSelect({ label, value, options, onChange, disabled }: ControlSelectProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded border p-2.5 transition-colors ${
        disabled
          ? 'border-border/30 opacity-50'
          : 'border-danger-soft bg-danger/10 text-danger-soft'
      }`}
    >
      <span className="font-mono text-[9px] opacity-70 mb-1.5 uppercase tracking-wider">{label}</span>
      <div className="relative w-full flex justify-center items-center">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="cursor-pointer appearance-none bg-transparent text-center font-mono text-[12px] font-bold outline-none pr-4 w-full"
          style={{
            backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%22//www.w3.org/2000/svg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23ff4444%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22/%3E%3C/svg%3E")`,
            backgroundRepeat: 'no-repeat',
            backgroundPosition: 'right 20% center',
            backgroundSize: '8px auto',
          }}
        >
          {options.map((opt) => (
            <option key={opt} value={opt} className="bg-surface text-foreground text-center">
              {opt.toUpperCase()}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
