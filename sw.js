// S.A.F.E. Mission Control — Minimal Service Worker for PWA installation
const CACHE_NAME = 'safe-cache-v1';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(clients.claim());
});

self.addEventListener('fetch', (e) => {
  // Let network handle all real-time stream/API calls
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
