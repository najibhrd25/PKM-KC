import type { SystemState } from '@/core/system/types';
import type { ActivityLogItem } from '@/features/mission-control/types';

interface ActivityReportData {
  frequency: number;
  logs: ActivityLogItem[];
  state: SystemState;
  temperature: number;
}

const stateLabels: Record<SystemState, string> = {
  OFF_STATE: 'OFFLINE',
  STARTUP_SEQUENCE: 'INITIALIZING',
  AUTO_MODE: 'AUTO MODE',
  MANUAL_MODE: 'MANUAL MODE',
};

function createReportHtml({
  frequency,
  logs,
  state,
  temperature,
}: ActivityReportData) {
  const generatedAt = new Intl.DateTimeFormat('id-ID', {
    dateStyle: 'full',
    timeStyle: 'medium',
  }).format(new Date());

  const rows = logs
    .map(
      (log) => `
        <tr>
          <td>${log.time}</td>
          <td><strong>${log.title}</strong><br /><span>${log.detail}</span></td>
        </tr>
      `,
    )
    .join('');

  return `
    <!DOCTYPE html>
    <html lang="id">
      <head>
        <meta charset="utf-8" />
        <style>
          @page { margin: 32px; }
          body { color: #241c1b; font-family: Helvetica, Arial, sans-serif; }
          header { border-bottom: 3px solid #b23b2e; margin-bottom: 24px; padding-bottom: 16px; }
          h1 { color: #8f1717; font-size: 26px; margin: 0 0 6px; }
          p { color: #655b59; font-size: 12px; margin: 0; }
          .summary { display: flex; gap: 12px; margin-bottom: 24px; }
          .metric { background: #f4eeee; flex: 1; padding: 12px; }
          .metric span { color: #786e6c; display: block; font-size: 10px; letter-spacing: 1px; }
          .metric strong { display: block; font-size: 18px; margin-top: 5px; }
          table { border-collapse: collapse; width: 100%; }
          th { background: #2b1d1d; color: white; font-size: 11px; letter-spacing: 1px; padding: 10px; text-align: left; }
          td { border-bottom: 1px solid #ded5d3; font-size: 11px; padding: 12px 10px; vertical-align: top; }
          td:first-child { color: #786e6c; font-family: monospace; width: 90px; }
          td span { color: #655b59; }
          footer { color: #8f8583; font-size: 9px; margin-top: 28px; text-align: center; }
        </style>
      </head>
      <body>
        <header>
          <h1>S.A.F.E. ACTIVITY REPORT</h1>
          <p>Dibuat pada ${generatedAt}</p>
        </header>
        <section class="summary">
          <div class="metric"><span>SYSTEM STATUS</span><strong>${stateLabels[state]}</strong></div>
          <div class="metric"><span>TEMPERATURE</span><strong>${temperature || '--'} C</strong></div>
          <div class="metric"><span>ACOUSTIC TARGET</span><strong>${frequency || '--'} Hz</strong></div>
        </section>
        <table>
          <thead><tr><th>WAKTU</th><th>KEJADIAN</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <footer>S.A.F.E. Mission Control - generated report</footer>
      </body>
    </html>
  `;
}

export async function shareActivityReport(data: ActivityReportData) {
  const html = createReportHtml(data);

  // Open a new window and use the browser's native print dialog (supports Save as PDF)
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    throw new Error('Pop-up blocked. Please allow pop-ups and try again.');
  }

  printWindow.document.write(html);
  printWindow.document.close();

  // Wait for content to render before printing
  printWindow.onload = () => {
    printWindow.print();
  };

  // Fallback if onload doesn't fire (some browsers)
  setTimeout(() => {
    printWindow.print();
  }, 500);
}
