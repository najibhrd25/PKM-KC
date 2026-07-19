import { Shield, Gamepad2 } from 'lucide-react';

interface BottomNavbarProps {
  currentTab: 'auto' | 'manual';
  onTabChange: (tab: 'auto' | 'manual') => void;
}

export function BottomNavbar({ currentTab, onTabChange }: BottomNavbarProps) {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 rounded-full liquid-glass px-8 py-2">
      <div className="flex h-12 flex-row items-center gap-12">
        <button
          onClick={() => onTabChange('auto')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            currentTab === 'auto' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
          }`}
        >
          <Shield className="h-5 w-5" />
          <span className="font-mono text-[10px] tracking-wider">AUTO</span>
        </button>

        <button
          onClick={() => onTabChange('manual')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            currentTab === 'manual' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
          }`}
        >
          <Gamepad2 className="h-5 w-5" />
          <span className="font-mono text-[10px] tracking-wider">MANUAL</span>
        </button>
      </div>
    </div>
  );
}
