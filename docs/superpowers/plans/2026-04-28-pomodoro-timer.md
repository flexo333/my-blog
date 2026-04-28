# Pomodoro Timer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page Pomodoro timer at `public/pomodoro/` with a forest scene that grows one tree per completed focus session, a persistent priority input, and three end-of-timer cues (visual pulse, audio chime, browser notification).

**Architecture:** Plain HTML / CSS / vanilla JS in Astro's `public/` directory (passed through verbatim by the build). One `index.html`, one `pomodoro.css`, one `pomodoro.js`. The JS is structured as five module-like sections inside one file: `storage`, `timer`, `scene`, `notify`, `controller`. Persistence via `localStorage`. Audio via Web Audio API (generated tone — no asset file).

**Tech Stack:** HTML5, CSS3 (custom properties, keyframes), vanilla ES modules-style JS (no bundler), Web Audio API, Notification API, localStorage.

**Spec:** `docs/superpowers/specs/2026-04-27-pomodoro-design.md`

---

## Refinements to the spec

**Chime delivery — Web Audio instead of `chime.mp3`.** The spec called for a `chime.mp3` asset. Implementing the chime via the Web Audio API (a short two-note bell built from `OscillatorNode`s with an envelope) is cleaner: no asset to commit, no licensing question, smaller payload. Same UX. **No `chime.mp3` file is created.**

## Test approach

The spec explicitly excludes test infrastructure for v1. No vitest/jest/playwright is added. **Verification at each task is manual:**

- For pure logic (`storage`, `timer`, `treePositions`): paste a short snippet into the browser DevTools console and check the printed output matches expected values. Each task that introduces logic includes a console-verification step with the exact snippet and expected output.
- For UI/scene behavior: open `http://localhost:4321/pomodoro/` in a browser and confirm what's described in the verification step.

The five JS sections (`storage`, `timer`, `scene`, `notify`, `controller`) are kept DOM-free wherever possible (scene/controller are the only ones that touch the DOM) so adding a real test runner later is mechanical.

## File structure

```
public/pomodoro/
├── index.html       — markup, inline forest SVG <symbol> defs, mounts pomodoro.js
└── pomodoro.css     — design tokens (copied from blog) + layout + scene styling

public/pomodoro/pomodoro.js
                     — five sections: storage, timer, scene, notify, controller

projects/pomodoro.md — one-line entry so it appears on willbright.link's projects column
```

`index.html` references `./pomodoro.css` and `./pomodoro.js` with relative paths. The page is served by CloudFront at `https://willbright.link/pomodoro/` (S3 `index.html` default-root for the prefix).

## Dev workflow

The blog uses Astro. Run `make dev` to start the dev server at `http://localhost:4321`. Astro serves `public/pomodoro/index.html` at `http://localhost:4321/pomodoro/`. Edit any of the three files and refresh to see changes — no HMR for `public/` assets, but a full reload is fine.

---

## Task 1: Scaffold the directory and skeleton HTML

**Files:**
- Create: `public/pomodoro/index.html`
- Create: `public/pomodoro/pomodoro.css` (empty for now)
- Create: `public/pomodoro/pomodoro.js` (empty for now)

- [ ] **Step 1: Create the directory and empty files**

```bash
mkdir -p public/pomodoro
touch public/pomodoro/pomodoro.css
touch public/pomodoro/pomodoro.js
```

