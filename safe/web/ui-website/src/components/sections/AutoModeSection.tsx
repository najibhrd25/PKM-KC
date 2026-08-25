import { VideoPanel } from '@/components/features/VideoPanel';
import { SensorCard } from '@/components/features/SensorControls';
import { ActivityLog } from '@/components/features/ActivityLog';
import type { CameraSource } from '@/lib/cameraSource';
import type { ActivityLogItem } from '@/data/types';

interface AutoModeSectionProps {
  streamSource: CameraSource;
  waveform: string;
  frequency: number;
  amplitude: number;
  duration: number;
  activityLogs: ActivityLogItem[];
  logsReady: boolean;
  isExporting: boolean;
  onExport: () => void;
}

export function AutoModeSection({
  streamSource,
  waveform,
  frequency,
  amplitude,
  duration,
  activityLogs,
  logsReady,
  isExporting,
  onExport,
}: AutoModeSectionProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Title Header */}
      <h2 className="text-center font-mono text-xs font-black tracking-widest text-success uppercase">
        AUTOMATIC SYSTEMS MONITORING
      </h2>

      {/* Camera Panel */}
      <VideoPanel isOff={false} cameraVisible={true} source={streamSource} />

      {/* Read-Only Stats Cards */}
      <div className="flex flex-row gap-3">
        <SensorCard>
          <div className="flex flex-col items-center justify-center rounded border border-border/40 bg-surface-low/20 p-2.5">
            <span className="font-mono text-[9px] text-muted mb-1.5 uppercase tracking-wider">waveform</span>
            <span className="font-mono text-[12px] font-bold text-foreground uppercase">{waveform}</span>
          </div>
          <div className="flex flex-col items-center justify-center rounded border border-border/40 bg-surface-low/20 p-2.5">
            <span className="font-mono text-[9px] text-muted mb-1.5 uppercase tracking-wider">freq</span>
            <div className="flex flex-row items-center gap-1">
              <span className="font-mono text-[12px] font-bold text-foreground">{frequency}</span>
              <span className="font-mono text-[9px] text-muted">Hz</span>
            </div>
          </div>
        </SensorCard>

        <SensorCard>
          <div className="flex flex-col items-center justify-center rounded border border-border/40 bg-surface-low/20 p-2.5">
            <span className="font-mono text-[9px] text-muted mb-1.5 uppercase tracking-wider">amplitude</span>
            <div className="flex flex-row items-center gap-1">
              <span className="font-mono text-[12px] font-bold text-foreground">{Math.round(amplitude * 100)}</span>
              <span className="font-mono text-[9px] text-muted">%</span>
            </div>
          </div>
          <div className="flex flex-col items-center justify-center rounded border border-border/40 bg-surface-low/20 p-2.5">
            <span className="font-mono text-[9px] text-muted mb-1.5 uppercase tracking-wider">duration</span>
            <div className="flex flex-row items-center gap-1">
              <span className="font-mono text-[12px] font-bold text-foreground">{duration}</span>
              <span className="font-mono text-[9px] text-muted">s</span>
            </div>
          </div>
        </SensorCard>
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
