'use client';

export default function SideNav() {
  return (
    <nav className="hidden lg:flex flex-col h-screen fixed left-0 top-0 bg-surface-container-lowest w-20 pt-24 items-center gap-8 z-40">
      <div className="flex flex-col items-center gap-1 mb-8">
        <span className="text-[10px] font-[family-name:var(--font-space-grotesk)] font-bold text-safe-red tracking-tighter">
          SEC 04
        </span>
      </div>
      <button className="text-safe-red font-bold border-l-4 border-safe-red bg-surface w-full py-4 flex flex-col items-center gap-1 active:scale-95 transition-transform">
        <span className="material-symbols-outlined">target</span>
      </button>
      <button className="text-muted hover:text-secondary w-full py-4 flex flex-col items-center gap-1 active:scale-95 transition-transform">
        <span className="material-symbols-outlined">sensors</span>
      </button>
      <button className="text-muted hover:text-secondary w-full py-4 flex flex-col items-center gap-1 active:scale-95 transition-transform">
        <span className="material-symbols-outlined">joystick</span>
      </button>
      <button className="text-muted hover:text-secondary w-full py-4 flex flex-col items-center gap-1 active:scale-95 transition-transform">
        <span className="material-symbols-outlined">receipt_long</span>
      </button>
    </nav>
  );
}