- [ ] **Step 2: Write `public/pomodoro/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="A pomodoro timer with a forest scene." />
    <title>Pomodoro</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />

    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    />

    <link rel="stylesheet" href="./pomodoro.css" />
  </head>
  <body>
    <a href="/" class="back-link">← willbright.link</a>

    <main class="stage" data-state="idle">
      <input
        id="priority"
        class="priority"
        type="text"
        placeholder="What are you focused on?"
        autocomplete="off"
        spellcheck="false"
        maxlength="120"
      />

      <div id="timer" class="timer">25:00</div>

      <div id="controls" class="controls">
        <button id="btn-start" class="btn btn-primary" type="button" disabled>Start focus</button>
        <button id="btn-pause" class="btn" type="button" hidden>Pause</button>
        <button id="btn-resume" class="btn btn-primary" type="button" hidden>Resume</button>
        <button id="btn-cancel" class="btn btn-ghost" type="button" hidden>Cancel</button>
        <button id="btn-start-break" class="btn btn-primary" type="button" hidden>Start break</button>
        <button id="btn-start-next" class="btn btn-primary" type="button" hidden>Start next focus</button>
      </div>

      <svg
        id="scene"
        class="scene"
        viewBox="0 0 1200 400"
        preserveAspectRatio="xMidYMax slice"
        aria-hidden="true"
      >
        <defs>
          <symbol id="tree" viewBox="0 0 60 100">
            <rect x="26" y="62" width="8" height="32" fill="#5a4a3a" />
            <polygon points="30,4 8,52 52,52" fill="#4a7c5f" />
            <polygon points="30,22 12,62 48,62" fill="#5a8c6f" />
            <polygon points="30,40 16,72 44,72" fill="#6a9c7f" />
          </symbol>
        </defs>

        <rect id="sky" class="sky" x="0" y="0" width="1200" height="280" />
        <path class="hill hill-back" d="M0,260 Q300,200 600,240 T1200,220 L1200,400 L0,400 Z" />
        <path class="hill hill-mid" d="M0,300 Q200,250 500,290 T1200,270 L1200,400 L0,400 Z" />
        <rect class="meadow" x="0" y="320" width="1200" height="80" />
        <g id="trees"></g>
      </svg>
    </main>

    <script src="./pomodoro.js"></script>
  </body>
</html>
```

- [ ] **Step 3: Start the dev server and verify the page loads**

Run: `make dev`

In a browser, open `http://localhost:4321/pomodoro/`.

Expected: A minimally-styled page with an unstyled input field, the text `25:00`, six (mostly hidden) buttons, and an SVG that renders the hills/meadow shapes (no trees yet) using the inline default fills. No console errors.

- [ ] **Step 4: Commit**

```bash
git add public/pomodoro/
git commit -m "Scaffold pomodoro SPA at public/pomodoro/"
```

---

## Task 2: Design tokens and base layout in CSS

**Files:**
- Modify: `public/pomodoro/pomodoro.css` (overwrite the empty file)

- [ ] **Step 1: Write the full stylesheet**

Replace the contents of `public/pomodoro/pomodoro.css` with:

