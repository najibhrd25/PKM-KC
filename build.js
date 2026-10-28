const fs = require('fs');
const path = require('path');

const outDir = path.join(__dirname, 'public');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Semua route memakai aplikasi yang sama. Satu sumber mencegah perbaikan
// kontrol/kamera tertinggal di salinan manual, auto, atau analisis.
for (const route of ['auto', 'manual', 'analisis']) {
  const routeDir = path.join(__dirname, route);
  fs.mkdirSync(routeDir, { recursive: true });
  fs.copyFileSync(path.join(__dirname, 'index.html'), path.join(routeDir, 'index.html'));
}

const items = [
  'index.html',
  'favicon.svg',
  'safe-logo.svg',
  'manifest.json',
  'sw.js',
  'assets',
  'auto',
  'manual',
  'analisis'
];

for (const item of items) {
  const src = path.join(__dirname, item);
  const dest = path.join(outDir, item);
  if (fs.existsSync(src)) {
    fs.cpSync(src, dest, { recursive: true, force: true });
  }
}

console.log('Build completed: all static pages and assets copied to public/');
