import { Download } from 'lucide-react';
import type { ActivityLogItem } from '@/features/mission-control/types';

import { AppButton } from '@/shared/components/AppButton';
import { Panel } from '@/shared/components/Panel';

interface ActivityLogProps {
  isOff: boolean;
  logsReady: boolean;
  isExporting: boolean;
  onExport: () => void;
  logs: ActivityLogItem[];
}

export function ActivityLog({
  isOff,
  logsReady,
  isExporting,
  onExport,
  logs,
}: ActivityLogProps) {
  const reportDisabled = isOff || !logsReady || isExporting;

  return (
    <Panel className="p-4">
      <div className="mb-4 flex flex-row items-center justify-between">
        <span className="text-lg font-black tracking-[0.5px] text-foreground">
          LOG KEJADIAN
        </span>
        <div className="flex flex-col items-end gap-2">
          <span className="font-mono text-[9px] tracking-wider text-muted">
            {isOff ? 'OFFLINE' : 'REAL-TIME SYNC'}
          </span>
          <button
            type="button"
            className={`border border-border px-3 py-2 transition-opacity active:opacity-70 ${
              reportDisabled ? 'pointer-events-none opacity-[0.35]' : 'cursor-pointer bg-surface'
            }`}
            disabled={reportDisabled}
            onClick={onExport}
          >
            <span className="font-mono text-[9px] font-black tracking-wider text-foreground">
              {isExporting ? 'CREATING...' : 'EXPORT PDF'}
            </span>
          </button>
        </div>
      </div>

      {isOff || !logsReady ? (
        <p className="py-6 text-center font-mono text-[11px] tracking-wider text-muted">
          {isOff ? 'SYSTEM OFFLINE' : 'INITIALIZING LOGS'}
        </p>
      ) : (
        logs.map((log) => (
          <div key={log.id} className="flex flex-row gap-3 py-2">
            <span className="w-[58px] font-mono text-[10px] text-muted">{log.time}</span>
            <div className="flex-1">
              <p
                className={`font-mono text-[11px] font-black tracking-wider ${
                  log.tone === 'danger'
                    ? 'text-danger-soft'
                    : log.tone === 'success'
                      ? 'text-success'
                      : 'text-foreground'
                }`}
              >
                {log.title}
              </p>
              <p className="mt-[3px] font-mono text-[10px] text-muted">
                {log.detail}
              </p>
            </div>
          </div>
        ))
      )}
    </Panel>
  );
}
