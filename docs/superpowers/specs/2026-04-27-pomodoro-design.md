# Pomodoro Timer SPA — Design

**Date:** 2026-04-27
**Location:** `public/pomodoro/` in the `my-blog` repo
**Live URL (after deploy):** `https://willbright.link/pomodoro/`

## Goal

A single-page Pomodoro timer with a forest scene. The user types one priority, runs a 25-minute focus session, and is then prompted to take a 5-minute break. Each completed focus session plants a tree in the scene. Visual styling matches the main `my-blog` aesthetic (sage/cream, DM Sans/DM Mono).

## Scope

**In scope (v1):**
- Single priority input, persisted to `localStorage`.
- 25-minute focus timer / 5-minute break timer.
- State machine: idle → focus → focus-done (prompt) → break → break-done (prompt) → focus → …
- Pause + cancel controls during a running timer.
- Three end-of-timer cues: visual pulse, audio chime, browser notification.
- Forest scene that grows one tree per completed focus session, resets daily at local midnight.
- Mobile-responsive single-viewport layout.

**Out of scope (v1):**
- Long break after 4 cycles (classic Pomodoro variant) — always 5 min.
- Settings UI (custom durations, sound/notification toggles, themes).
- Stats / history beyond today's forest.
- Mid-session priority editing.
- Service worker / offline support.
- Persisting a running timer across reloads.
- Lifetime totals or streaks.

## File Layout

```
public/pomodoro/
├── index.html       — markup, inline forest SVG <symbol> defs
├── pomodoro.css     — design tokens (copied from blog) + layout + scene styling
├── pomodoro.js      — state machine, timer, persistence, notifications, audio
└── chime.mp3        — short soft bell (~1s, public-domain / CC0)
```

Files in Astro's `public/` directory pass through verbatim at build time. The existing GitHub Actions workflow on push to `main` (and `make deploy`) syncs `public/` to S3 and invalidates CloudFront. **No infra changes required.**

`pomodoro.css` redeclares the design tokens (`--sage`, `--bg`, `--font-display`, etc.) and `@import`s the same Google Fonts as the blog so the page is fully self-contained but visually consistent.

## UI Layout

Single viewport, no scroll, anchored from top to bottom:

```
┌─────────────────────────────────────────────┐
│  ← back to willbright.link                  │  top-left, muted, small
│                                             │
│         [ priority input field ]            │  centered, editable when idle
│                                             │
│                  25:00                      │  large mono numerals
│                                             │
│           [ Start focus ]                    │  primary button (state-dependent)
│                                             │
│  ░░░░░░░ FOREST SVG ░░░░░░░░░░░░░░░░░░░░░  │  anchored to bottom, full width
└─────────────────────────────────────────────┘
```

**Three visual states:**
1. **Idle** — sky = `--bg` (cream). Priority field editable. "Start focus" button (disabled until priority is non-empty).
2. **Focus** — sky tints to `--sage-pale`. Priority text rendered as static (not an input). Pause + Cancel buttons.
3. **Break** — sky tints to `--peach-pale`. Same Pause + Cancel buttons.

**Typography:**
- Timer: DM Mono, ~6rem, `--text` color, `font-variant-numeric: tabular-nums`.
- Priority: DM Sans, ~1.25rem, centered. Sage placeholder: "What are you focused on?".
- Buttons: DM Sans, sage background (`--sage`), cream text, generous padding, rounded corners.

**Mobile:** stacks naturally; forest scales down, timer shrinks. `@media (max-width: 600px)` matches the blog's breakpoint.

## State Machine

```
       ┌──────┐  start    ┌───────┐  00:00   ┌─────────────┐
       │ IDLE │ ────────▶ │ FOCUS │ ───────▶ │ FOCUS_DONE  │
       └──────┘           └───────┘          └─────────────┘
          ▲                  │ ▲                    │ start break
          │                  │ │ resume             ▼
          │              pause │              ┌───────┐  00:00  ┌─────────────┐
          │                  ▼ │              │ BREAK │ ──────▶ │ BREAK_DONE  │
          │             ┌────────┐            └───────┘         └─────────────┘
          │             │ PAUSED │              │ ▲                    │
          │             └────────┘              │ │                    │ start focus
          │                                  pause│ │ resume             │
          │  cancel                             ▼ │                      │
          └────────────────────────────────────────────────────────────────┘
```

`PAUSED` remembers which mode it came from (FOCUS or BREAK) so Resume returns correctly.

**Buttons by state:**

| State | Buttons shown |
|---|---|
| IDLE | `Start focus` (disabled until priority is non-empty) |
| FOCUS / BREAK | `Pause`, `Cancel` |
| PAUSED | `Resume`, `Cancel` |
| FOCUS_DONE | `Start break` |
| BREAK_DONE | `Start next focus` |

**Cancel** → returns to IDLE. Does *not* plant a tree. Restores priority field to editable. Already-planted trees from earlier today stay.

## Timer Mechanics

- On start/resume: store `endsAt = Date.now() + remainingMs` (wall-clock timestamp).
- Tick every 250ms via `setInterval`. Compute `remainingMs = endsAt - Date.now()`. When `≤ 0`, transition to the appropriate `*_DONE` state and fire end-of-timer cues.
- **Drift-proof:** if the browser throttles our interval while backgrounded, the next tick still computes the correct remaining time from the wall clock.
- On pause: store `remainingMs = endsAt - Date.now()`, clear `endsAt`.
- Display: `mm:ss` from `Math.ceil(remainingMs / 1000)` so the timer reads "25:00" the instant focus starts.

