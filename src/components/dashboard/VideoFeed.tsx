'use client';

import { useSystemState } from '@/store/useSystemState';

export default function VideoFeed() {
  const { state, startupPhase } = useSystemState();
  const isOff = state === 'OFF_STATE';
  const cameraVisible = startupPhase.cameraVisible;

  return (
    <div className="relative w-full h-full bg-surface-container-lowest overflow-hidden rounded-lg">
      {/* Camera image */}
      <div
        className={`w-full h-full transition-all duration-700 ${
          isOff
            ? 'opacity-20 grayscale'
            : cameraVisible
            ? 'opacity-60 grayscale-0 hover:grayscale-0 hover:opacity-80'
            : 'opacity-0'
        }`}
        style={{
          backgroundImage: 'url(/camera-placeholder.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundColor: '#0a0a0a',
        }}
      />

      {/* HUD Scanline Overlay */}
      <div className="absolute inset-0 hud-scanline" />

      {/* Targeting Reticle */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-32 h-32 lg:w-48 lg:h-48 custom-reticle flex items-center justify-center">
          <div className="w-1 h-8 bg-primary-container absolute top-0" />
          <div className="w-1 h-8 bg-primary-container absolute bottom-0" />
          <div className="w-8 h-1 bg-primary-container absolute left-0" />
          <div className="w-8 h-1 bg-primary-container absolute right-0" />
        </div>
      </div>



      {/* LIVE Indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${
            isOff ? 'bg-muted' : 'bg-primary-container animate-pulse shadow-[0_0_8px_#DC2626]'
          }`}
        />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] font-bold tracking-[0.2em] text-on-surface">
          {isOff ? 'OFFLINE' : 'LIVE'}
        </span>
      </div>



      {/* Video bar under the feed (desktop) */}
      <div className="hidden lg:flex absolute bottom-0 left-0 right-0 justify-between items-center bg-surface-container-low/90 px-6 py-3">
        <div className="flex gap-4">
          <span className="flex items-center gap-2 font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-secondary">
            <span className={`w-1.5 h-1.5 rounded-full ${isOff ? 'bg-muted' : 'bg-green-500'}`} />
            {isOff ? 'STANDBY' : 'LIVE'}
          </span>
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted tracking-widest">
            SERVER_CLUSTER_A4
          </span>
        </div>
        <div className="flex gap-2">
          <button className="p-1 hover:bg-surface-container-high text-secondary">
            <span className="material-symbols-outlined text-sm">zoom_in</span>
          </button>
          <button className="p-1 hover:bg-surface-container-high text-secondary">
            <span className="material-symbols-outlined text-sm">videocam</span>
          </button>
        </div>
      </div>
    </div>
  );
}
