import { VideoPanel } from '@/components/features/VideoPanel';
import { SensorPanel } from '@/components/features/SensorPanel';
import { JoystickControls } from '@/components/features/JoystickControls';
import { ActivityLog } from '@/components/features/ActivityLog';
import type { CameraSource } from '@/lib/cameraSource';
import type { ActivityLogItem } from '@/data/types';
import { useSystemState } from '@/store/useSystemState';

interface ManualModeSectionProps {
  streamSource: CameraSource;
  waveform: string;
  frequency: number;
  amplitude: number;
  duration: number;
  setWaveform: (w: string) => void;
  setFrequency: (f: number) => void;
  setAmplitude: (a: number) => void;
  setDuration: (d: number) => void;
  onShoot: () => void;
  activityLogs: ActivityLogItem[];
  logsReady: boolean;
  isExporting: boolean;
  onExport: () => void;
}

export function ManualModeSection({
  streamSource,
  waveform,
  frequency,
  amplitude,
  duration,
  setWaveform,
  setFrequency,
  setAmplitude,
  setDuration,
  onShoot,
  activityLogs,
  logsReady,
  isExporting,
  onExport,
}: ManualModeSectionProps) {
  return (
    <div
      className="flex flex-col gap-2.5"
      onPointerDownCapture={() => useSystemState.getState().pingActivity()}
    >
      {/* Camera Panel */}
      <VideoPanel isOff={false} cameraVisible={true} source={streamSource} />

      <div className="flex flex-row gap-2.5 min-h-[286px] w-full">
        {/* Interactive Sensor Panel */}
        <SensorPanel
          waveform={waveform}
          frequency={frequency}
          amplitude={amplitude}
          duration={duration}
          isOff={false}
          isManual={true}
          setWaveform={setWaveform}
          setFrequency={setFrequency}
          setAmplitude={setAmplitude}
          setDuration={setDuration}
        />
        
        {/* Joystick Controls */}
        <JoystickControls
          isOff={false}
          isStarting={false}
          isManual={true}
          frequency={frequency}
          onAuthorize={() => true}
          onShoot={onShoot}
        />
      </div>

      {/* Activity Log */}
      <ActivityLog
        logs={activityLogs}
        isOff={false}
        logsReady={logsReady}
        isExporting={isExporting}
        onExport={onExport}
      />
    </div>
  );
}
