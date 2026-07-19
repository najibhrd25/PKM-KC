import { Shield, Gamepad2 } from 'lucide-react';

interface BottomNavbarProps {
  currentTab: 'auto' | 'manual';
  onTabChange: (tab: 'auto' | 'manual') => void;
}

export function BottomNavbar({ currentTab, onTabChange }: BottomNavbarProps) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-surface/90 pb-safe-bottom backdrop-blur-md">
      <div className="flex h-16 w-full flex-row items-center justify-around px-6">
        <button
          onClick={() => onTabChange('auto')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            currentTab === 'auto' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
          }`}
        >
          <Shield className="h-5 w-5" />
          <span className="font-mono text-[10px] tracking-wider">AUTO MODE</span>
        </button>

        <button
          onClick={() => onTabChange('manual')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            currentTab === 'manual' ? 'text-danger-soft font-bold' : 'text-muted hover:text-foreground'
          }`}
        >
          <Gamepad2 className="h-5 w-5" />
          <span className="font-mono text-[10px] tracking-wider">MANUAL MODE</span>
        </button>
      </div>
    </div>
  );
}