**Tab title sync:** while a timer runs, set `document.title = "${mm:ss} · ${priority} — Pomodoro"`. Reset to `"Pomodoro"` when idle.

**Page lifecycle:**
- `visibilitychange` → visible: re-render immediately (don't wait for next 250ms tick).
- `beforeunload` mid-session: no warning. Closing the tab cancels the run.

## Persistence

Single localStorage key: `pomodoro.v1`, JSON-encoded.

```json
{
  "priority": "Ship the Q2 report draft",
  "trees": {
    "date": "2026-04-27",
    "count": 3
  }
}
```

**`priority`** — written on every keystroke (debounced 300ms) and on session start. Read on page load.

**`trees`** — `date` is `YYYY-MM-DD` in local timezone. `count` is a non-negative integer.

**Daily reset logic:** on page load and on every focus completion, compare `trees.date` to today (local). If different, replace with `{ date: today, count: 0 }` *before* incrementing on completion. No background timer needed.

**Rendering trees from `count`:** a deterministic function `treePositions(count, seed)` returns `(x, y, scale)` for each tree. The seed is the date string, so positions are stable within a day but vary day-to-day. Up to 12 trees are positioned across the meadow; for `count > 12`, the value continues to increment (so the date-comparison reset works correctly) but no additional tree is drawn.

**Versioning:** the `.v1` suffix lets us change the schema later without breaking on old data.

**Failure modes:**
- localStorage disabled → silently fall back to in-memory state. Page works for current session; nothing persists.
- Malformed JSON → reset to defaults silently.

**Deliberately not stored:** running timer state (`endsAt`, paused remaining, current state machine value), lifetime totals, sound/notification preferences.

## Forest Scene

A horizontal SVG anchored to the bottom of the viewport, full width.

- Background: layered muted sage hills (2–3 layers, lighter as they recede).
- Foreground: a meadow strip.
- Sky: a `<rect>` whose fill is driven by a CSS variable on the parent — state transitions tint the whole sky.
- Trees: simple flat illustrations. Sage triangle/cluster shapes (e.g., 2–3 stacked triangles) with a darker trunk. No animation.
- Initial daily state: empty meadow with hills (no trees).

## End-of-Timer Cues

Fire simultaneously when a timer hits 00:00:

**1. Visual pulse** (always works, no permission)
- Sky `<rect>` briefly increases opacity / shifts hue via a CSS keyframe (~600ms).
- Focus completion → soft sage glow.
- Break completion → soft peach glow.
- This is the only *guaranteed* cue.

**2. Audio chime** (works after first user interaction)
- `chime.mp3` loaded on page load: `new Audio('chime.mp3')`, `preload="auto"`.
- On completion: `audio.currentTime = 0; audio.play()`.
- The user has clicked "Start focus" by definition, so autoplay restrictions don't apply.
- Source: a CC0 / public-domain bell sound (~1 sec). Volume moderate; no in-page volume slider in v1.

**3. Browser notification** (requires permission)
- On the *first* "Start focus" click, request permission via `Notification.requestPermission()`. If denied, never ask again.
- Focus completion: `new Notification('Focus complete', { body: 'Time for a 5-min break.', icon: '/favicon.svg', silent: true })`.
- Break completion: `new Notification('Break over', { body: 'Ready for the next focus session?', icon: '/favicon.svg', silent: true })`.
- `silent: true` to avoid the OS doubling up on the chime.

**Permission states:**

| State | Behavior |
|---|---|
| `default` | Ask on first Start click. Fire on completion if granted. |
| `granted` | Fire on completion. |
| `denied` | Skip the notification call entirely. Visual + chime still fire. |

**Tree planting:** on focus completion (only), `trees.count` increments and the scene re-renders with the new tree.

## Edge Cases

- **Empty priority** → "Start focus" disabled.
- **System sleep mid-timer** → drift-proof timer reflects correct remaining time on wake, or shows the appropriate `*_DONE` state if the wake time is past `endsAt`. End-of-timer cues only fire if the tab is awake at 00:00; no retroactive chime/notification.
- **Refresh / tab close mid-session** → cancels the session. Priority and trees persist. In-flight timer state is not restored.
- **Multiple tabs open** → each tab is independent; `localStorage.trees.count` is last-write-wins. Acceptable for v1.

## Component Boundaries (for `pomodoro.js`)

Loose modular structure within a single file (no bundler), via top-level closures or namespaced object:

- **`storage`** — load/save `pomodoro.v1`, daily reset logic, malformed-data handling.
- **`timer`** — start/pause/resume/cancel, `endsAt` tracking, ticking, transitions to `*_DONE`. Pure mechanics, no DOM.
- **`scene`** — render trees from a count + seed, sky-state class on the SVG parent, glow keyframe trigger.
- **`notify`** — chime playback, notification permission + dispatch.
- **`controller`** — state machine, wires UI button clicks to `timer` calls, listens for `timer` completion to fire `scene` and `notify`.

Each unit testable in isolation in principle (no test infra in v1, but boundaries should make adding it later trivial).

## Open Questions

None at design time. Tree SVG aesthetic and chime sound selection are implementation-time decisions that don't affect the spec.