```css
/* ── Design tokens (copied from blog Layout.astro) ──────────────── */
:root {
  --bg:            #fefdf8;
  --surface:       #f5f2eb;
  --border:        #e0dbd0;
  --border-light:  #ede9e0;
  --text:          #1c1a16;
  --muted:         #7a7468;
  --link:          #4a7c5f;
  --link-hover:    #2f5c42;

  --sage:          #4a7c5f;
  --sage-light:    #8fba9f;
  --sage-pale:     #eef5f1;
  --rose:          #c07878;
  --rose-pale:     #f9efef;
  --peach:         #c49060;
  --peach-pale:    #fdf3ea;

  --font-display:  'DM Sans', system-ui, -apple-system, sans-serif;
  --font-body:     'DM Sans', system-ui, -apple-system, sans-serif;
  --font-ui:       'DM Sans', system-ui, -apple-system, sans-serif;
  --font-mono:     'DM Mono', 'Fira Code', Consolas, monospace;

  /* sky color is state-driven; default = idle */
  --sky-fill: var(--bg);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

body {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* single-viewport, no scroll */
}

.back-link {
  position: absolute;
  top: 1rem;
  left: 1.25rem;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  color: var(--muted);
  text-decoration: none;
  z-index: 10;
}
.back-link:hover { color: var(--link); }

.stage {
  flex: 1;
  display: grid;
  grid-template-rows: auto auto auto 1fr;
  align-items: center;
  justify-items: center;
  padding-top: 5rem;
  position: relative;
}

/* ── Priority input ───────────────────────────────────────────── */
.priority {
  font-family: var(--font-body);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--text);
  text-align: center;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  padding: 0.5rem 0.75rem;
  width: min(28rem, 80vw);
  outline: none;
  transition: border-color 0.15s;
}
.priority::placeholder { color: var(--muted); opacity: 0.7; }
.priority:focus { border-color: var(--sage); }
.priority:disabled { color: var(--text); -webkit-text-fill-color: var(--text); opacity: 1; cursor: default; }

/* When a session is running we visually freeze the input as static text */
.stage[data-state="focus"] .priority,
.stage[data-state="break"] .priority,
.stage[data-state="paused-focus"] .priority,
.stage[data-state="paused-break"] .priority,
.stage[data-state="focus_done"] .priority,
.stage[data-state="break_done"] .priority {
  border-bottom-color: transparent;
  pointer-events: none;
}

/* ── Timer ────────────────────────────────────────────────────── */
.timer {
  font-family: var(--font-mono);
  font-size: clamp(4rem, 12vw, 7rem);
  font-weight: 500;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  margin-top: 1.5rem;
  color: var(--text);
}

/* ── Controls ─────────────────────────────────────────────────── */
.controls {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.btn {
  font-family: var(--font-ui);
  font-size: 0.95rem;
  font-weight: 500;
  padding: 0.65rem 1.4rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, color 0.12s, transform 0.08s;
}
.btn:hover { background: var(--border-light); }
.btn:active { transform: translateY(1px); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-primary {
  background: var(--sage);
  color: var(--bg);
  border-color: var(--sage);
}
.btn-primary:hover { background: var(--link-hover); border-color: var(--link-hover); }
.btn-primary:disabled { background: var(--sage); border-color: var(--sage); }

.btn-ghost {
  background: transparent;
  color: var(--muted);
  border-color: var(--border-light);
}
.btn-ghost:hover { background: var(--surface); color: var(--text); }

/* ── Scene ────────────────────────────────────────────────────── */
.scene {
  width: 100%;
  height: auto;
  display: block;
  align-self: end;
  margin-top: 2rem;
}

.sky { fill: var(--sky-fill); transition: fill 600ms ease; }
.hill-back { fill: #d6e3d8; }
.hill-mid  { fill: #b6d2bc; }
.meadow    { fill: #c9d9b8; }

/* ── State-driven sky tints ───────────────────────────────────── */
.stage[data-state="idle"]        { --sky-fill: var(--bg); }
.stage[data-state="focus"],
.stage[data-state="paused-focus"]{ --sky-fill: var(--sage-pale); }
.stage[data-state="break"],
.stage[data-state="paused-break"]{ --sky-fill: var(--peach-pale); }
.stage[data-state="focus_done"]  { --sky-fill: var(--sage-pale); }
.stage[data-state="break_done"]  { --sky-fill: var(--peach-pale); }

/* ── End-of-timer pulse ───────────────────────────────────────── */
@keyframes pulse-sage {
  0%   { fill: var(--sage-pale); }
  40%  { fill: var(--sage-light); }
  100% { fill: var(--sage-pale); }
}
@keyframes pulse-peach {
  0%   { fill: var(--peach-pale); }
  40%  { fill: var(--peach); }
  100% { fill: var(--peach-pale); }
}
.sky.pulse-sage  { animation: pulse-sage  900ms ease-out; }
.sky.pulse-peach { animation: pulse-peach 900ms ease-out; }

/* ── Mobile ───────────────────────────────────────────────────── */
@media (max-width: 600px) {
  .stage { padding-top: 4rem; }
  .priority { font-size: 1.1rem; width: 90vw; }
  .controls { flex-wrap: wrap; justify-content: center; }
}
```

- [ ] **Step 2: Verify in browser**

Refresh `http://localhost:4321/pomodoro/`.

