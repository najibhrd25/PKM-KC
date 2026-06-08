'use client';

import { useSystemState } from '@/store/useSystemState';
import Header from '@/components/layout/Header';
import SideNav from '@/components/layout/SideNav';
import BottomNav from '@/components/layout/BottomNav';
import VideoFeed from '@/components/dashboard/VideoFeed';
import SensorCards from '@/components/dashboard/SensorCards';
import TacticalCard from '@/components/dashboard/TacticalCard';
import LogSection from '@/components/dashboard/LogSection';
import { useStartupAudio } from '@/platform/web/useStartupAudio';

export default function Home() {
  const { state, startupPhase } = useSystemState();
  useStartupAudio(startupPhase);

  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';

  // Determine main content class based on system state
  const contentClass = isOff
    ? 'system-off'
    : isStarting && !startupPhase.filterRemoved
    ? 'system-off'
    : 'system-waking';

  return (
    <>
      <Header />
      <SideNav />

      <main className="min-h-screen max-w-[1600px] mx-auto px-4 pt-20 pb-24 lg:ml-20 lg:px-6 lg:pb-20">
        {/* Dashboard Header (Desktop only) */}
        <div className="hidden lg:flex justify-between items-end mb-10 mt-8">
          <div>
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-muted tracking-[0.3em] uppercase mb-1">
              System Status: {isOff ? 'Cold Standby' : isStarting ? 'Initializing...' : 'Active Monitoring'}
            </p>
            <h1 className="text-4xl font-[family-name:var(--font-space-grotesk)] font-bold tracking-tighter text-on-surface">
              MISSION CONTROL
            </h1>
          </div>
          <div className="text-right">
            <p className="font-[family-name:var(--font-jetbrains-mono)] text-xs text-muted uppercase">Sector Coordination</p>
            <p className="font-[family-name:var(--font-space-grotesk)] text-lg text-primary tracking-tighter">
              42.3601° N, 71.0589° W
            </p>
          </div>
        </div>

        <div className={`hidden lg:flex flex-row items-stretch gap-6 mb-12 transition-all duration-700 ${contentClass}`}>
          <div className="w-[75%] relative aspect-video">
            <div className="absolute inset-0">
              <VideoFeed />
            </div>
          </div>

          <div className="w-[25%] relative">
            <div className="absolute inset-0 flex flex-col gap-4 min-h-0">
              <SensorCards />
              <TacticalCard />
            </div>
          </div>
        </div>

        <div className={`lg:hidden space-y-4 transition-all duration-700 ${contentClass}`}>
          <section aria-label="Live camera feed" className="-mx-4 aspect-square">
            <VideoFeed variant="mobile" />
          </section>

          <section aria-label="Sensors and manual controls" className="grid grid-cols-2 gap-3">
            <div className="flex min-h-[260px] flex-col gap-3">
              <SensorCards />
            </div>
            <TacticalCard />
          </section>
        </div>

        <div className="mt-8 lg:mt-12">
          <LogSection />
        </div>
      </main>

      <BottomNav />
    </>
  );
}
