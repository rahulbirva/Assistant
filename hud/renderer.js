/**
 * JARVIS HUD — Renderer process (Phase 6)
 * WebSocket client connecting to Python hud_server.py on ws://localhost:7789
 * Handles all real-time UI updates: state, conversation, stats, mic level.
 */

'use strict';

/* ── Config ──────────────────────────────────────────────────── */
const WS_URL         = 'ws://localhost:7789';
const RECONNECT_MS   = 3000;
const MIC_BAR_COUNT  = 14;
const MAX_MESSAGES   = 60;   // prune conversation after this many

/* ── State color map (matches CSS variables) ─────────────────── */
const STATE = {
  IDLE:      { color: '#3c4558', label: 'IDLE' },
  LISTENING: { color: '#2060a0', label: 'LISTENING' },
  THINKING:  { color: '#8a6c1a', label: 'THINKING' },
  SPEAKING:  { color: '#1e7a50', label: 'SPEAKING' },
  LOCKED:    { color: '#8a2828', label: 'LOCKED' },
  SEEING:    { color: '#1e6a6a', label: 'VISION SCAN' },
  PAUSED:    { color: '#4a3868', label: 'PAUSED' },
};

/* ── DOM refs ────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const els = {
  indicator: $('state-indicator'),
  stateMode: $('state-mode'),
  dotOcr:    $('dot-ocr'),   valOcr:   $('val-ocr'),
  dotGate:   $('dot-gate'),  valGate:  $('val-gate'),
  dotWs:     $('dot-ws'),    valWs:    $('val-ws'),
  valModel:  $('val-model'),
  heardText: $('heard-text'),
  convo:     $('conversation'),
  emptyMsg:  $('empty-state'),
  statCpu:   $('stat-cpu'),
  statRam:   $('stat-ram'),
  statGpu:   $('stat-gpu'),
  statTime:  $('stat-time'),
};

const micBars = Array.from({ length: MIC_BAR_COUNT }, (_, i) => $(`mbar-${i}`));

/* ── Time clock ──────────────────────────────────────────────── */
function tick() {
  els.statTime.textContent = new Date().toTimeString().slice(0, 8);
}
setInterval(tick, 1000);
tick();

/* ── Mic bar visualiser ──────────────────────────────────────── */
let micRaf      = null;
let micActive   = false;

function renderMicBars(level) {
  // level 0-100
  const COLORS = { active: '#2060a0', idle: '#3c4558' };
  micBars.forEach((bar, i) => {
    const threshold = (i / MIC_BAR_COUNT) * 100;
    if (level > threshold) {
      const h = 2 + ((level - threshold) / 100) * 14;
      bar.style.height = `${Math.round(h)}px`;
      bar.style.background = micActive ? COLORS.active : COLORS.idle;
    } else {
      bar.style.height = '2px';
      bar.style.background = COLORS.idle;
    }
  });
}

function startMicAnim() {
  micActive = true;
  function frame() {
    renderMicBars(Math.random() * 75 + 15);
    micRaf = requestAnimationFrame(frame);
  }
  frame();
}

function stopMicAnim() {
  micActive = false;
  cancelAnimationFrame(micRaf);
  renderMicBars(0);
}

/* ── State display ───────────────────────────────────────────── */
let currentStatus = 'IDLE';

function applyStatus(status) {
  const s = STATE[status] || STATE.IDLE;
  currentStatus = status;
  els.indicator.style.background = s.color;
  els.stateMode.textContent = `/ ${s.label}`;

  if (status === 'LISTENING') startMicAnim();
  else                        stopMicAnim();
}

/* ── Conversation ────────────────────────────────────────────── */
let msgCount = 0;