Expected:
- Cream background, sage-bordered priority input centered near the top with "What are you focused on?" placeholder.
- Large `25:00` in DM Mono below the input.
- A single sage "Start focus" button (disabled, slightly faded) below the timer.
- The forest SVG fills the bottom of the viewport: cream sky, two layered sage hills, green meadow strip. No trees yet.
- No scrollbar; content fits the viewport.

Resize the window to phone width — content stacks, hills scale.

- [ ] **Step 3: Commit**

```bash
git add public/pomodoro/pomodoro.css
git commit -m "Add base styles and design tokens for pomodoro page"
```

---

## Task 3: `storage` module — load, save, daily reset

**Files:**
- Modify: `public/pomodoro/pomodoro.js`

The `storage` module is pure JS — no DOM access. It owns the `pomodoro.v1` localStorage key.

- [ ] **Step 1: Write the storage module**

Append to `public/pomodoro/pomodoro.js`:

```js
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
    // daily reset
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
```

- [ ] **Step 2: Verify in DevTools console**

Refresh `http://localhost:4321/pomodoro/`. Open DevTools → Console.

Run:

```js
localStorage.removeItem('pomodoro.v1');
let s = storage.load();
console.assert(s.priority === '', 'fresh load: priority empty');
console.assert(s.trees.count === 0, 'fresh load: count 0');
console.assert(s.trees.date === storage.todayLocal(), 'fresh load: today');

storage.setPriority(s, 'ship the report');
storage.incrementTrees(s);
storage.incrementTrees(s);

let s2 = storage.load();
console.assert(s2.priority === 'ship the report', 'persisted priority');
console.assert(s2.trees.count === 2, 'persisted count');

// simulate yesterday
localStorage.setItem('pomodoro.v1', JSON.stringify({
  priority: 'old', trees: { date: '2020-01-01', count: 99 }
}));
let s3 = storage.load();
console.assert(s3.trees.count === 0, 'daily reset zeroes count');
console.assert(s3.trees.date === storage.todayLocal(), 'daily reset to today');
console.assert(s3.priority === 'old', 'priority survives daily reset');

// malformed JSON
localStorage.setItem('pomodoro.v1', '{not json');
let s4 = storage.load();
console.assert(s4.priority === '', 'malformed → defaults');

console.log('storage OK');
```

Expected: Console prints `storage OK` with no `Assertion failed` messages.

- [ ] **Step 3: Commit**

```bash
git add public/pomodoro/pomodoro.js
git commit -m "Add storage module for pomodoro state"
```

---

## Task 4: `timer` module — drift-proof countdown

**Files:**
- Modify: `public/pomodoro/pomodoro.js`

The `timer` is a finite-state machine over `idle` / `running` / `paused`. It calls callbacks (`onTick`, `onComplete`) so it stays DOM-free.

- [ ] **Step 1: Append the timer module**

Append to `public/pomodoro/pomodoro.js`:

```js
// ── timer ─────────────────────────────────────────────────────────────────
const timer = (() => {
  let endsAt = null;        // wall-clock ms when timer fires
  let remainingMs = 0;      // for paused state
  let intervalId = null;
  let onTick = () => {};
  let onComplete = () => {};
  let mode = 'idle';        // 'idle' | 'running' | 'paused'

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
```

- [ ] **Step 2: Verify in DevTools console**

Refresh the page. Run in console:

