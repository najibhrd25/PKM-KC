import { useState, useEffect } from 'react';
import { Home, Download, X, Smartphone, Share2 } from 'lucide-react';
import safeLogo from '@/assets/safe-logo.svg';
import { StatusPill } from '@/components/ui/StatusPill';

interface HeaderProps {
  state: string;
  isManual: boolean;
  onPowerPress: () => void;
  onHomePress: () => void;
}

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

export function Header({ state, isManual, onPowerPress, onHomePress }: HeaderProps) {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      try {
        await deferredPrompt.prompt();
        const choice = await deferredPrompt.userChoice;
        if (choice.outcome === 'accepted') {
          setDeferredPrompt(null);
          return;
        }
      } catch {
        setShowGuide(true);
        return;
      }
    }
    setShowGuide(true);
  };

  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';

  const isPulsing = !isOff && !isStarting && !isManual;

  return (
    <>
      <div className="flex w-full flex-row items-center justify-between px-4 py-2.5">
        <div className="flex flex-row items-center gap-2.5">
          <img src={safeLogo} alt="S.A.F.E. Logo" className="h-[54px] w-[54px] object-contain" />
          <div>
            <p className="text-lg font-black tracking-[-0.5px] text-foreground leading-none mb-1">
              S.A.F.E.
            </p>
            <StatusPill
              label={isOff ? 'OFFLINE' : isStarting ? 'STARTING' : 'ONLINE'}
              tone={isOff ? 'idle' : 'active'}
              isPulsing={isPulsing}
            />
          </div>
        </div>

        <div className="flex flex-row items-center gap-2">
          {/* Tombol Download Hijau (PWA Install) */}
          <button
            type="button"
            aria-label="Download Aplikasi"
            title="Download / Pasang Aplikasi ke HP"
            onClick={handleInstallClick}
            className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25 active:scale-[0.96] transition-all shadow-sm"
          >
            <Download className="h-4.5 w-4.5 text-emerald-400" />
          </button>

          <button
            type="button"
            aria-label="Home Servo"
            className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-full border transition-transform active:scale-[0.96] active:opacity-75 ${
              isOff
                ? 'border-border/30 opacity-40'
                : 'border-border bg-surface-high'
            }`}
            onClick={onHomePress}
            disabled={isOff || isStarting}
          >
            <Home className="h-4.5 w-4.5 text-muted" />
          </button>

          <button
            type="button"
            aria-label={isOff ? 'Power on system' : 'Power off system'}
            className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-full border transition-transform active:scale-[0.96] active:opacity-75 ${
              isOff
                ? 'border-border/40 bg-surface-high opacity-50 text-muted'
                : 'border-danger-soft bg-danger text-white'
            }`}
            onClick={onPowerPress}
          >
            <span className="font-mono text-[11px] font-extrabold text-white">
              {isOff ? 'OFF' : 'ON'}
            </span>
          </button>
        </div>
      </div>

      {/* Panduan Instalasi Modal (PWA) */}
      {showGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 px-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-sm rounded-2xl border border-border/80 bg-[#161616] p-5 shadow-2xl">
            <button
              type="button"
              onClick={() => setShowGuide(false)}
              className="absolute right-3.5 top-3.5 flex h-8 w-8 items-center justify-center rounded-full bg-surface-high text-muted hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="flex items-center gap-2.5 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                <Smartphone className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">Pasang ke Layar Utama</h3>
                <p className="text-xs text-muted">Jadikan aplikasi native di HP Anda</p>
              </div>
            </div>

            <div className="space-y-2.5 my-4 text-xs text-muted leading-relaxed">
              <div className="rounded-xl border border-border/50 bg-[#1c1c1c] p-3">
                <p className="font-semibold text-foreground mb-1 flex items-center gap-1.5">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">1</span>
                  Untuk Google Chrome (Android):
                </p>
                <p>
                  Ketuk titik tiga <strong className="text-foreground">`⋮`</strong> di pojok kanan atas browser &rarr; pilih <strong className="text-emerald-400">"Tambahkan ke Layar Utama"</strong> atau <strong className="text-emerald-400">"Instal aplikasi"</strong>.
                </p>
              </div>

              <div className="rounded-xl border border-border/50 bg-[#1c1c1c] p-3">
                <p className="font-semibold text-foreground mb-1 flex items-center gap-1.5">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">2</span>
                  Untuk Safari (iPhone / iPad):
                </p>
                <p className="flex items-start gap-1">
                  Ketuk tombol Bagikan <Share2 className="h-3.5 w-3.5 inline mx-0.5 mt-0.5 text-foreground" /> &rarr; gulir ke bawah dan pilih <strong className="text-emerald-400">"Add to Home Screen"</strong>.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowGuide(false)}
              className="w-full rounded-xl bg-emerald-500/20 border border-emerald-500/40 py-2.5 text-center text-xs font-bold text-emerald-400 hover:bg-emerald-500/30 active:scale-98 transition-all"
            >
              Saya Mengerti
            </button>
          </div>
        </div>
      )}
    </>
  );
}
