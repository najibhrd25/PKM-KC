import { getCameraStreamUrl } from '@/lib/safeApi';
import type { CameraSource } from '@/lib/cameraSource';
import { Card } from '@/components/ui/Card';
import { useState } from 'react';
// import { useEffect, useRef } from 'react'; // [AKTIFKAN JIKA PAKAI VIDEO]

interface VideoPanelProps {
  isOff: boolean;
  cameraVisible: boolean;
  source: CameraSource;
}

// [KODE OPSI VIDEO] - Aktifkan jika ingin memakai video looping:
// const START_TIME = 0.9888; // Detik mulai video (misal 55 detik atau awal)

export function VideoPanel({ isOff }: VideoPanelProps) {
  const [streamError, setStreamError] = useState(false);
  const streamUrl = getCameraStreamUrl();

  return (
    <Card
      className={`relative w-full aspect-[16/10.5] max-h-[235px] overflow-hidden bg-black ${
        isOff ? 'opacity-[0.45]' : ''
      }`}
    >
      <div className="absolute inset-0 overflow-hidden flex items-center justify-center bg-black">
        {/* Stream langsung dari Raspberry Pi */}
        {!streamError ? (
          <img
            src={streamUrl}
            alt="Live Camera Feed Raspberry Pi"
            onError={() => setStreamError(true)}
            onLoad={() => setStreamError(false)}
            className="h-full w-full object-cover object-center"
          />
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 p-4 text-center">
            <div className="h-2.5 w-2.5 rounded-full bg-red-500/80 animate-pulse" />
            <span className="font-mono text-[11px] font-bold tracking-wider text-muted uppercase">
              Kamera Raspberry Pi Offline
            </span>
            <span className="font-mono text-[9px] text-muted/60">
              {streamUrl}
            </span>
            <button
              type="button"
              onClick={() => setStreamError(false)}
              className="mt-1 px-3 py-1 text-[10px] font-mono font-bold rounded border border-border bg-surface-high hover:border-danger-soft transition-colors cursor-pointer text-foreground"
            >
              Coba Hubungkan Ulang
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}


