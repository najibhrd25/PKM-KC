'use client';

import { useSystemState } from '@/store/useSystemState';

const DUMMY_LOGS = [
  { date: '02 Apr 2026', time: '13:22:04', event: 'Api Terdeteksi', accuracy: '94.2%', status: 'BERHASIL DIPADAMKAN', isAlert: true },
  { date: '02 Apr 2026', time: '11:15:30', event: 'Pemeriksaan Rutin', accuracy: '--', status: 'AMAN — TIDAK ADA ANOMALI', isAlert: false },
  { date: '01 Apr 2026', time: '21:44:56', event: 'Api Terdeteksi', accuracy: '87.6%', status: 'BERHASIL DIPADAMKAN', isAlert: true },
  { date: '01 Apr 2026', time: '14:08:12', event: 'Percikan Listrik', accuracy: '62.1%', status: 'FALSE POSITIVE — DIABAIKAN', isAlert: false },
  { date: '31 Mar 2026', time: '09:30:00', event: 'Kalibrasi Sensor', accuracy: '--', status: 'SENSOR SUHU & AKUSTIK OK', isAlert: false },
  { date: '30 Mar 2026', time: '22:17:43', event: 'Api Terdeteksi', accuracy: '91.8%', status: 'BERHASIL DIPADAMKAN', isAlert: true },
  { date: '29 Mar 2026', time: '08:00:00', event: 'Sistem Dinyalakan', accuracy: '--', status: 'STARTUP SEQUENCE COMPLETE', isAlert: false },
];

const MOBILE_LOGS = [
  { time: '13:22:04', text: 'API TERDETEKSI — AKURASI 94.2% — DIPADAMKAN', isWarning: true },
  { time: '11:15:30', text: 'PEMERIKSAAN RUTIN — AMAN' },
  { time: '21:44:56', text: 'API TERDETEKSI — AKURASI 87.6% — DIPADAMKAN', isWarning: true },
  { time: '14:08:12', text: 'PERCIKAN LISTRIK — 62.1% — FALSE POSITIVE' },
  { time: '09:30:00', text: 'KALIBRASI SENSOR SUHU & AKUSTIK — OK' },
  { time: '22:17:43', text: 'API TERDETEKSI — AKURASI 91.8% — DIPADAMKAN', isWarning: true },
];

export default function LogSection() {
  const { state, startupPhase } = useSystemState();
  const isOff = state === 'OFF_STATE';
  const logsReady = startupPhase.logsInitialized;

  return (
    <div className="bg-surface-container-low p-6 lg:p-8">
      <div className="flex justify-between items-center mb-6 lg:mb-8">
        <div className="flex items-center gap-4">
          <h2 className={`text-lg lg:text-xl font-[family-name:var(--font-space-grotesk)] font-bold tracking-tight ${isOff ? 'text-white' : ''}`}>
            LOG KEJADIAN
          </h2>
          <span className={`px-2 py-1 bg-surface-container-high font-[family-name:var(--font-jetbrains-mono)] text-[10px] ${isOff ? 'text-white font-bold' : 'text-secondary'}`}>
            {isOff ? 'OFFLINE' : 'REAL-TIME SYNC'}
          </span>
        </div>
        <button
          disabled={isOff}
          className={`px-4 lg:px-6 py-2 flex items-center gap-2 text-xs font-[family-name:var(--font-space-grotesk)] font-bold uppercase tracking-widest text-white transition-colors ${
            isOff
              ? 'bg-muted/30 cursor-not-allowed'
              : 'bg-safe-red hover:bg-on-primary-fixed-variant'
          }`}
        >
          <span className="material-symbols-outlined text-sm">picture_as_pdf</span>
          <span className="hidden sm:inline">Export PDF</span>
        </button>
      </div>

      {/* Desktop: Table view */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full text-left">
          <thead className="border-b border-outline-variant/10">
            <tr className="text-muted font-[family-name:var(--font-jetbrains-mono)] text-[10px] tracking-widest uppercase">
              <th className="pb-4 font-normal">Tanggal</th>
              <th className="pb-4 font-normal">Waktu</th>
              <th className="pb-4 font-normal">Kejadian</th>
              <th className="pb-4 font-normal">Akurasi API</th>
              <th className="pb-4 font-normal text-right">Status</th>
            </tr>
          </thead>
          <tbody className="font-[family-name:var(--font-jetbrains-mono)] text-xs divide-y divide-outline-variant/5">
            {isOff || !logsReady ? (
              <tr>
                <td colSpan={5} className={`py-8 text-center ${isOff ? 'text-white opacity-80' : 'text-muted'}`}>
                  {isOff ? 'SYSTEM OFFLINE — NO DATA' : 'INITIALIZING LOGS...'}
                </td>
              </tr>
            ) : (
              DUMMY_LOGS.map((log, i) => (
                <tr key={i} className="hover:bg-surface-container-high/40 transition-colors animate-[fade-in_0.5s_ease-out]" style={{ animationDelay: `${i * 100}ms` }}>
                  <td className="py-4 text-on-surface">{log.date}</td>
                  <td className="py-4 text-on-surface">{log.time}</td>
                  <td className="py-4">
                    <span className={log.isAlert ? 'text-primary font-bold' : 'text-secondary'}>{log.event}</span>
                  </td>
                  <td className="py-4 text-secondary">{log.accuracy}</td>
                  <td className="py-4 text-right">
                    <span className={log.status.includes('BERHASIL DIPADAMKAN') ? 'text-green-500 font-bold' : log.isAlert ? 'text-safe-red font-bold' : 'text-secondary'}>{log.status}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile: List view */}
      <div className="lg:hidden space-y-2 font-[family-name:var(--font-jetbrains-mono)] text-[10px]">
        {isOff || !logsReady ? (
          <div className={`text-center py-6 ${isOff ? 'text-white opacity-80' : 'text-muted'}`}>
            {isOff ? 'SYSTEM OFFLINE' : 'INITIALIZING...'}
          </div>
        ) : (
          MOBILE_LOGS.map((log, i) => (
            <div
              key={i}
              className="flex gap-3 animate-[fade-in_0.5s_ease-out]"
              style={{ animationDelay: `${i * 150}ms` }}
            >
              <span className="opacity-50 text-white font-normal w-[45px] shrink-0">{log.time}</span>
              <span className="flex-1 whitespace-nowrap overflow-hidden text-ellipsis">
                {log.text.split(' — ').map((part, idx, arr) => (
                  <span key={idx}>
                    <span className={
                      part.includes('API TERDETEKSI') || part.includes('PERCIKAN LISTRIK') || part.includes('AKURASI') ? 'text-safe-red font-bold' :
                      part.includes('DIPADAMKAN') || part.includes('AMAN') ? 'text-green-500 font-bold' :
                      'text-white'
                    }>
                      {part}
                    </span>
                    {idx < arr.length - 1 && <span className="mx-1 text-muted/30">—</span>}
                  </span>
                ))}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
