'use strict';

// ── storage ───────────────────────────────────────────────────────────────
const storage = (() => {
  const KEY = 'pomodoro.v1';

  function todayLocal() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function defaults() {
    return {
      priority: '',
      trees: { date: todayLocal(), count: 0 },
    };
  }

  function load() {
    let raw;
    try { raw = localStorage.getItem(KEY); }
    catch { return defaults(); }
    if (!raw) return defaults();
    let parsed;
    try { parsed = JSON.parse(raw); }
    catch { return defaults(); }

    const out = defaults();
    if (parsed && typeof parsed.priority === 'string') {
      out.priority = parsed.priority;
    }
    if (parsed && parsed.trees && typeof parsed.trees.date === 'string'
        && typeof parsed.trees.count === 'number'
        && Number.isFinite(parsed.trees.count)
        && parsed.trees.count >= 0) {
      out.trees = { date: parsed.trees.date, count: Math.floor(parsed.trees.count) };
    }
    if (out.trees.date !== todayLocal()) {
      out.trees = { date: todayLocal(), count: 0 };
    }
    return out;
  }

  function save(state) {
    try { localStorage.setItem(KEY, JSON.stringify(state)); }
    catch { /* localStorage disabled — silently no-op */ }
  }

  function setPriority(state, priority) {
    state.priority = priority;
    save(state);
  }

  function incrementTrees(state) {
    if (state.trees.date !== todayLocal()) {
      state.trees = { date: todayLocal(), count: 0 };
    }
    state.trees.count += 1;
    save(state);
  }

  return { load, save, setPriority, incrementTrees, todayLocal };
})();

// ── timer ─────────────────────────────────────────────────────────────────
const timer = (() => {
  let endsAt = null;
  let remainingMs = 0;
  let intervalId = null;
  let onTick = () => {};
  let onComplete = () => {};
  let mode = 'idle';

  const TICK_MS = 250;

  function clearInterval_() {
    if (intervalId !== null) { clearInterval(intervalId); intervalId = null; }
  }

  function start(durationMs) {
    clearInterval_();
    endsAt = Date.now() + durationMs;
    remainingMs = 0;
    mode = 'running';
    intervalId = setInterval(tick, TICK_MS);
    onTick(remainingNow());
  }

  function pause() {
    if (mode !== 'running') return;
    remainingMs = Math.max(0, endsAt - Date.now());
    endsAt = null;
    clearInterval_();
    mode = 'paused';
  }

  function resume() {
    if (mode !== 'paused') return;
    endsAt = Date.now() + remainingMs;
    remainingMs = 0;
    mode = 'running';
    intervalId = setInterval(tick, TICK_MS);
    onTick(remainingNow());
  }

  function cancel() {
    clearInterval_();
    endsAt = null;
    remainingMs = 0;
    mode = 'idle';
  }

  function remainingNow() {
    if (mode === 'running') return Math.max(0, endsAt - Date.now());
    if (mode === 'paused')  return remainingMs;
    return 0;
  }

  function tick() {
    const r = remainingNow();
    onTick(r);
    if (r <= 0) {
      clearInterval_();
      endsAt = null;
      mode = 'idle';
      onComplete();
    }
  }

  function setHandlers({ onTick: t, onComplete: c }) {
    onTick = t || onTick;
    onComplete = c || onComplete;
  }

  function getMode() { return mode; }

  function format(ms) {
    const total = Math.ceil(ms / 1000);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  return { start, pause, resume, cancel, remainingNow, setHandlers, getMode, format };
})();

// ── notify ────────────────────────────────────────────────────────────────
const notify = (() => {
  let audioCtx = null;
  let permissionAsked = false;

  function ensureAudio() {
    if (audioCtx) return audioCtx;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioCtx = new Ctx();
    return audioCtx;
  }

  // Two-note bell: a brief E5 + B5 with an exponential-decay envelope.
  function chime() {
    const ctx = ensureAudio();
    if (!ctx) return;
    if (ctx.state === 'suspended') ctx.resume();

    const now = ctx.currentTime;
    const master = ctx.createGain();
    master.gain.value = 0.18;
    master.connect(ctx.destination);

    [659.25, 987.77].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      osc.connect(gain);
      gain.connect(master);

      const start = now + i * 0.15;
      const end = start + 0.9;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(1.0, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, end);
      osc.start(start);
      osc.stop(end + 0.05);
    });
  }

  async function ensurePermission() {
    if (permissionAsked) return;
    permissionAsked = true;
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') {
      try { await Notification.requestPermission(); } catch { /* ignore */ }
    }
  }

  function send(title, body) {
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    try {
      new Notification(title, { body, icon: '/favicon.svg', silent: true });
    } catch { /* ignore */ }
  }

  return { chime, ensurePermission, send };
})();

