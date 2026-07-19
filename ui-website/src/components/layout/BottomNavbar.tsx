import { Shield, Gamepad2, History } from 'lucide-react';
import { useRef, useState, useEffect } from 'react';

interface BottomNavbarProps {
  currentTab: 'auto' | 'manual' | 'riwayat';
  onTabChange: (tab: 'auto' | 'manual' | 'riwayat') => void;
}

export function BottomNavbar({ currentTab, onTabChange }: BottomNavbarProps) {
  const navbarRef = useRef<HTMLDivElement>(null);
  const autoRef = useRef<HTMLDivElement>(null);
  const manualRef = useRef<HTMLDivElement>(null);
  const riwayatRef = useRef<HTMLDivElement>(null);

  const [indicator, setIndicator] = useState({ left: 0, width: 0 });

  useEffect(() => {
    const refs = {
      auto: autoRef,
      manual: manualRef,
      riwayat: riwayatRef,
    };
    const activeRef = refs[currentTab];

    if (activeRef.current && navbarRef.current) {
      const activeRect = activeRef.current.getBoundingClientRect();
      const navbarRect = navbarRef.current.getBoundingClientRect();
      
      const paddingX = 16; // breathing room for the indicator pill
      
      setIndicator({
        left: activeRect.left - navbarRect.left - paddingX,
        width: activeRect.width + paddingX * 2,
      });
    }
  }, [currentTab]);

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
      <div 
        ref={navbarRef}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 rounded-full liquid-glass p-1.5 w-[360px]"
      >
        <div className="relative flex h-11 w-full flex-row items-center justify-between">
          {/* Animated active sliding pill */}
          <div
            className="absolute top-0 bottom-0 rounded-full bg-danger/20 transition-all duration-300 ease-out"
            style={{
              left: `${indicator.left}px`,
              width: `${indicator.width}px`,
            }}
          />

          <button
            onClick={() => onTabChange('auto')}
            className={`z-10 flex flex-1 h-full items-center justify-center transition-colors ${
              currentTab === 'auto' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
            }`}
          >
            <div ref={autoRef} className="flex flex-col items-center justify-center gap-0.5">
              <Shield className="h-4.5 w-4.5" />
              <span className="font-mono text-[9px] tracking-wider">OTOMATIS</span>
            </div>
          </button>

          <button
            onClick={() => onTabChange('manual')}
            className={`z-10 flex flex-1 h-full items-center justify-center transition-colors ${
              currentTab === 'manual' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
            }`}
          >
            <div ref={manualRef} className="flex flex-col items-center justify-center gap-0.5">
              <Gamepad2 className="h-4.5 w-4.5" />
              <span className="font-mono text-[9px] tracking-wider">MANUAL</span>
            </div>
          </button>

          <button
            onClick={() => onTabChange('riwayat')}
            className={`z-10 flex flex-1 h-full items-center justify-center transition-colors ${
              currentTab === 'riwayat' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
            }`}
          >
            <div ref={riwayatRef} className="flex flex-col items-center justify-center gap-0.5">
              <History className="h-4.5 w-4.5" />
              <span className="font-mono text-[9px] tracking-wider">RIWAYAT</span>
            </div>
          </button>
        </div>
      </div>
    </>
  );
}