```js
console.assert(timer.format(25 * 60 * 1000) === '25:00', 'format 25min');
console.assert(timer.format(0) === '00:00', 'format 0');
console.assert(timer.format(1000) === '00:01', 'format 1s');
console.assert(timer.format(59 * 1000 + 999) === '01:00', 'format ceil up');
console.assert(timer.format(60 * 1000) === '01:00', 'format exact 1min');

let ticks = 0, completed = false;
timer.setHandlers({
  onTick: (ms) => { ticks++; },
  onComplete: () => { completed = true; },
});

timer.start(800);                       // 0.8 second timer
console.assert(timer.getMode() === 'running');

await new Promise(r => setTimeout(r, 300));
timer.pause();
console.assert(timer.getMode() === 'paused', 'pause sets mode');
const remAfterPause = timer.remainingNow();
console.assert(remAfterPause > 400 && remAfterPause < 600, `paused remaining ~500: ${remAfterPause}`);

await new Promise(r => setTimeout(r, 400));   // pretend we walked away
console.assert(timer.remainingNow() === remAfterPause, 'paused remaining stable');

timer.resume();
await new Promise(r => setTimeout(r, 700));
console.assert(completed === true, 'onComplete fired');
console.assert(timer.getMode() === 'idle', 'idle after complete');
console.log('timer OK, ticks =', ticks);
```

Expected: Console prints `timer OK, ticks = ...` (a number ≥ 3) with no assertion failures.

- [ ] **Step 3: Commit**

```bash
git add public/pomodoro/pomodoro.js
git commit -m "Add timer module with drift-proof countdown"
```

---

## Task 5: `notify` module — Web Audio chime + browser notification

**Files:**
- Modify: `public/pomodoro/pomodoro.js`

- [ ] **Step 1: Append the notify module**

Append to `public/pomodoro/pomodoro.js`:

```js
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
```

- [ ] **Step 2: Verify in DevTools console**

Refresh the page. Run:

```js
notify.chime();
```

Expected: A brief two-note bell plays through the speakers.

Then run:

```js
await notify.ensurePermission();
notify.send('Test', 'Notification works');
```

Expected: First call prompts for notification permission (if not already granted/denied). If you grant it, a system notification titled "Test" appears.

- [ ] **Step 3: Commit**

```bash
git add public/pomodoro/pomodoro.js
git commit -m "Add notify module: Web Audio chime + browser notifications"
```

---

## Task 6: `scene` module — render trees, sky state, pulse

**Files:**
- Modify: `public/pomodoro/pomodoro.js`

`scene` is the only purely-DOM-touching module. It exposes three actions: render N trees, set the stage's `data-state`, and pulse the sky.

- [ ] **Step 1: Append the scene module**

Append to `public/pomodoro/pomodoro.js`:

```js
// ── scene ─────────────────────────────────────────────────────────────────
const scene = (() => {
  const MAX_DRAWN_TREES = 12;

  // Mulberry32: small, good-enough deterministic PRNG seeded by an int.
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

  // For a given count and seed, return [{x, y, scale}] for up to MAX_DRAWN_TREES trees.
  // Trees are placed in horizontal slots across the meadow with slight random jitter.
  function treePositions(count, seed) {
    const drawn = Math.min(count, MAX_DRAWN_TREES);
    if (drawn === 0) return [];
    const rand = prng(seed);
    // Slot layout across viewBox 0..1200, roughly y=270 (on the meadow).
    const slotW = 1200 / MAX_DRAWN_TREES;
    const positions = [];
    for (let i = 0; i < drawn; i++) {
      const slotCenter = slotW * (i + 0.5);
      const jitterX = (rand() - 0.5) * slotW * 0.6;
      const jitterY = (rand() - 0.5) * 14;
      const scale = 0.85 + rand() * 0.35;     // 0.85 .. 1.20
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

  function pulse(kind /* 'sage' | 'peach' */) {
    const sky = document.getElementById('sky');
    sky.classList.remove('pulse-sage', 'pulse-peach');
    // Force reflow so the animation restarts even if the same class is re-added.
    void sky.getBoundingClientRect();
    sky.classList.add(kind === 'peach' ? 'pulse-peach' : 'pulse-sage');
  }

  return { renderTrees, setState, pulse, treePositions, seedFromDate, MAX_DRAWN_TREES };
})();
```

- [ ] **Step 2: Verify trees render in browser via console**

Refresh the page. Run:

```js
scene.renderTrees(0, '2026-04-28');
```
Expected: No trees on the meadow.

```js
scene.renderTrees(3, '2026-04-28');
```
Expected: Three trees evenly distributed across the meadow.

