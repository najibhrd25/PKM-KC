import { useState, useEffect } from 'react';

import { Header } from '@/components/features/Header';
import { BottomNavbar } from '@/components/layout/BottomNavbar';
import { AutoModeSection } from '@/components/sections/AutoModeSection';
import { ManualModeSection } from '@/components/sections/ManualModeSection';
import { RiwayatSection } from '@/components/sections/RiwayatSection';
import { createRaspberryPiCameraSource } from '@/lib/cameraSource';
import { shareActivityReport } from '@/lib/activityReport';
import { triggerAcousticPulse, getCameraStreamUrl, homeServo, stopServo } from '@/lib/safeApi';
import { useSystemState } from '@/store/useSystemState';

export function MissionControlScreen() {
  const [isExporting, setIsExporting] = useState(false);
  const [activeTab, setActiveTab] = useState<'auto' | 'manual' | 'analisis'>('auto');

  const {
    waveform,
    frequency,
    amplitude,
    duration,
    activityLogs,
    isManual,
    startupPhase,
    state,
    temperature,
    setWaveform,
    setFrequency,
    setAmplitude,
    setDuration,
    activateManual,
    deactivateManual,
  } = useSystemState();

  useEffect(() => {
    // Auto-initialize SSE when dashboard is visited
    useSystemState.getState()._initSSE();

    return () => {
      useSystemState.getState()._closeSSE();
    };
  }, []);

  // Sync tab with hardware mode changes
  useEffect(() => {
    if (isManual && activeTab === 'auto') {
      setActiveTab('manual');
    } else if (!isManual && activeTab === 'manual') {
      setActiveTab('auto');
    }
  }, [isManual]);

  const streamUrl = getCameraStreamUrl();
  const liveCameraSource = createRaspberryPiCameraSource(streamUrl);

  function handlePowerPress() {
    stopServo().catch(() => {});
  }

  function handleHomePress() {
    homeServo().catch(() => {});
  }

  function handleShoot() {
    triggerAcousticPulse({ action: 'shoot', waveform, frequency, amplitude, duration }).catch(() => {});
  }

  function handleTabChange(tab: 'auto' | 'manual' | 'analisis') {
    setActiveTab(tab);
    if (tab === 'manual') {
      activateManual();
    } else if (tab === 'auto') {
      deactivateManual();
    }
  }

  async function handleExportReport() {
    try {
      setIsExporting(true);
      await shareActivityReport({
        frequency,
        logs: activityLogs,
        state,
        temperature,
      });
    } catch {
      alert('Export failed: The PDF report could not be created.');
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="flex min-h-dvh w-full flex-1 flex-col bg-background">
      <Header state={state} isManual={isManual} onPowerPress={handlePowerPress} onHomePress={handleHomePress} />

      <div className="flex w-full flex-1 flex-col gap-3 overflow-y-auto px-4 pb-20">
        <div className="flex flex-col gap-0.5 pt-1">
          <span
            className={`font-mono text-[9px] font-bold tracking-[2px] ${
              activeTab === 'auto'
                ? 'text-success'
                : activeTab === 'manual'
                ? 'text-danger-soft'
                : 'text-info'
            }`}
          >
            {activeTab === 'manual'
              ? 'MANUAL CONTROL ACTIVE'
              : activeTab === 'analisis'
              ? 'SYSTEM DIAGNOSTICS'
              : 'AUTOMATIC MONITORING ACTIVE'}
          </span>
          <h1 className="text-[22px] font-black tracking-tight text-foreground leading-tight">
            MISSION CONTROL
          </h1>
        </div>

        {activeTab === 'manual' && (
          <ManualModeSection
            streamSource={liveCameraSource}
            waveform={waveform}
            frequency={frequency}
            amplitude={amplitude}
            duration={duration}
            setWaveform={setWaveform}
            setFrequency={setFrequency}
            setAmplitude={setAmplitude}
            setDuration={setDuration}
            onShoot={handleShoot}
            activityLogs={activityLogs}
            logsReady={startupPhase.logsInitialized}
            isExporting={isExporting}
            onExport={handleExportReport}
          />
        )}

        {activeTab === 'auto' && (
          <AutoModeSection
            streamSource={liveCameraSource}
            waveform={waveform}
            frequency={frequency}
            amplitude={amplitude}
            duration={duration}
            activityLogs={activityLogs}
            logsReady={startupPhase.logsInitialized}
            isExporting={isExporting}
            onExport={handleExportReport}
          />
        )}

        {activeTab === 'analisis' && (
          <RiwayatSection
            temperature={temperature}
            activityLogsCount={activityLogs.length}
          />
        )}
      </div>

      <BottomNavbar currentTab={activeTab} onTabChange={handleTabChange} />
    </div>
  );
}
