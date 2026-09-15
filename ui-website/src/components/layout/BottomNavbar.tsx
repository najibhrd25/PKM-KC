import { Shield, Gamepad2, LineChart } from 'lucide-react';

interface BottomNavbarProps {
  currentTab: 'auto' | 'manual' | 'analisis';
  onTabChange: (tab: 'auto' | 'manual' | 'analisis') => void;
}

export function BottomNavbar({ currentTab, onTabChange }: BottomNavbarProps) {
  // Posisi horizontal sliding indicator (33.333% per tab)
  const indicatorPosition = {
    auto: 'left-0',
    manual: 'left-1/3',
    analisis: 'left-2/3',
  }[currentTab];

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 w-full border-t border-border/40 bg-surface/95 backdrop-blur-xl shadow-2xl pb-safe">
      <div className="relative mx-auto flex h-14 w-full max-w-md flex-row items-center justify-between px-0 py-1">
        {/* Animated active sliding container */}
        <div
          className={`absolute top-1 bottom-1 w-1/3 transition-all duration-300 ease-out ${indicatorPosition} ${currentTab === 'auto'
              ? 'rounded-r-full rounded-l-none bg-danger/20 border-r border-y border-danger/35'
              : currentTab === 'analisis'
                ? 'rounded-l-full rounded-r-none bg-danger/20 border-l border-y border-danger/35'
                : 'px-2'
            }`}
        >
          {currentTab === 'manual' && (
            <div className="w-full h-full rounded-full bg-danger/20 border border-danger/35" />
          )}
        </div>

        {/* Tab 1: Otomatis */}
        <button
          type="button"
          onClick={() => onTabChange('auto')}
          className={`z-10 flex w-1/3 h-full flex-col items-center justify-center gap-0.5 transition-colors ${currentTab === 'auto'
              ? 'text-danger-soft font-bold'
              : 'text-muted hover:text-foreground font-medium'
            }`}
        >
          <Shield className="h-5 w-5" />
          <span className="font-mono text-[9px] tracking-wider">OTOMATIS</span>
        </button>

        {/* Tab 2: Manual */}
        <button
          type="button"
          onClick={() => onTabChange('manual')}
          className={`z-10 flex w-1/3 h-full flex-col items-center justify-center gap-0.5 transition-colors ${currentTab === 'manual'
              ? 'text-danger-soft font-bold'
              : 'text-muted hover:text-foreground font-medium'
            }`}
        >
          <Gamepad2 className="h-5 w-5" />
          <span className="font-mono text-[9px] tracking-wider">MANUAL</span>
        </button>

        {/* Tab 3: Analisis */}
        <button
          type="button"
          onClick={() => onTabChange('analisis')}
          className={`z-10 flex w-1/3 h-full flex-col items-center justify-center gap-0.5 transition-colors ${currentTab === 'analisis'
              ? 'text-danger-soft font-bold'
              : 'text-muted hover:text-foreground font-medium'
            }`}
        >
          <LineChart className="h-5 w-5" />
          <span className="font-mono text-[9px] tracking-wider">ANALISIS</span>
        </button>
      </div>
    </div>
  );
}
