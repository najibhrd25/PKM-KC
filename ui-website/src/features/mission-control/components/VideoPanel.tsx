import type { CameraSource } from '@/services/camera/cameraSource';
import { getCameraStreamUrl } from '@/services/safe-api/safeApi';
import { Panel } from '@/shared/components/Panel';
import { StatusPill } from '@/shared/components/StatusPill';

interface VideoPanelProps {
  isOff: boolean;
  cameraVisible: boolean;
  source: CameraSource;
}

export function VideoPanel({ isOff, cameraVisible, source }: VideoPanelProps) {
  // Tentukan URL stream berdasarkan jenis sumber kamera
  const isLiveStream = source.kind === 'raspberry-pi-stream' || (cameraVisible && !isOff);
  const streamUrl = source.streamUrl ?? getCameraStreamUrl();

  return (
    <Panel
      className={`relative aspect-square overflow-hidden ${
        isOff ? 'opacity-[0.45]' : ''
      }`}
    >
      <div
        className={`absolute inset-0 bg-[#050505] ${
          cameraVisible && !isOff ? 'opacity-[0.72]' : 'opacity-20'
        }`}
      >
        {/* Live MJPEG stream dari Raspberry Pi */}
        {isLiveStream && (
          <img
            src={streamUrl}
            alt="Live camera stream"
            className="absolute inset-0 h-full w-full object-cover"
          />
        )}

        {/* Overlay efek warna */}
        <div className="absolute inset-0 bg-danger/[0.035]" />
      </div>

      <div className="absolute left-4 top-4">
        <StatusPill label={isOff ? 'OFFLINE' : 'LIVE'} tone={isOff ? 'idle' : 'danger'} />
      </div>

      <div className="absolute inset-x-0 bottom-0 flex flex-row items-center justify-between bg-surface/90 px-4 py-3">
        <span className="font-mono text-[10px] tracking-wider text-muted">
          {source.label}
        </span>
        <span className="font-mono text-[10px] font-extrabold tracking-wider text-foreground">
          {source.kind.toUpperCase()}
        </span>
      </div>
    </Panel>
  );
}