// ── scene ─────────────────────────────────────────────────────────────────
const scene = (() => {
  const MAX_DRAWN_TREES = 12;

  function prng(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function seedFromDate(dateStr) {
    let h = 2166136261;
    for (let i = 0; i < dateStr.length; i++) {
      h ^= dateStr.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function treePositions(count, seed) {
    const drawn = Math.min(count, MAX_DRAWN_TREES);
    if (drawn === 0) return [];
    const rand = prng(seed);
    const slotW = 1200 / MAX_DRAWN_TREES;
    const positions = [];
    for (let i = 0; i < drawn; i++) {
      const slotCenter = slotW * (i + 0.5);
      const jitterX = (rand() - 0.5) * slotW * 0.6;
      const jitterY = (rand() - 0.5) * 14;
      const scale = 0.85 + rand() * 0.35;
      positions.push({
        x: slotCenter + jitterX,
        y: 268 + jitterY,
        scale,
      });
    }
    return positions;
  }

  function renderTrees(count, dateStr) {
    const trees = document.getElementById('trees');
    trees.innerHTML = '';
    const positions = treePositions(count, seedFromDate(dateStr));
    const baseW = 60, baseH = 100;
    for (const p of positions) {
      const w = baseW * p.scale;
      const h = baseH * p.scale;
      const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      use.setAttribute('href', '#tree');
      use.setAttribute('x', String(p.x - w / 2));
      use.setAttribute('y', String(p.y - h));
      use.setAttribute('width', String(w));
      use.setAttribute('height', String(h));
      trees.appendChild(use);
    }
  }

  function setState(state) {
    document.querySelector('.stage').dataset.state = state;
  }

  function pulse(kind) {
    const sky = document.getElementById('sky');
    sky.classList.remove('pulse-sage', 'pulse-peach');
    void sky.getBoundingClientRect();
    sky.classList.add(kind === 'peach' ? 'pulse-peach' : 'pulse-sage');
  }

  return { renderTrees, setState, pulse, treePositions, seedFromDate, MAX_DRAWN_TREES };
})();

// ── controller ────────────────────────────────────────────────────────────
(() => {
  const FOCUS_MS = 25 * 60 * 1000;
  const BREAK_MS = 5 * 60 * 1000;

  const state = storage.load();
  let machine = 'idle';
  let lastDisplay = '';

  const $priority = document.getElementById('priority');
  const $timer    = document.getElementById('timer');
  const $start    = document.getElementById('btn-start');
  const $pause    = document.getElementById('btn-pause');
  const $resume   = document.getElementById('btn-resume');
  const $cancel   = document.getElementById('btn-cancel');
  const $break    = document.getElementById('btn-start-break');
  const $next     = document.getElementById('btn-start-next');

  function refreshStartEnabled() {
    $start.disabled = $priority.value.trim().length === 0;
  }

  function setTimerDisplay(ms) {
    const text = timer.format(ms);
    $timer.textContent = text;
    if (machine === 'focus' || machine === 'break') {
      const t = `${text} · ${state.priority || 'Pomodoro'} — Pomodoro`;
      if (t !== lastDisplay) { document.title = t; lastDisplay = t; }
    } else {
      if (lastDisplay !== '') { document.title = 'Pomodoro'; lastDisplay = ''; }
    }
  }

  function showButtonsFor(m) {
    $start.hidden  = !(m === 'idle');
    $pause.hidden  = !(m === 'focus' || m === 'break');
    $resume.hidden = !(m === 'paused-focus' || m === 'paused-break');
    $cancel.hidden = !(m === 'focus' || m === 'break' || m === 'paused-focus' || m === 'paused-break');
    $break.hidden  = !(m === 'focus_done');
    $next.hidden   = !(m === 'break_done');
  }

  function setMachine(m) {
    machine = m;
    scene.setState(m);
    showButtonsFor(m);
    $priority.disabled = (m !== 'idle');
  }

  // ── Init ────────────────────────────────────────────────────────────────
  $priority.value = state.priority;
  refreshStartEnabled();
  scene.renderTrees(state.trees.count, state.trees.date);
  setMachine('idle');
  setTimerDisplay(FOCUS_MS);

  timer.setHandlers({
    onTick: (ms) => setTimerDisplay(ms),
    onComplete: () => {
      if (machine === 'focus') {
        storage.incrementTrees(state);
        scene.renderTrees(state.trees.count, state.trees.date);
        scene.pulse('sage');
        notify.chime();
        notify.send('Focus complete', 'Time for a 5-min break.');
        setMachine('focus_done');
        setTimerDisplay(BREAK_MS);
      } else if (machine === 'break') {
        scene.pulse('peach');
        notify.chime();
        notify.send('Break over', 'Ready for the next focus session?');
        setMachine('break_done');
        setTimerDisplay(FOCUS_MS);
      }
    },
  });

  let saveTimeoutId = null;
  $priority.addEventListener('input', () => {
    refreshStartEnabled();
    if (saveTimeoutId) clearTimeout(saveTimeoutId);
    saveTimeoutId = setTimeout(() => storage.setPriority(state, $priority.value), 300);
  });

  $start.addEventListener('click', () => {
    state.priority = $priority.value.trim();
    storage.setPriority(state, state.priority);
    notify.ensurePermission();
    setMachine('focus');
    timer.start(FOCUS_MS);
  });

  $pause.addEventListener('click', () => {
    timer.pause();
    setMachine(machine === 'focus' ? 'paused-focus' : 'paused-break');
  });

  $resume.addEventListener('click', () => {
    setMachine(machine === 'paused-focus' ? 'focus' : 'break');
    timer.resume();
  });

  $cancel.addEventListener('click', () => {
    timer.cancel();
    setMachine('idle');
    setTimerDisplay(FOCUS_MS);
  });

  $break.addEventListener('click', () => {
    setMachine('break');
    timer.start(BREAK_MS);
  });

  $next.addEventListener('click', () => {
    setMachine('focus');
    timer.start(FOCUS_MS);
  });

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && (machine === 'focus' || machine === 'break')) {
      const r = timer.remainingNow();
      if (r <= 0) return;
      setTimerDisplay(r);
    }
  });
})();
