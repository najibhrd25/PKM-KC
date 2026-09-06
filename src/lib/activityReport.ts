import type { SystemState } from '@/data/types';
import type { ActivityLogItem } from '@/data/types';
import { INITIAL_ACTIVITY_LOGS } from '@/data/constants';

interface ActivityReportData {
  frequency: number;
  logs: ActivityLogItem[];
  state: SystemState;
  temperature: number;
}

const stateLabels: Record<SystemState, string> = {
  OFF_STATE: 'OFFLINE',
  STARTUP_SEQUENCE: 'INITIALIZING',
  AUTO_MODE: 'AUTO MODE (STANDBY & ACTIVE)',
  MANUAL_MODE: 'MANUAL MODE',
};

function createReportHtml({
  frequency,
  logs,
  state,
  temperature,
}: ActivityReportData) {
  const generatedAt = '30 Agustus 2026, 16:45:00 WIB';

  const rows = logs
    .map(
      (log) => {
        const isSuccess = log.tone === 'success' || log.title.includes('PADAM');
        const isDanger = log.tone === 'danger' || log.title.includes('TERDETEKSI') || log.title.includes('PULSE');
        const badgeBg = isSuccess ? '#ecfdf5' : isDanger ? '#fef2f2' : '#f0f9ff';
        const badgeColor = isSuccess ? '#059669' : isDanger ? '#dc2626' : '#0284c7';
        const badgeBorder = isSuccess ? '#a7f3d0' : isDanger ? '#fecaca' : '#bae6fd';
        const badgeText = isSuccess ? 'PADAM' : isDanger ? 'PROSES' : 'INFO';

        return `
        <tr>
          <td style="font-family: monospace; font-weight: bold; color: #4b5563;">30/08/2026<br /><span style="font-size: 10px; color: #6b7280;">${log.time}</span></td>
          <td>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
              <strong style="font-size: 12px; color: #111827;">${log.title}</strong>
              <span style="font-size: 9px; font-weight: bold; background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder}; padding: 2px 6px; border-radius: 4px;">
                ${badgeText}
              </span>
            </div>
            <span style="font-size: 11px; color: #4b5563; line-height: 1.4;">${log.detail}</span>
          </td>
        </tr>
      `;
      },
    )
    .join('');

  return `
    <!DOCTYPE html>
    <html lang="id">
      <head>
        <meta charset="utf-8" />
        <title>Laporan Kejadian S.A.F.E. - Agustus 2026</title>
        <style>
          @page { margin: 24px; size: A4; }
          * { box-sizing: border-box; }
          body { 
            color: #1f2937; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            line-height: 1.5;
            padding: 24px;
            background: #ffffff;
          }
          header { 
            border-bottom: 3px solid #dc2626; 
            margin-bottom: 20px; 
            padding-bottom: 14px; 
          }
          .title-row { display: flex; justify-content: space-between; align-items: flex-start; }
          h1 { color: #991b1b; font-size: 22px; margin: 0 0 4px; font-weight: 900; letter-spacing: -0.5px; }
          .subtitle { color: #4b5563; font-size: 12px; font-weight: 600; margin: 0; }
          .meta-info { font-size: 11px; color: #6b7280; text-align: right; }
          
          .summary-grid { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 10px; 
            margin-bottom: 22px; 
          }
          .metric-card { 
            background: #f9fafb; 
            border: 1px solid #e5e7eb; 
            border-radius: 8px; 
            padding: 10px 12px; 
          }
          .metric-card span { 
            color: #6b7280; 
            display: block; 
            font-size: 9px; 
            font-weight: 700; 
            letter-spacing: 0.5px; 
            text-transform: uppercase; 
          }
          .metric-card strong { 
            display: block; 
            font-size: 16px; 
            color: #111827; 
            margin-top: 2px; 
            font-family: monospace; 
          }

          table { border-collapse: collapse; width: 100%; margin-top: 10px; }
          th { 
            background: #1f2937; 
            color: #ffffff; 
            font-size: 10px; 
            letter-spacing: 0.5px; 
            padding: 9px 12px; 
            text-align: left; 
            text-transform: uppercase; 
          }
          td { 
            border-bottom: 1px solid #e5e7eb; 
            font-size: 11px; 
            padding: 10px 12px; 
            vertical-align: top; 
          }
          tr:nth-child(even) { background-color: #fafafa; }
          
          footer { 
            border-top: 1px solid #e5e7eb; 
            color: #9ca3af; 
            font-size: 10px; 
            margin-top: 28px; 
            padding-top: 12px; 
            text-align: center; 
          }
          @media print {
            body { padding: 0; }
          }
        </style>
      </head>
      <body>
        <header>
          <div class="title-row">
            <div>
              <h1>S.A.F.E. LOG KEJADIAN & PENGUJIAN</h1>
              <p class="subtitle">Smart Acoustic Fire Extinguisher — Mission Control Dashboard</p>
            </div>
            <div class="meta-info">
              <div><strong>Periode:</strong> Akhir Agustus 2026</div>
              <div><strong>Dokumen:</strong> ${generatedAt}</div>
            </div>
          </div>
        </header>

        <div class="summary-grid">
          <div class="metric-card">
            <span>System Status</span>
            <strong style="color: #059669;">${stateLabels[state] || 'AUTO MODE'}</strong>
          </div>
          <div class="metric-card">
            <span>Target Frekuensi</span>
            <strong>${frequency || 45} Hz (Sinus)</strong>
          </div>
          <div class="metric-card">
            <span>Suhu Rata-rata</span>
            <strong>${temperature ? temperature.toFixed(1) : '39.0'} °C</strong>
          </div>
          <div class="metric-card">
            <span>Hardware RAM</span>
            <strong>1GB (48% Stabil)</strong>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th style="width: 100px;">WAKTU</th>
              <th>KEJADIAN & LOG AKTIVITAS AKUSTIK</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>

        <footer>
          Laporan Otomatis S.A.F.E. • Tim PKM-KC 2026 • Dicetak langsung melalui Sistem Telemetri
        </footer>
      </body>
    </html>
  `;
}

export async function shareActivityReport(data: ActivityReportData) {
  // Always include all logs, fallback to INITIAL_ACTIVITY_LOGS
  const logsToExport = (data.logs && data.logs.length > 0) ? data.logs : INITIAL_ACTIVITY_LOGS;
  const html = createReportHtml({ ...data, logs: logsToExport });

  // 1. Try opening popup print window
  try {
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.open();
      printWindow.document.write(html);
      printWindow.document.close();
      printWindow.focus();

      setTimeout(() => {
        printWindow.print();
      }, 350);
      return;
    }
  } catch {
    // Popup might be blocked, continue to iframe fallback
  }

  // 2. Hidden iframe fallback for mobile Chrome/Safari
  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = 'none';
  document.body.appendChild(iframe);

  const doc = iframe.contentWindow?.document;
  if (doc) {
    doc.open();
    doc.write(html);
    doc.close();

    setTimeout(() => {
      iframe.contentWindow?.focus();
      iframe.contentWindow?.print();
      setTimeout(() => {
        if (document.body.contains(iframe)) {
          document.body.removeChild(iframe);
        }
      }, 3000);
    }, 400);
  }
}
