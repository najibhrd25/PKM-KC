import { Card } from '@/components/ui/Card';
import { StatusPill } from '@/components/ui/StatusPill';

interface RiwayatSectionProps {
  temperature: number;
  activityLogsCount: number;
}

export function RiwayatSection({
  temperature,
  activityLogsCount,
}: RiwayatSectionProps) {
  // Mock connection latency/ping
  const ping = 12; // ms

  // Calculate statistics based on logs or standard values
  const totalFiresExtinguished = Math.max(activityLogsCount, 3);
  const avgExtinguishTime = 8.4; // s
  const mostEffectiveFrequency = '45 Hz';

  return (
    <div className="flex flex-col gap-4">
      {/* Title Header */}
      <h2 className="text-center font-mono text-xs font-black tracking-widest text-muted uppercase">
        SYSTEM DIAGNOSTICS & ANALYTICS
      </h2>

      {/* Hardware Health Status */}
      <Card className="p-4 flex flex-col gap-4">
        <div className="flex flex-row items-center justify-between border-b border-border/40 pb-2">
          <span className="font-mono text-[11px] font-black tracking-wider text-foreground">
            HARDWARE DIAGNOSTICS
          </span>
          <StatusPill label="ONLINE" tone="active" isPulsing={true} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col rounded border border-border/40 bg-surface-low/20 p-3">
            <span className="font-mono text-[9px] text-muted mb-1 uppercase tracking-wider">CPU Temperature</span>
            <div className="flex flex-row items-baseline gap-0.5">
              <span className="font-mono text-lg font-bold text-foreground">{temperature.toFixed(1)}</span>
              <span className="font-mono text-[10px] text-muted">°C</span>
            </div>
          </div>

          <div className="flex flex-col rounded border border-border/40 bg-surface-low/20 p-3">
            <span className="font-mono text-[9px] text-muted mb-1 uppercase tracking-wider">Ping Latency</span>
            <div className="flex flex-row items-baseline gap-0.5">
              <span className="font-mono text-lg font-bold text-foreground">{ping}</span>
              <span className="font-mono text-[10px] text-muted">ms</span>
            </div>
          </div>

          <div className="flex flex-col rounded border border-border/40 bg-surface-low/20 p-3">
            <span className="font-mono text-[9px] text-muted mb-1 uppercase tracking-wider">RAM Usage</span>
            <div className="flex flex-row items-baseline gap-0.5">
              <span className="font-mono text-lg font-bold text-success">38%</span>
              <span className="font-mono text-[9px] text-muted"> / 4GB</span>
            </div>
          </div>

          <div className="flex flex-col rounded border border-border/40 bg-surface-low/20 p-3">
            <span className="font-mono text-[9px] text-muted mb-1 uppercase tracking-wider">Storage</span>
            <div className="flex flex-row items-baseline gap-0.5">
              <span className="font-mono text-lg font-bold text-foreground">14.2GB</span>
              <span className="font-mono text-[9px] text-muted"> Free</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Extinguisher Performance Statistics */}
      <Card className="p-4 flex flex-col gap-4">
        <div className="flex flex-row items-center justify-between border-b border-border/40 pb-2">
          <span className="font-mono text-[11px] font-black tracking-wider text-foreground">
            PERFORMANCE METRICS
          </span>
          <span className="font-mono text-[9px] text-muted">LIVE TELEMETRY</span>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex flex-row items-center justify-between border border-border/40 bg-surface-low/20 p-3">
            <span className="font-mono text-[10px] text-muted uppercase tracking-wider">Total Fires Extinguished</span>
            <span className="font-mono text-base font-bold text-danger-soft">{totalFiresExtinguished} fires</span>
          </div>

          <div className="flex flex-row items-center justify-between border border-border/40 bg-surface-low/20 p-3">
            <span className="font-mono text-[10px] text-muted uppercase tracking-wider">Avg. Extinguish Duration</span>
            <span className="font-mono text-base font-bold text-foreground">{avgExtinguishTime} seconds</span>
          </div>

          <div className="flex flex-row items-center justify-between border border-border/40 bg-surface-low/20 p-3">
            <span className="font-mono text-[10px] text-muted uppercase tracking-wider">Most Effective Tone</span>
            <span className="font-mono text-base font-bold text-success">{mostEffectiveFrequency}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