```js
scene.renderTrees(12, '2026-04-28');
```
Expected: Twelve trees filling the meadow.

```js
scene.renderTrees(20, '2026-04-28');
```
Expected: Still only twelve trees (cap holds).

```js
scene.renderTrees(5, '2026-04-28');
scene.renderTrees(5, '2026-04-29');
```
Expected: Same number of trees, but in different positions (date seed changes layout).

- [ ] **Step 3: Verify state + pulse via console**

```js
scene.setState('focus');
```
Expected: Sky tints sage-pale.

```js
scene.setState('break');
```
Expected: Sky tints peach-pale.

```js
scene.setState('idle'); scene.pulse('sage');
```
Expected: Sky briefly flashes a darker sage and returns to cream.

```js
scene.pulse('peach');
```
Expected: Sky briefly flashes peach.

- [ ] **Step 4: Commit**

```bash
git add public/pomodoro/pomodoro.js
git commit -m "Add scene module: tree placement, sky state, end-of-timer pulse"
```

---

## Task 7: `controller` — state machine, button wiring, end-to-end behavior

**Files:**
- Modify: `public/pomodoro/pomodoro.js`

The controller owns:
- The persistent `state` object (loaded from `storage`).
- The current state machine value: `idle | focus | paused-focus | focus_done | break | paused-break | break_done`.
- Wiring DOM events (button clicks, priority input, visibility change) to `timer` / `notify` / `scene`.

- [ ] **Step 1: Append the controller**

Append to `public/pomodoro/pomodoro.js`:

```js
// ── controller ────────────────────────────────────────────────────────────
(() => {
  const FOCUS_MS = 25 * 60 * 1000;
  const BREAK_MS = 5 * 60 * 1000;

  const state = storage.load();
  let machine = 'idle';        // idle | focus | paused-focus | focus_done | break | paused-break | break_done
  let pausedRemainingMs = 0;   // populated on pause; consumed on resume
  let lastDisplay = '';        // for tab-title diffing

  // ── DOM refs ────────────────────────────────────────────────────────────
  const $priority = document.getElementById('priority');
  const $timer    = document.getElementById('timer');
  const $start    = document.getElementById('btn-start');
  const $pause    = document.getElementById('btn-pause');
  const $resume   = document.getElementById('btn-resume');
  const $cancel   = document.getElementById('btn-cancel');
  const $break    = document.getElementById('btn-start-break');
  const $next     = document.getElementById('btn-start-next');

  // ── Init ────────────────────────────────────────────────────────────────
  $priority.value = state.priority;
  refreshStartEnabled();
  scene.renderTrees(state.trees.count, state.trees.date);
  scene.setState('idle');
  setTimerDisplay(FOCUS_MS);
  showButtonsFor('idle');

  // ── Helpers ─────────────────────────────────────────────────────────────
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
    scene.setState(m === 'paused-focus' ? 'paused-focus'
                 : m === 'paused-break' ? 'paused-break'
                 : m);
    showButtonsFor(m);
    if (m === 'idle') {
      $priority.disabled = false;
    } else {
      $priority.disabled = true;
    }
  }

  // ── Timer wiring ────────────────────────────────────────────────────────
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

  // ── Priority input ──────────────────────────────────────────────────────
  let saveTimeoutId = null;
  $priority.addEventListener('input', () => {
    refreshStartEnabled();
    if (saveTimeoutId) clearTimeout(saveTimeoutId);
    saveTimeoutId = setTimeout(() => storage.setPriority(state, $priority.value), 300);
  });

  // ── Buttons ─────────────────────────────────────────────────────────────
  $start.addEventListener('click', () => {
    state.priority = $priority.value.trim();
    storage.setPriority(state, state.priority);
    notify.ensurePermission();
    setMachine('focus');
    timer.start(FOCUS_MS);
  });

  $pause.addEventListener('click', () => {
    timer.pause();
    pausedRemainingMs = timer.remainingNow();
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

  // ── Visibility: re-sync display immediately on tab refocus ──────────────
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && (machine === 'focus' || machine === 'break')) {
      const r = timer.remainingNow();
      if (r <= 0) return; // tick will handle completion
      setTimerDisplay(r);
    }
  });
})();
```

