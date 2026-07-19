import { Shield, Gamepad2, LineChart } from 'lucide-react';

interface BottomNavbarProps {
  currentTab: 'auto' | 'manual' | 'analisis';
  onTabChange: (tab: 'auto' | 'manual' | 'analisis') => void;
}

export function BottomNavbar({ currentTab, onTabChange }: BottomNavbarProps) {
  const indicatorStyle = {
    auto: 'left-[6px]',
    manual: 'left-[122px]',
    analisis: 'left-[238px]',
  }[currentTab];

  return (
    <>
      <style>{`
        .liquid-glass {
          background: rgba(10, 10, 15, 0.75); 
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.08);
        }

        .liquid-glass::before {
          content: "";
          position: absolute;
          inset: 0;
          padding: 1.4px; 
          border-radius: inherit;
          background: linear-gradient(180deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0) 100%);
          -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          pointer-events: none; 
        }
      `}</style>
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 rounded-full liquid-glass p-1.5 w-[360px]">
        <div className="relative flex h-11 w-full flex-row items-center justify-between">
          {/* Animated active sliding pill */}
          <div
            className={`absolute top-0 bottom-0 w-[116px] rounded-full bg-danger/20 transition-all duration-300 ease-out ${indicatorStyle}`}
          />

          <button
            onClick={() => onTabChange('auto')}
            className={`z-10 flex w-[116px] h-full flex-col items-center justify-center gap-0.5 transition-colors ${
              currentTab === 'auto' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
            }`}
          >
            <Shield className="h-4.5 w-4.5" />
            <span className="font-mono text-[9px] tracking-wider">OTOMATIS</span>
          </button>

          <button
            onClick={() => onTabChange('manual')}
            className={`z-10 flex w-[116px] h-full flex-col items-center justify-center gap-0.5 transition-colors ${
              currentTab === 'manual' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
            }`}
          >
            <Gamepad2 className="h-4.5 w-4.5" />
            <span className="font-mono text-[9px] tracking-wider">MANUAL</span>
          </button>

          <button
            onClick={() => onTabChange('analisis')}
            className={`z-10 flex w-[116px] h-full flex-col items-center justify-center gap-0.5 transition-colors ${
              currentTab === 'analisis' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
            }`}
          >
            <LineChart className="h-4.5 w-4.5" />
            <span className="font-mono text-[9px] tracking-wider">ANALISIS</span>
          </button>
        </div>
      </div>
    </>
  );
}
