'use client';

import { useState } from 'react';
import { useSystemState } from '@/store/useSystemState';
import AuthModal from '@/components/ui/AuthModal';

export default function TacticalCard() {
  const { state, isManual, deactivateManual } = useSystemState();
  const [showAuth, setShowAuth] = useState(false);
  const [joyPos, setJoyPos] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';
  const isLocked = !isManual;

  const handleControlClick = () => {
    if (isOff || isStarting) return;
    if (isLocked) {
      setShowAuth(true);
    }
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    if (isOff || isStarting || isLocked) return;
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging) return;
    // Calculate new position
    let newX = joyPos.x + e.movementX;
    let newY = joyPos.y + e.movementY;
    
    // Clamp to circle (radius 40px)
    const distance = Math.sqrt(newX * newX + newY * newY);
    if (distance > 40) {
      newX = (newX / distance) * 40;
      newY = (newY / distance) * 40;
    }
    
    setJoyPos({ x: newX, y: newY });
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    setIsDragging(false);
    setJoyPos({ x: 0, y: 0 }); // Spring back to center
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  return (
    <>
      <div
        className={`flex-[2] bg-surface-container p-4 lg:p-5 flex flex-col items-center justify-center gap-4 border-t-2 border-primary-container relative ${
          isOff ? 'opacity-40' : ''
        }`}
      >
        {/* Lock indicator */}
        {!isOff && (
          <div className="absolute top-4 right-4 flex items-center gap-2">
            <button
              onClick={() => {
                if (isManual) {
                  deactivateManual();
                } else {
                  setShowAuth(true);
                }
              }}
              className="flex items-center gap-1 text-xs"
            >
              <span
                className={`material-symbols-outlined text-sm ${
                  isManual ? 'text-green-500' : 'text-safe-red animate-pulse'
                }`}
              >
                {isManual ? 'lock_open' : 'lock'}
              </span>
              <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted tracking-widest uppercase">
                {isManual ? 'MANUAL' : 'AUTO'}
              </span>
            </button>
          </div>
        )}

        {/* Joystick */}
        <div
          onClick={handleControlClick}
          className={`relative w-20 h-20 lg:w-28 lg:h-28 rounded-full border border-outline-variant flex items-center justify-center bg-surface-container-low ${
            isLocked && !isOff ? 'cursor-pointer' : ''
          }`}
        >
          <div className="w-14 h-14 lg:w-20 lg:h-20 rounded-full border border-dashed border-secondary/30 absolute" />
          
          <div 
            className="w-10 h-10 lg:w-14 lg:h-14 bg-surface-container-highest rounded-full flex items-center justify-center shadow-[0_5px_15px_rgba(0,0,0,0.5)] border border-outline-variant/30 touch-none z-10"
            style={{ transform: `translate(${joyPos.x}px, ${joyPos.y}px)`, transition: isDragging ? 'none' : 'transform 0.2s cubic-bezier(0.18, 0.89, 0.32, 1.28)' }}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
          >
            <div className="w-3 h-3 lg:w-4 lg:h-4 rounded-full bg-secondary/10 flex items-center justify-center">
               <div className={`w-1.5 h-1.5 lg:w-2 lg:h-2 rounded-full ${isLocked ? 'bg-secondary' : 'bg-primary shadow-[0_0_8px_#ffb4ab]'}`} />
            </div>
          </div>
          
          <span className="material-symbols-outlined text-secondary/40 absolute top-1 lg:top-2 text-sm lg:text-base pointer-events-none">
            north
          </span>
          <span className="material-symbols-outlined text-secondary/40 absolute bottom-1 lg:bottom-2 text-sm lg:text-base pointer-events-none">
            south
          </span>
          <span className="material-symbols-outlined text-secondary/40 absolute left-1 lg:left-2 text-sm lg:text-base pointer-events-none">
            west
          </span>
          <span className="material-symbols-outlined text-secondary/40 absolute right-1 lg:right-2 text-sm lg:text-base pointer-events-none">
            east
          </span>

          {/* Lock overlay when locked */}
          {isLocked && !isOff && !isStarting && (
            <div className="absolute inset-0 rounded-full bg-black/60 flex items-center justify-center backdrop-blur-[2px] z-20">
              <span className="material-symbols-outlined text-safe-red text-lg lg:text-xl drop-shadow-[0_0_8px_#dc2626] animate-pulse">
                lock
              </span>
            </div>
          )}
        </div>

        {/* Bottom Controls */}
        <div className="w-full bg-surface-container-low p-3 text-center border-t border-outline-variant/10">
          <div className="flex justify-between items-center px-2 lg:px-4">
            <div className="text-left">
              <span className="block font-[family-name:var(--font-jetbrains-mono)] text-[8px] lg:text-[10px] text-muted tracking-widest uppercase mb-0.5">
                Recovery Mode
              </span>
              <span
                className={`font-[family-name:var(--font-jetbrains-mono)] text-[8px] lg:text-[10px] uppercase font-bold tracking-widest transition-colors ${
                  isOff ? 'text-muted' : isLocked ? 'text-white' : 'text-primary'
                }`}
              >
                {isOff ? 'OFFLINE' : isLocked ? 'AUTO' : 'MANUAL'}
              </span>
            </div>
            <button
              onClick={handleControlClick}
              disabled={isOff || isLocked}
              className={`px-4 lg:px-8 py-2 lg:py-3 font-[family-name:var(--font-space-grotesk)] text-xs lg:text-sm font-bold tracking-[0.2em] transition-all ${
                isOff || isLocked
                  ? 'bg-surface-container-highest text-muted cursor-not-allowed'
                  : 'bg-safe-red text-white hover:bg-red-500 shadow-[0_0_15px_rgba(220,38,38,0.5)] hover:shadow-[0_0_25px_rgba(220,38,38,0.8)]'
              }`}
            >
              SHOOT
            </button>
          </div>
        </div>
      </div>

      {/* Auth Modal */}
      <AuthModal isOpen={showAuth} onClose={() => setShowAuth(false)} />
    </>
  );
}