- [ ] **Step 2: Manual end-to-end verification**

Refresh `http://localhost:4321/pomodoro/`. Walk through the full happy path:

1. The "Start focus" button is **disabled** and the priority input shows the placeholder.
2. Type "test priority". Start button becomes **enabled**.
3. Click **Start focus**.
   - The first time only: a notification permission prompt appears. Grant it (so we can verify notifications later).
   - Sky tints sage-pale; priority field becomes static; Pause and Cancel buttons appear; timer begins counting down from `25:00`.
   - The browser tab title updates to e.g. `24:59 · test priority — Pomodoro`.
4. Click **Pause**. Timer freezes on the current time. Resume + Cancel are visible. Sky stays tinted.
5. Wait ~5 seconds. Confirm the timer display does not decrement.
6. Click **Resume**. Timer resumes from where it paused. Pause + Cancel return.
7. Click **Cancel**. Returns to idle: timer shows `25:00`, sky returns to cream, priority field becomes editable again, single Start button visible.
8. To verify completion behavior without waiting 25 minutes, paste in DevTools console:
   ```js
   timer.cancel();
   // pretend "Start focus" was clicked, but with a 3-second timer
   document.querySelector('.stage').dataset.state = 'focus';
   document.getElementById('priority').disabled = true;
   timer.start(3000);
   ```
   Wait 3 seconds. Expected:
   - Sky pulses (briefly darker sage).
   - The chime plays.
   - A "Focus complete" browser notification appears.
   - **A new tree appears** in the meadow.
   - Buttons collapse to a single "Start break".
   - Timer shows `05:00`.
9. Click **Start break**. Sky tints peach-pale, timer starts counting down from `05:00`. Buttons are Pause + Cancel.
10. Run `timer.start(2000)` in console to skip to break completion.
    - Sky pulses peach.
    - Chime plays.
    - "Break over" notification appears.
    - **No new tree appears** (only focus completion plants trees).
    - Single "Start next focus" button visible.
11. Click **Start next focus**. Returns to focus mode with `25:00`.
12. Reload the page. Confirm:
    - Priority text is still "test priority".
    - The tree(s) planted in step 8 are still on the meadow in the same positions.
    - Timer is back at `25:00`, single Start button visible.

If any of those steps fail, fix the controller and re-verify before moving on.

- [ ] **Step 3: Commit**

```bash
git add public/pomodoro/pomodoro.js
git commit -m "Wire pomodoro state machine, controls, and full session flow"
```

---

## Task 8: List the project on willbright.link

**Files:**
- Create: `projects/pomodoro.md`

The blog's homepage reads `projects/*.md` to render the projects column. Adding an entry surfaces the new SPA there.

- [ ] **Step 1: Create the project entry**

Write `projects/pomodoro.md`:

```markdown
---
name: Pomodoro
url: https://willbright.link/pomodoro/
order: 1
isNew: true
---

A pomodoro timer with a forest scene. Type one priority, focus for 25 minutes, plant a tree.
```

This pushes "Pomodoro" to `order: 1` (most prominent). Update the existing yt2txt entry to demote it.

- [ ] **Step 2: Demote yt2txt to order: 2**

Modify `projects/yt2txt.md`. Change `order: 1` to `order: 2`, and change `isNew: true` to `isNew: false`.

After: the file frontmatter should read:

```markdown
---
name: yt2txt
url: https://yt2txt.willbright.link
order: 2
isNew: false
---
```

- [ ] **Step 3: Demote sleep-health to order: 3**

Modify `projects/sleep-health.md`. Change `order: 2` to `order: 3`. Leave `isNew: false`.

- [ ] **Step 4: Verify the homepage**

