'use client';

import { useSystemState } from '@/store/useSystemState';
import { useState } from 'react';

export default function Header() {
  const { state, powerOn, powerOff } = useSystemState();
  const [showConfirm, setShowConfirm] = useState(false);

  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';

  const handlePowerClick = () => {
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    if (isOff) {
      powerOn();
    } else {
      powerOff();
    }
    setShowConfirm(false);
  };

  return (
    <>
      <header
        className={`bg-surface-container-lowest text-safe-red font-[family-name:var(--font-space-grotesk)] tracking-tight flex justify-between items-center w-full px-6 py-4 fixed top-0 z-50 transition-colors ${
          isOff ? 'border-b border-white/5' : 'border-b border-[#dc2626]/20'
        }`}
      >
        {/* Left: Logo + Status */}
        <div className={`flex items-center gap-4 transition-all duration-700`}>
          <span className="text-2xl font-bold tracking-tighter text-safe-red flex flex-col leading-none">
            S.A.F.E.
            <span className={`text-[10px] font-normal tracking-widest mt-1 ${isOff ? 'text-white' : 'text-muted'}`}>
              [{isOff ? 'OFFLINE' : 'ONLINE'}]
            </span>
          </span>
          {/* Desktop nav links */}
          <div className="hidden lg:flex gap-8 ml-12">
            <a className="text-safe-red font-[family-name:var(--font-space-grotesk)] uppercase text-xs tracking-[0.2em]" href="#">
              MISSION
            </a>
            <a className="text-muted font-[family-name:var(--font-space-grotesk)] uppercase text-xs tracking-[0.2em] hover:text-secondary transition-colors" href="#">
              SENSORS
            </a>
            <a className="text-muted font-[family-name:var(--font-space-grotesk)] uppercase text-xs tracking-[0.2em] hover:text-secondary transition-colors" href="#">
              TACTICAL
            </a>
            <a className="text-muted font-[family-name:var(--font-space-grotesk)] uppercase text-xs tracking-[0.2em] hover:text-secondary transition-colors" href="#">
              LOGS
            </a>
          </div>
        </div>

        {/* Right: Power Toggle */}
        <div className="flex items-center gap-6">
          <button
            onClick={handlePowerClick}
            disabled={isStarting}
            className={`p-2 rounded-full transition-all ${
              isOff
                ? 'animate-[pulse-red_2s_cubic-bezier(0.4,0,0.6,1)_infinite] text-red-800'
                : 'text-safe-red power-glow hover:bg-surface-container-high'
            } ${isStarting ? 'cursor-wait' : 'cursor-pointer'}`}
            aria-label="Power Toggle"
          >
            <span className="material-symbols-outlined text-2xl">
              power_settings_new
            </span>
          </button>
        </div>
      </header>

      {/* Confirm Dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setShowConfirm(false)}
          />
          {/* Modal */}
          <div className="glass-modal relative z-10 p-8 max-w-md w-full mx-4 animate-[fade-in_0.3s_ease-out]">
            <div className="text-center">
              <span className="material-symbols-outlined text-5xl text-safe-red mb-4 block">
                {isOff ? 'power_settings_new' : 'power_off'}
              </span>
              <h2 className="font-[family-name:var(--font-space-grotesk)] text-xl font-bold text-on-surface mb-2 tracking-tight">
                {isOff
                  ? 'MENGAKTIFKAN SELURUH SISTEM S.A.F.E.?'
                  : 'SHUTDOWN ALL SYSTEMS?'}
              </h2>
              <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-muted mb-6 tracking-wider">
                {isOff
                  ? 'Startup Sequence akan dimulai.'
                  : 'Semua modul akan dimatikan.'}
              </p>
              <div className="flex gap-4 justify-center">
                <button
                  onClick={() => setShowConfirm(false)}
                  className="px-8 py-3 bg-surface-container-high text-secondary font-[family-name:var(--font-space-grotesk)] font-bold text-sm tracking-[0.2em] uppercase hover:bg-surface-container-highest transition-colors"
                >
                  NO
                </button>
                <button
                  onClick={handleConfirm}
                  className="px-8 py-3 bg-safe-red text-white font-[family-name:var(--font-space-grotesk)] font-bold text-sm tracking-[0.2em] uppercase hover:opacity-90 transition-all"
                >
                  YES
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
