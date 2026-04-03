'use client';

export default function BottomNav() {
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center h-16 bg-surface-container-lowest shadow-[0_-4px_40px_rgba(220,38,38,0.04)]">
      <button className="flex flex-col items-center justify-center text-safe-red">
        <span className="material-symbols-outlined">videocam</span>
        <span className="font-[family-name:var(--font-inter)] text-[10px] tracking-widest uppercase">LIVE</span>
      </button>
      <button className="flex flex-col items-center justify-center text-muted">
        <span className="material-symbols-outlined">query_stats</span>
        <span className="font-[family-name:var(--font-inter)] text-[10px] tracking-widest uppercase">DATA</span>
      </button>
      <button className="flex flex-col items-center justify-center text-muted">
        <span className="material-symbols-outlined">videogame_asset</span>
        <span className="font-[family-name:var(--font-inter)] text-[10px] tracking-widest uppercase">CONTROL</span>
      </button>
      <button className="flex flex-col items-center justify-center text-muted">
        <span className="material-symbols-outlined">list_alt</span>
        <span className="font-[family-name:var(--font-inter)] text-[10px] tracking-widest uppercase">LOGS</span>
      </button>
    </nav>
  );
}
