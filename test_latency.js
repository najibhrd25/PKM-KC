// Run: node --test test_latency.js. Network is simulated; no Pi is controlled.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const control = html.split('// ================= LOW-LATENCY CONTROL CHANNEL =================')[1]
  .split('// ================= CLIENT-SIDE ROUTER')[0];

function controls(fetch) {
  class Socket {
    static OPEN = 1;
    static CONNECTING = 0;
    constructor() { this.readyState = 1; this.bufferedAmount = 0; this.sent = []; }
    send(value) { this.sent.push(JSON.parse(value)); }
    close() { this.readyState = 3; this.onclose?.(); }
  }
  const context = vm.createContext({
    URL, AbortController, WebSocket: Socket, fetch,
    performance, Date, setTimeout, clearTimeout,
    window: { location: { origin: 'https://demo.test' } },
    document: { visibilityState: 'visible' },
  });
  vm.runInContext('const BASE_URL = ""; let currentTab = "manual";' + control, context);
  return { context, run: code => vm.runInContext(code, context) };
}

test('slow WebSocket keeps one unacknowledged command instead of 10 queued commands', () => {
  const { run } = controls(() => assert.fail('HTTP should not be used'));
  run('for (let i = 0; i < 10; i++) sendJogCommand(i, 0)');
  assert.equal(run('controlSocket.sent.length'), 1);
  run('controlSocket.onmessage({data: JSON.stringify({type: "ack"})}); sendJogCommand(9, 0)');
  assert.equal(run('controlSocket.sent.length'), 2);
  assert.equal(run('controlSocket.sent[1].d_yaw'), 9);
});

test('HTTP fallback keeps one request active and sends only the newest pending value', async () => {
  const pending = [];
  const calls = [];
  const { run } = controls((url, options) => {
    calls.push(JSON.parse(options.body));
    return new Promise(resolve => pending.push(resolve));
  });
  run('ensureControlSocket(); controlSocket.readyState = WebSocket.CONNECTING');
  run('for (let i = 0; i < 10; i++) sendJogCommand(i, 0)');
  assert.equal(calls.length, 1);
  pending.shift()({ ok: true });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.length, 2);
  assert.equal(calls[1].d_yaw, 9);
  pending.shift()({ ok: true });
  await new Promise(resolve => setImmediate(resolve));
});

test('joystick does not send motion while the PWA is hidden', () => {
  const { context, run } = controls(() => assert.fail('No request expected'));
  context.document.visibilityState = 'hidden';
  run('sendJogCommand(3, 0)');
  assert.equal(run('controlSocket'), null);
});

test('remote camera waits for each frame and cancels requests when hidden', async () => {
  const stream = html.split('    let streamTimer = null;')[1]
    .split('    window.addEventListener("DOMContentLoaded", initStreamFeeds);')[0];
  const requests = [];
  const timers = new Map();
  let nextTimer = 0;
  const image = { src: '', removeAttribute() { this.src = ''; } };
  const context = vm.createContext({
    AbortController, performance, Date, console,
    URL: { createObjectURL: () => 'blob:latest', revokeObjectURL() {} },
    document: { visibilityState: 'visible', getElementById: () => image },
    fetch(url, options) {
      return new Promise(resolve => requests.push({ resolve, signal: options.signal }));
    },
    setTimeout(callback) { const id = ++nextTimer; timers.set(id, callback); return id; },
    clearTimeout(id) { timers.delete(id); },
  });
  vm.runInContext('const BASE_URL="https://demo.test", isLocal=false; let currentTab="auto";'
    + 'let streamTimer=null;' + stream + ';updateActiveStreamFeed()', context);
  assert.equal(requests.length, 1);
  // No timer schedules another frame while this slow request is still in flight.
  assert.equal(timers.size, 1); // request timeout only
  requests[0].resolve({ ok: true, blob: async () => ({}) });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(image.src, 'blob:latest');
  assert.equal(timers.size, 1); // next-frame timer only
  [...timers.values()][0]();
  assert.equal(requests.length, 2);
  context.document.visibilityState = 'hidden';
  vm.runInContext('updateActiveStreamFeed()', context);
  assert.equal(requests[1].signal.aborted, true);
  requests[1].resolve({ ok: true, blob: async () => ({}) });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(image.src, ''); // late frame must not restart a hidden stream
});
