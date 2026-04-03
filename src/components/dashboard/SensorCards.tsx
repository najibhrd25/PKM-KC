'use client';

import { useSystemState } from '@/store/useSystemState';

export default function SensorCards() {
  const { state, temperature, frequency, startupPhase } = useSystemState();
  const isOff = state === 'OFF_STATE';
  const numbersReady = startupPhase.numbersRolled;

  return (
    <>
      {/* Temperature Card */}
      <div className="flex-1 bg-surface-container-low p-4 lg:p-5 flex flex-col justify-between relative overflow-hidden group">
        <div className="absolute -inset-1 bg-gradient-to-br from-primary-container/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-2xl" />
        <div className="relative z-10 flex justify-between items-start">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[8px] lg:text-[10px] text-muted tracking-[0.2em] uppercase">
            Ambient Temp
          </span>
          <span className="material-symbols-outlined text-secondary opacity-50 text-sm lg:text-base">
            device_thermostat
          </span>
        </div>
        <div className="relative z-10 flex items-baseline gap-2 mt-1 lg:mt-0">
          <span
            className={`text-4xl lg:text-3xl xl:text-4xl leading-none font-[family-name:var(--font-space-grotesk)] font-bold text-on-surface tracking-tighter transition-all duration-500 ${numbersReady && !isOff ? 'animate-[roll-number_1s_ease-out] drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]' : ''
              }`}
          >
            {isOff ? '--' : temperature}
          </span>
          <span className="text-sm lg:text-3xl font-[family-name:var(--font-space-grotesk)] font-light text-secondary">
            {isOff ? '' : '°C'}
          </span>
        </div>
        <div className="relative z-10 w-full h-[2px] lg:h-1 bg-surface-container-highest mt-2 lg:mt-4 overflow-hidden rounded-full">
          <div
            className="h-full bg-gradient-to-r from-orange-500 to-red-500 transition-all duration-1000 rounded-full"
            style={{ width: isOff ? '0%' : `${(temperature / 100) * 100}%` }}
          />
        </div>
      </div>

      {/* Frequency Card */}
      <div className="flex-1 bg-surface-container-low p-4 lg:p-5 flex flex-col justify-between mt-0 relative overflow-hidden group">
        <div className="absolute -inset-1 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-2xl" />
        <div className="relative z-10 flex justify-between items-start">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[8px] lg:text-[10px] text-muted tracking-[0.2em] uppercase">
            Acoustic Range
          </span>
          <span className={`font-[family-name:var(--font-jetbrains-mono)] text-[8px] lg:text-[10px] ${isOff ? 'text-muted' : 'text-blue-400 animate-pulse'}`}>
            {isOff ? 'STANDBY' : 'ACTIVE SCANNING'}
          </span>
        </div>
        <div className="relative z-10 mt-1 lg:mt-auto mb-2 lg:mb-4">
          <p className="text-[8px] lg:text-[10px] font-[family-name:var(--font-jetbrains-mono)] uppercase tracking-widest text-secondary opacity-50 mb-0 lg:mb-1">Target Frequency</p>
          <p
            className={`text-2xl lg:text-3xl xl:text-4xl font-[family-name:var(--font-space-grotesk)] font-bold text-safe-red tracking-tight transition-all duration-500 ${numbersReady && !isOff ? 'animate-[roll-number_1s_ease-out] drop-shadow-[0_0_15px_rgba(220,38,38,0.2)]' : ''
              }`}
          >
            {isOff ? '-- Hz' : `${frequency} Hz`}
          </p>
        </div>
        <div className="relative z-10 flex items-end gap-[2px] h-6 lg:h-10 w-full">
          {[15, 30, 45, 80, 100, 70, 40, 20, 35, 65].map((h, i) => (
            <div
              key={i}
              className={`flex-1 rounded-sm transition-all duration-500 ${isOff
                ? 'bg-muted/10 h-[2px] lg:h-1'
                : `bg-gradient-to-t from-primary-container/20 to-primary-container ${i % 3 === 0 ? 'animate-pulse' : ''}`
                }`}
              style={{ height: isOff ? (typeof window !== 'undefined' && window.innerWidth >= 1024 ? '4px' : '2px') : `${h}%` }}
            />
          ))}
        </div>
      </div>
    </>
  );
}
