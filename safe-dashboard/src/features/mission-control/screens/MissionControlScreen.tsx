import { useState, useEffect } from 'react';

import { ActivityLog } from '@/features/mission-control/components/ActivityLog';
import { MissionHeader } from '@/features/mission-control/components/MissionHeader';
import { SensorPanel } from '@/features/mission-control/components/SensorPanel';
import { TacticalControls } from '@/features/mission-control/components/TacticalControls';
import { VideoPanel } from '@/features/mission-control/components/VideoPanel';
import { createRaspberryPiCameraSource } from '@/services/camera/cameraSource';
import { shareActivityReport } from '@/services/reports/activityReport';
import { triggerAcousticPulse, getCameraStreamUrl, homeServo, stopServo } from '@/services/safe-api/safeApi';
import { useSystemState } from '@/store/useSystemState';

export function MissionControlScreen() {
  const [isExporting, setIsExporting] = useState(false);
  const {
    authPassword,
    waveform,
    frequency,
    amplitude,
    duration,
    activityLogs,
    isManual,
    powerOff,
    powerOn,
    startupPhase,
    state,
    temperature,
    setWaveform,
    setFrequency,
    setAmplitude,
    setDuration,
    pingActivity,
  } = useSystemState();

  useEffect(() => {
    // Auto-initialize SSE when dashboard is visited
    useSystemState.getState()._initSSE();

    if (!isManual) return;
    
    const handleActivity = () => {
      pingActivity();
    };

    window.addEventListener('pointermove', handleActivity);
    window.addEventListener('keydown', handleActivity);
    window.addEventListener('touchstart', handleActivity);

    return () => {
      useSystemState.getState()._closeSSE();
      window.removeEventListener('pointermove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('touchstart', handleActivity);
    };
  }, [isManual, pingActivity]);

  const isOff = state === 'OFF_STATE';
  const isStarting = state === 'STARTUP_SEQUENCE';
  const contentDisabled = isOff || (isStarting && !startupPhase.filterRemoved);

  const streamUrl = getCameraStreamUrl();
  const liveCameraSource = createRaspberryPiCameraSource(streamUrl);

  function handlePowerPress() {
    // Only stop/disable the servo
    stopServo().catch(() => {});
  }

  function handleHomePress() {
    homeServo().catch(() => {});
  }

  function handleShoot() {
    triggerAcousticPulse({ action: 'shoot', waveform, frequency, amplitude, duration }).catch(() => {});
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
      <MissionHeader state={state} isManual={isManual} onPowerPress={handlePowerPress} onHomePress={handleHomePress} />

      <div className="flex w-full flex-1 flex-col gap-4 overflow-y-auto px-4 pb-8">
        <div className="flex flex-col gap-1 pt-2">
          <span className="font-mono text-[10px] tracking-[2.4px] text-muted">
            {isOff ? 'COLD STANDBY' : isStarting ? 'INITIALIZING' : 'ACTIVE MONITORING'}
          </span>
          <h1 className="text-[30px] font-black tracking-[-1px] text-foreground">
            MISSION CONTROL
          </h1>
        </div>

        <div className={contentDisabled ? 'opacity-[0.62]' : ''}>
          <VideoPanel
            cameraVisible={startupPhase.cameraVisible}
            isOff={isOff}
            source={liveCameraSource}
          />

          <div className="mt-4 flex min-h-[286px] w-full flex-row gap-3">
            <SensorPanel
              waveform={waveform}
              frequency={frequency}
              amplitude={amplitude}
              duration={duration}
              isOff={isOff}
              isManual={isManual}
              setWaveform={setWaveform}
              setFrequency={setFrequency}
              setAmplitude={setAmplitude}
              setDuration={setDuration}
            />
            <TacticalControls
              frequency={frequency}
              isManual={isManual}
              isOff={isOff}
              isStarting={isStarting}
              onAuthorize={authPassword}
              onShoot={handleShoot}
            />
          </div>

          <div className="mt-4">
            <ActivityLog
              isExporting={isExporting}
              isOff={isOff}
              logsReady={startupPhase.logsInitialized}
              onExport={handleExportReport}
              logs={activityLogs}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
