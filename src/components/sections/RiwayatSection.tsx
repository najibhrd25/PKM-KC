import { useState } from 'react';
import {
  Calendar,
  Flame,
  CheckCircle2,
  XCircle,
  Cpu,
  X,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { StatusPill } from '@/components/ui/StatusPill';

interface MonthlyLogRecord {
  id: string;
  date: string;
  time: string;
  title: string;
  freq: string;
  duration: string;
  status: 'success' | 'failed';
  notes: string;
}

interface MonthData {
  id: string;
  name: string;
  year: string;
  totalTests: number;
  successRate: string;
  avgDuration: string;
  records: MonthlyLogRecord[];
}

const MONTHLY_RECORDS: MonthData[] = [
  {
    id: 'juni',
    name: 'Juni',
    year: '2026',
    totalTests: 4,
    successRate: '75%',
    avgDuration: '9.4s',
    records: [
      {
        id: 'jun-4',
        date: '28 Jun',
        time: '14:20',
        title: 'Uji Resonansi Awal',
        freq: '40 Hz',
        duration: '8.8s',
        status: 'success',
        notes: 'Api padam jarak 30 cm dengan gelombang sinus.',
      },
      {
        id: 'jun-3',
        date: '21 Jun',
        time: '16:05',
        title: 'Sweep Frekuensi 30-60Hz',
        freq: '45 Hz',
        duration: '9.1s',
        status: 'success',
        notes: 'Resonansi optimal di rentang 44-46 Hz.',
      },
      {
        id: 'jun-2',
        date: '14 Jun',
        time: '11:42',
        title: 'Kalibrasi Sudut Servo',
        freq: '50 Hz',
        duration: '12.0s',
        status: 'failed',
        notes: 'Deviasi nozzle menyebabkan api belum padam.',
      },
      {
        id: 'jun-1',
        date: '08 Jun',
        time: '10:15',
        title: 'Uji Kolimator Akustik',
        freq: '40 Hz',
        duration: '10.2s',
        status: 'success',
        notes: 'Kolimator berhasil memfokuskan rambatan suara.',
      },
    ],
  },
  {
    id: 'juli',
    name: 'Juli',
    year: '2026',
    totalTests: 8,
    successRate: '87.5%',
    avgDuration: '7.6s',
    records: [
      {
        id: 'jul-4',
        date: '29 Jul',
        time: '15:10',
        title: 'Pemadaman Otomatis Tahap II',
        freq: '45 Hz',
        duration: '6.9s',
        status: 'success',
        notes: 'Penguncian servo presisi pada koordinat api.',
      },
      {
        id: 'jul-3',
        date: '22 Jul',
        time: '13:45',
        title: 'Variasi Amplitudo',
        freq: '45 Hz',
        duration: '7.2s',
        status: 'success',
        notes: 'Amplitudo 85% memberi pemadaman tercepat.',
      },
      {
        id: 'jul-2',
        date: '15 Jul',
        time: '16:20',
        title: 'Uji Turbulensi Angin',
        freq: '42 Hz',
        duration: '11.5s',
        status: 'failed',
        notes: 'Hembusan angin luar mengganggu stabilitas gelombang.',
      },
      {
        id: 'jul-1',
        date: '08 Jul',
        time: '10:30',
        title: 'Integrasi YOLO & Akustik',
        freq: '45 Hz',
        duration: '7.8s',
        status: 'success',
        notes: 'Pulse otomatis terpicu saat bounding box terdeteksi.',
      },
    ],
  },
  {
    id: 'agustus',
    name: 'Agustus',
    year: '2026',
    totalTests: 12,
    successRate: '100%',
    avgDuration: '6.2s',
    records: [
      {
        id: 'agu-4',
        date: '30 Agu',
        time: '16:45',
        title: 'Validasi Akhir Pemadaman Cepat',
        freq: '45 Hz',
        duration: '5.4s',
        status: 'success',
        notes: 'Pemadaman stabil, respon kolimator presisi dalam 5.4 detik.',
      },
      {
        id: 'agu-3',
        date: '28 Agu',
        time: '15:32',
        title: 'Pengujian Lapangan Beruntun',
        freq: '45 Hz',
        duration: '5.8s',
        status: 'success',
        notes: 'Deteksi akurat, 5 titik api berturut-turut padam sempurna.',
      },
      {
        id: 'agu-2',
        date: '26 Agu',
        time: '14:10',
        title: 'Validasi Tracking Kamera Real-Time',
        freq: '45 Hz',
        duration: '6.1s',
        status: 'success',
        notes: 'Latensi tracking di bawah 50ms, servo responsif.',
      },
      {
        id: 'agu-1',
        date: '25 Agu',
        time: '11:20',
        title: 'Uji Daya Tahan & Stabilitas Termal',
        freq: '45 Hz',
        duration: '6.5s',
        status: 'success',
        notes: 'Suhu aman 42.4°C, konsumsi RAM stabil 48%.',
      },
    ],
  },
  {
    id: 'september',
    name: 'September',
    year: '2026',
    totalTests: 6,
    successRate: '100%',
    avgDuration: '5.4s',
    records: [
      {
        id: 'sep-3',
        date: '18 Sep',
        time: '15:40',
        title: 'Demonstrasi Monitoring Web',
        freq: '45 Hz',
        duration: '5.2s',
        status: 'success',
        notes: 'Sinkronisasi telemetri dashboard responsif.',
      },
      {
        id: 'sep-2',
        date: '10 Sep',
        time: '13:12',
        title: 'Efisiensi Daya Gelombang',
        freq: '45 Hz',
        duration: '5.4s',
        status: 'success',
        notes: 'Daya stabil dengan hasil pemadaman optimal.',
      },
      {
        id: 'sep-1',
        date: '04 Sep',
        time: '10:00',
        title: 'Uji Stabilitas Termal',
        freq: '45 Hz',
        duration: '5.6s',
        status: 'success',
        notes: 'Suhu Raspberry Pi & amplifier aman di 42°C.',
      },
    ],
  },
];

interface RiwayatSectionProps {
  temperature: number;
  activityLogsCount: number;
}

export function RiwayatSection({
  temperature,
  activityLogsCount,
}: RiwayatSectionProps) {
  const [activeModalMonthId, setActiveModalMonthId] = useState<string | null>(null);

  const cpuTemp = temperature > 0 ? temperature : 42.4;
  const ping = 12;
  const totalFires = Math.max(activityLogsCount + 28, 30);
  const activeModalData = MONTHLY_RECORDS.find((m) => m.id === activeModalMonthId);

  return (
    <div className="flex flex-col gap-3 pb-8">
      {/* 1. HARDWARE HEALTH & TELEMETRY */}
      <Card className="p-3.5 flex flex-col gap-3">
        <div className="flex flex-row items-center justify-between border-b border-border/40 pb-2">
          <div className="flex flex-row items-center gap-2">
            <Cpu className="h-4 w-4 text-danger-soft" />
            <span className="font-mono text-[12px] font-black tracking-wider text-foreground">
              HARDWARE TELEMETRY
            </span>
          </div>
          <StatusPill label="ONLINE" tone="active" isPulsing={true} />
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          {/* Suhu CPU */}
          <div className="flex flex-col justify-center rounded-lg border border-border/40 bg-surface-low/30 p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              CPU Temp
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-foreground">
                {cpuTemp.toFixed(1)}
              </span>
              <span className="font-mono text-[12px] font-bold text-muted">°C</span>
            </div>
          </div>

          {/* Ping Latency */}
          <div className="flex flex-col justify-center rounded-lg border border-border/40 bg-surface-low/30 p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              Latency
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-foreground">
                {ping}
              </span>
              <span className="font-mono text-[12px] font-bold text-muted">ms</span>
            </div>
          </div>

          {/* RAM Usage */}
          <div className="flex flex-col justify-center rounded-lg border border-border/40 bg-surface-low/30 p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              RAM (1GB)
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-success">
                48%
              </span>
              <span className="font-mono text-[10px] font-bold text-muted">480MB</span>
            </div>
          </div>

          {/* Storage Free */}
          <div className="flex flex-col justify-center rounded-lg border border-border/40 bg-surface-low/30 p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              Storage Free
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-foreground">
                14.2
              </span>
              <span className="font-mono text-[12px] font-bold text-muted">GB</span>
            </div>
          </div>
        </div>
      </Card>

      {/* 2. ACOUSTIC PERFORMANCE METRICS */}
      <Card className="p-3.5 flex flex-col gap-3">
        <div className="flex flex-row items-center justify-between border-b border-border/40 pb-2">
          <div className="flex flex-row items-center gap-2">
            <Flame className="h-4 w-4 text-danger-soft" />
            <span className="font-mono text-[12px] font-black tracking-wider text-foreground">
              PERFORMANCE METRICS
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div className="flex flex-col justify-center border border-border/40 bg-surface-low/30 rounded-lg p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              Api Padam
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-danger-soft">{totalFires}</span>
              <span className="font-mono text-[11px] font-bold text-muted">titik</span>
            </div>
          </div>

          <div className="flex flex-col justify-center border border-border/40 bg-surface-low/30 rounded-lg p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              Avg. Waktu
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-foreground">6.8</span>
              <span className="font-mono text-[11px] font-bold text-muted">detik</span>
            </div>
          </div>

          <div className="flex flex-col justify-center border border-border/40 bg-surface-low/30 rounded-lg p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              Best Tone
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-success">45</span>
              <span className="font-mono text-[11px] font-bold text-muted">Hz</span>
            </div>
          </div>

          <div className="flex flex-col justify-center border border-border/40 bg-surface-low/30 rounded-lg p-2.5">
            <span className="font-mono text-[10px] font-bold text-muted uppercase tracking-wider">
              Success Rate
            </span>
            <div className="flex flex-row items-baseline gap-1 mt-0.5">
              <span className="font-mono text-[22px] font-black text-success">96.7%</span>
            </div>
          </div>
        </div>
      </Card>

      {/* 3. MONTHLY LOGS SECTION (Juni, Juli, Agustus, September) */}
      <div className="flex flex-col gap-2 mt-1">
        <div className="flex flex-row items-center gap-1.5 px-1">
          <Calendar className="h-4 w-4 text-danger-soft" />
          <span className="font-mono text-[12px] font-black tracking-wider text-foreground uppercase">
            Log Riwayat Bulanan
          </span>
        </div>

        {/* 2x2 Month Selection Cards - Minimalist & Punchy */}
        <div className="grid grid-cols-2 gap-2.5">
          {MONTHLY_RECORDS.map((month) => (
            <button
              key={month.id}
              type="button"
              onClick={() => setActiveModalMonthId(month.id)}
              className="flex flex-col text-left p-3 rounded-xl border border-border/50 bg-surface hover:border-danger-soft hover:bg-surface-high transition-all active:scale-[0.97] cursor-pointer shadow-md"
            >
              <div className="flex flex-row items-baseline justify-between w-full">
                <span className="font-mono text-[17px] font-black text-foreground">
                  {month.name}
                </span>
                <span className="font-mono text-[11px] font-bold text-muted">{month.year}</span>
              </div>

              <div className="flex flex-row items-center justify-between w-full font-mono mt-2 pt-2 border-t border-border/20">
                <span className="text-[12px] font-bold text-muted">{month.totalTests} Tes</span>
                <span className="text-[14px] font-black text-success">{month.successRate}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 4. OVERLAY MODAL DETAIL LOG BULANAN */}
      {activeModalData && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setActiveModalMonthId(null)}
        >
          <div
            className="relative flex w-full max-w-md max-h-[80vh] flex-col rounded-2xl border border-border bg-[#141414] p-4 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex flex-row items-center justify-between border-b border-border/50 pb-3">
              <div className="flex flex-row items-baseline gap-2">
                <span className="text-xl font-black text-foreground">
                  {activeModalData.name} {activeModalData.year}
                </span>
                <span className="font-mono text-[12px] font-black text-success bg-success/15 px-2 py-0.5 rounded-full border border-success/30">
                  {activeModalData.successRate}
                </span>
              </div>

              <button
                type="button"
                onClick={() => setActiveModalMonthId(null)}
                aria-label="Tutup"
                className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface-high text-muted hover:text-foreground transition-all cursor-pointer shrink-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Scrollable Records List */}
            <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto py-3 pr-0.5">
              {activeModalData.records.map((record) => (
                <div
                  key={record.id}
                  className="flex flex-col rounded-xl border border-border/30 bg-surface-low/40 p-3 gap-1.5"
                >
                  <div className="flex flex-row items-center justify-between">
                    <div className="flex flex-row items-center gap-1.5">
                      {record.status === 'success' ? (
                        <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-danger-soft shrink-0" />
                      )}
                      <span className="font-mono text-[13px] font-black text-foreground">
                        {record.title}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-muted shrink-0">
                      {record.date} {record.time}
                    </span>
                  </div>

                  <div className="flex flex-row items-center gap-3 text-[11px] font-mono">
                    <span className="text-muted">
                      {record.freq} • {record.duration}
                    </span>
                    <span
                      className={`font-black ml-auto text-[10px] px-1.5 py-0.5 rounded ${
                        record.status === 'success'
                          ? 'bg-success/10 text-success'
                          : 'bg-danger/10 text-danger-soft'
                      }`}
                    >
                      {record.status === 'success' ? 'PADAM' : 'EVALUASI'}
                    </span>
                  </div>

                  <p className="font-mono text-[10px] text-muted border-t border-border/20 pt-1 leading-snug">
                    {record.notes}
                  </p>
                </div>
              ))}
            </div>

            {/* Modal Bottom Action */}
            <div className="border-t border-border/50 pt-3">
              <button
                type="button"
                onClick={() => setActiveModalMonthId(null)}
                className="w-full py-2.5 rounded-xl bg-surface-high border border-border font-mono text-[12px] font-bold text-foreground hover:border-danger-soft transition-colors cursor-pointer"
              >
                TUTUP
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



