import { SensorCard, ControlInput, ControlSelect } from './SensorControls';

interface SensorPanelProps {
  isOff: boolean;
  isManual: boolean;
  waveform: string;
  frequency: number;
  amplitude: number;
  duration: number;
  setWaveform: (w: string) => void;
  setFrequency: (f: number) => void;
  setAmplitude: (a: number) => void;
  setDuration: (d: number) => void;
}

export function SensorPanel({
  isOff,
  isManual,
  waveform,
  frequency,
  amplitude,
  duration,
  setWaveform,
  setFrequency,
  setAmplitude,
  setDuration,
}: SensorPanelProps) {
  const disabled = isOff || !isManual;

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-3">
      <SensorCard>
        <ControlSelect
          label="waveform"
          value={waveform}
          options={['sine', 'square', 'sawtooth', 'triangle', 'sweep', 'pulse']}
          onChange={setWaveform}
          disabled={disabled}
        />
        <ControlInput
          label="freq"
          value={frequency}
          unit="Hz"
          onChange={setFrequency}
          disabled={disabled}
        />
      </SensorCard>

      <SensorCard>
        <ControlInput
          label="amplitude"
          value={amplitude * 100}
          unit="%"
          onChange={(val) => setAmplitude(val / 100)}
          disabled={disabled}
        />
        <ControlInput
          label="duration"
          value={duration}
          unit="s"
          onChange={setDuration}
          disabled={disabled}
        />
      </SensorCard>
    </div>
  );
}