function formatTime(ts) {
  return ts ? new Date(ts).toTimeString().slice(0, 8) : new Date().toTimeString().slice(0, 8);
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function addMsg(role, text, ts) {
  if (els.emptyMsg) els.emptyMsg.style.display = 'none';

  // Prune old messages
  if (msgCount >= MAX_MESSAGES) {
    const first = els.convo.querySelector('.msg-block');
    if (first) els.convo.removeChild(first);
    msgCount--;
  }

  const isYou = (role === 'user');
  const block = document.createElement('div');
  block.className = 'msg-block';
  block.innerHTML =
    `<div class="msg-header">` +
      `<span class="msg-role ${isYou ? 'you' : 'jarvis'}">${isYou ? 'YOU' : 'JARVIS'}</span>` +
      `<span class="msg-ts">${formatTime(ts)}</span>` +
    `</div>` +
    `<div class="msg-text">${esc(text)}</div>`;

  els.convo.appendChild(block);
  msgCount++;
  els.convo.scrollTop = els.convo.scrollHeight;
}

/* ── Stats ───────────────────────────────────────────────────── */
function applyStats(d) {
  if (d.cpu !== undefined) els.statCpu.textContent = `${Math.round(d.cpu)}%`;
  if (d.ram !== undefined) els.statRam.textContent = `${Math.round(d.ram)}%`;
  if (d.gpu !== undefined) {
    els.statGpu.textContent = d.gpu > 0 ? `${Math.round(d.gpu)}%` : 'N/A';
  }
}

/* ── Status strip helpers ────────────────────────────────────── */
const GOOD = '#1e7a50';
const BAD  = '#8a2828';
const DIM  = '#3c4558';

function setOcr(active) {
  els.dotOcr.style.background = active ? '#1e6a6a' : DIM;
  els.valOcr.textContent = active ? 'ON' : 'OFF';
}

function setGate(locked) {
  els.dotGate.style.background = locked ? BAD : GOOD;
  els.valGate.textContent = locked ? 'LOCKED' : 'OPEN';
}

function setWs(ok) {
  els.dotWs.style.background = ok ? GOOD : BAD;
  els.valWs.textContent = ok ? 'OK' : 'DOWN';
}

/* ── Message dispatcher ──────────────────────────────────────── */
function handleMsg(msg) {
  switch (msg.type) {
    case 'state': {
      const d = msg.data || {};
      applyStatus(d.status || 'IDLE');
      if (d.message)      els.heardText.textContent = d.message;
      if (d.model)        els.valModel.textContent  = d.model.slice(0, 12);
      if (d.screen_active !== undefined) setOcr(d.screen_active);
      if (d.face_gate     !== undefined) setGate(d.face_gate);
      if (d.conversation)  d.conversation.forEach(c => addMsg(c.role, c.text, c.timestamp));
      applyStats(d);
      break;
    }
    case 'status_update': {
      const d = msg.data || {};
      applyStatus(d.status || 'IDLE');
      if (d.message) els.heardText.textContent = d.message;
      break;
    }
    case 'conversation':
      addMsg(msg.data.role, msg.data.text, msg.data.timestamp);
      break;
    case 'stats':
      applyStats(msg.data);
      break;
    case 'ocr_update':
      setOcr(msg.data.active);
      break;
    case 'gate_update':
      setGate(msg.data.locked);
      break;
    case 'model_info':
      els.valModel.textContent = (msg.data.name || '--').slice(0, 12);
      break;
    default:
      break;
  }
}

/* ── WebSocket client ────────────────────────────────────────── */
let ws           = null;
let reconnectTid = null;

function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  setWs(false);

  try {
    ws = new WebSocket(WS_URL);
  } catch (_) {
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    setWs(true);
    if (reconnectTid) { clearTimeout(reconnectTid); reconnectTid = null; }
  };

  ws.onmessage = e => {
    try { handleMsg(JSON.parse(e.data)); }
    catch (_) { /* ignore malformed */ }
  };

  ws.onerror = () => {
    setWs(false);
  };

  ws.onclose = () => {
    setWs(false);
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  if (reconnectTid) return;
  reconnectTid = setTimeout(() => { reconnectTid = null; connect(); }, RECONNECT_MS);
}

/* ── IPC button wiring ───────────────────────────────────────── */
document.getElementById('btn-minimize').addEventListener('click', () => {
  window.electron?.minimizeHud();
});
document.getElementById('btn-close').addEventListener('click', () => {
  window.electron?.closeHud();
});

/* ── Boot ────────────────────────────────────────────────────── */
applyStatus('IDLE');
connect();
