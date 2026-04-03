'use client';

import { useSystemState } from '@/store/useSystemState';
import Header from '@/components/layout/Header';
import SideNav from '@/components/layout/SideNav';
import BottomNav from '@/components/layout/BottomNav';
import VideoFeed from '@/components/dashboard/VideoFeed';
import SensorCards from '@/components/dashboard/SensorCards';
import TacticalCard from '@/components/dashboard/TacticalCard';
import LogSection from '@/components/dashboard/LogSection';

export default function Home() {
  const { state, startupPhase } = useSystemState();
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

      {/* Main Content Canvas */}
      <main className={`lg:ml-20 pt-20 pb-20 px-4 lg:px-6 max-w-[1600px] mx-auto min-h-screen`}>
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

        {/* ===== DESKTOP LAYOUT (lg+) ===== */}
        <div className={`hidden lg:flex flex-row items-stretch gap-6 mb-12 transition-all duration-700 ${contentClass}`}>
          {/* Left Column: Video Feed (16:9 ratio) */}
          <div className="w-[75%] relative aspect-video">
            <div className="absolute inset-0">
              <VideoFeed />
            </div>
          </div>

          {/* Right Column: 3 Control Cards stacked vertically, strictly bound by left column's height */}
          <div className="w-[25%] relative">
            <div className="absolute inset-0 flex flex-col gap-4 min-h-0">
              <SensorCards />
              <TacticalCard />
            </div>
          </div>
        </div>

        {/* ===== MOBILE LAYOUT (<lg) ===== */}
        <div className={`lg:hidden space-y-4 mt-4 transition-all duration-700 ${contentClass}`}>
          {/* Section 1: Camera Feed (16:9 aspect, full-width) */}
          <div className="aspect-video w-full">
            <VideoFeed />
          </div>

          {/* Section 2: 2-Column Grid (Sensor + Controls) */}
          <div className="grid grid-cols-2 gap-3">
            {/* Col 1: Sensor Info (stacked vertically) */}
            <div className="space-y-4">
              <SensorCards />
            </div>

            {/* Col 2: Manual Controls */}
            <TacticalCard />
          </div>
        </div>

        {/* Bottom: Logs (both layouts) */}
        <div className="mt-8 lg:mt-12">
          <LogSection />
        </div>
      </main>

      <BottomNav />
    </>
  );
}