In a browser, open `http://localhost:4321/`.

Expected: The Projects column lists Pomodoro first (with a "new" badge), then yt2txt, then Sleep Health. Clicking "Pomodoro" opens the new SPA at `/pomodoro/` (in dev: `http://localhost:4321/pomodoro/`).

- [ ] **Step 5: Commit**

```bash
git add projects/
git commit -m "Add Pomodoro to projects list, demote yt2txt and sleep-health"
```

---

## Task 9: Final QA pass

This task has no code changes. It's a single manual verification of everything together.

- [ ] **Step 1: Hard reload + clean state**

In DevTools console: `localStorage.clear()`. Hard-reload `http://localhost:4321/pomodoro/` (Cmd+Shift+R).

Expected: Empty priority field, Start disabled, `25:00`, no trees, cream sky.

- [ ] **Step 2: Walk a full focus → break → focus cycle without console shortcuts**

Type a priority (e.g. "QA pass"), click **Start focus**, then *immediately* paste this in console to compress the timer (just for QA):

```js
timer.cancel();
document.querySelector('.stage').dataset.state = 'focus';
document.getElementById('priority').disabled = true;
timer.start(2000);
```

Wait through all five end-of-timer effects (visual pulse, chime, notification, new tree, button change). Click "Start break". Compress break similarly with `timer.start(1500)`. Click "Start next focus". Click **Cancel** to wind down.

Expected: All transitions clean, no console errors.

- [ ] **Step 3: Mobile viewport check**

In DevTools, switch device emulation to iPhone SE. Reload.

Expected: Priority field, timer, button, and forest all fit in the viewport with no horizontal scroll. Forest scales proportionally.

- [ ] **Step 4: localStorage-disabled check**

In Chrome DevTools → Application → Storage → uncheck "Local storage" (or use a private window where it's blocked). Reload `http://localhost:4321/pomodoro/`.

Expected: The page still loads and works for the current session. No errors. (Priority and trees won't persist across reloads, which is the documented fallback.)

- [ ] **Step 5: Astro build check**

Stop the dev server. Run:

```bash
make build
```

Expected: Build succeeds. Check that `dist/pomodoro/` contains `index.html`, `pomodoro.css`, `pomodoro.js` (Astro should pass them through unchanged).

```bash
ls dist/pomodoro/
```

- [ ] **Step 6: Final commit if any fixes were needed**

If steps 1–5 surfaced issues and you fixed them, commit those fixes:

```bash
git add public/pomodoro/
git commit -m "Polish from final QA pass"
```

If nothing needed fixing, skip this step.

- [ ] **Step 7: Confirm the deploy path**

The blog uses GitHub Actions on push to `main` to run `make deploy`. After merging this work, push to main and verify the page is live at `https://willbright.link/pomodoro/`. Don't push as part of this plan — the user controls release.

---

## Self-review checklist

(Done by the plan author after writing — for handoff completeness.)

- ✅ Spec coverage: file layout, UI layout, state machine, timer mechanics, persistence, forest scene, end-of-timer cues, edge cases, component boundaries — each maps to a task above. The chime delivery is implemented via Web Audio (refinement called out at top).
- ✅ No `TBD` / `TODO` / "implement later" — every step has concrete code or commands.
- ✅ Identifier consistency: `storage.load`, `storage.save`, `storage.setPriority`, `storage.incrementTrees`, `storage.todayLocal`; `timer.start/pause/resume/cancel/remainingNow/setHandlers/getMode/format`; `scene.renderTrees/setState/pulse`; `notify.chime/ensurePermission/send` — used consistently across tasks.
- ✅ State machine values: `idle`, `focus`, `paused-focus`, `focus_done`, `break`, `paused-break`, `break_done` — match between controller and CSS `data-state` selectors.
- ✅ DOM IDs in HTML (Task 1) match queries in controller (Task 7).
- ✅ Files in `public/` are passed through verbatim by Astro (verified against project's `astro.config.mjs` workflow); no Astro coupling required.
