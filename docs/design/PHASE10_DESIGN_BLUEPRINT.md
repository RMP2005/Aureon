# AUREON — PHASE 10 DESIGN BLUEPRINT

**Product thesis:** Urban Intelligence Operating System.
**Experience model:** NASA mission control × Palantir Gotham × Bloomberg Terminal × next-generation digital twin.
**Status:** LOCKED DIRECTION — awaiting approval before implementation.

Design pillars (non-negotiable): **Trust · Precision · Clarity · Controlled urgency · Cinematic impact.**
Explicitly rejected: generic AI-startup aesthetics, purple/cyan gradient SaaS look, floating glass cards everywhere, template dashboards.

---

## 0. Experience Model

| Surface | Behavior | Content |
|---|---|---|
| **Landing** (`/`) | Cinematic **scroll-based storytelling journey** (~600vh). Never zero-scroll. | The Bangalore digital twin introduces the product. The city is the hero — no logo wall, no marketing illustration. |
| **Command Center** (`/command`, replaces `/dashboard` as home after entry) | **Zero-scroll, full-viewport mission control.** No page scrolling ever. | Living 3D twin center, ops panels left/right, timeline + metrics bottom. |

---

## 1. DESIGN SYSTEM

### 1.1 Color System

#### Core Palette (LOCKED)

| Token | Hex | Meaning | Rules |
|---|---|---|---|
| `void` | `#05070D` | Obsidian Void — global background | Only true page base |
| `teal-core` | `#16F2D4` | Electric Teal — live units, active network, operational state | Primary activity color. Never used decoratively |
| `violet-intel` | `#7C5CFF` | Deep Ultraviolet — predictions, adaptive reasoning, AI decisions | **Exclusively** the AI layer. Users learn: violet = machine thinking |
| `titanium` | `#D6B45A` | Warm Titanium — roads, geography, infrastructure | Map structure, graticule, static geometry |
| `crit-red` | `#FF3655` | Critical Red — active incidents, failures, danger | **Never decorative.** If red is on screen, something is happening |

#### Derived Tokens (supporting cast — subordinate to locked palette)

| Token | Value | Meaning |
|---|---|---|
| `surface-1/2/3` | `#090E18` / `#0C1322` / `#111A2E` | Panel layers above void |
| `hairline` / `hairline-strong` | `rgba(237,242,247,.06)` / `.12` | Borders, dividers |
| `text-primary` / `secondary` / `muted` | `#EDF2F7` / `#93A0B4` / `#5B6678` | Type hierarchy |
| `amber-warn` | `#F5B841` | Caution: queued, degraded, on-scene, mismatch |
| `orange-high` | `#FF8A4A` | Severity: HIGH incidents, heat step |
| `heat-ramp` | `#16F2D4 → #57DCA8 → #F5B841 → #FF8A4A → #FF3655` | Hospital load, congestion intensity |

Semantic discipline:
- **Incident severity:** CRITICAL `#FF3655` · HIGH `#FF8A4A` · MODERATE `#F5B841` · LOW `#93A0B4`.
- **Ambulance states:** idle = teal outline · dispatched/en-route = solid teal · on-scene = teal pulse · transporting = teal + titanium destination arrow · handover = amber. Operational states vary by *shape/intensity*, not extra hues.
- **Violet appears only on:** AI decision arcs, reason chips, adaptive mode badge, prediction overlays, ledger accents.
- Contrast floor: all text ≥ 4.5:1 on its composed surface; status glyphs ≥ 3:1; color never the sole signal (shape/prefix always paired).

### 1.2 Typography

| Role | Font | Usage |
|---|---|---|
| Display | **Space Grotesk** 500/600/700 | Headlines, panel titles, big numerals contexts |
| UI | **Inter** 400/500/600 | Body, controls, descriptions |
| Telemetry | **JetBrains Mono** 400/500/700 (`tabular-nums` mandatory) | All numbers, timestamps, coordinates, IDs, tickers |
| HUD stamp (optional accent) | **IBM Plex Mono** | Section stamps: `// SECTOR-04`, `// DECISION LEDGER` |

Scale (px/line-height):

```
display-xl  72/76  SG 700  -2%   (landing finale)
display-lg  56/60  SG 600        (landing chapters)
h1          40/44  SG 600
h2          28/34  SG 500
h3          20/28  SG 500
body-l      16/26  Inter
body        14/22  Inter
caption     12/18  Inter
micro       11/16  Inter 500 UPPERCASE tracking +6%   (HUD labels)
mono-data   13/20  JBM tabular
mono-stamp  11/16  IPM uppercase tracking +8%
```

Rules: every dynamic number renders in mono with tabular figures; micro-labels always uppercase + tracked; no font below 11px anywhere.

### 1.3 Spacing & Grid

Two density regimes:

| Regime | Base scale | Rhythm | Used by |
|---|---|---|---|
| **Cinematic** (landing) | 8px | Chapter padding 120–240px vertical, content max-w 1200px | Landing acts |
| **Operational** (command) | 4px | Steps 4/8/12/16/20/24; panel padding 12–16px; gutter 8px | Command center |

Radii: chips 4 · panels 8 · modals/drawers 12 · buttons 6. Borders always 1px hairline; selected state = 1px token-colored border + faint outer ring (no drop-shadow soup).

### 1.4 Iconography & Glyphs
Phosphor icons, 1.5px stroke, single family per hierarchy level. Status dots are geometric (circle/ring/triangle for info/warn/crit) so state survives color-blind viewing. No emoji anywhere in product surfaces.

### 1.5 Data Visualization Standards (ECharts)
- Canvas renderer everywhere; dark theme matching §1.1 exactly.
- Series distinguished by hue **and** line style/marker (accessibility rule).
- Streaming charts: buffer 60–300s, downsample older, pause control mandatory, current-value readout beside every chart.
- Forecast/AI-derived series render dashed violet; actuals solid teal; baseline comparisons dashed gray.
- Every chart has: tooltip, keyboard-focusable summary, `prefers-reduced-motion` disables intro animations.

---

## 2. MOTION LANGUAGE & ANIMATION PRINCIPLES

### 2.1 Motion Tokens

| Token | Value | Use |
|---|---|---|
| `t-instant` | 100ms | State flips, toggles |
| `t-fast` | 200ms | Hover/press, chips |
| `t-base` | 320ms | Panel enter/exit, drawer |
| `t-slow` | 600ms | Large surface transitions |
| `t-cinematic` | 1200ms+ | Landing sequences, camera moves |
| `ease-exit` | `cubic-bezier(.16,1,.3,1)` (expo-out) | Default exits & reveals |
| `ease-io` | `cubic-bezier(.65,0,.35,1)` | Scrub-linked, symmetric moves |
| `ease-spring` | gentle overshoot (FM spring, dampening 18/6) | Small toggles only |
| `stagger` | 40ms/item, cap 8 items | Lists, card grids |
| `pulse-crit` | 2.4s breathing loop | Critical incidents only |

### 2.2 Animation Principles

1. **Motion carries meaning.** Something animates because state changed — never because the page is bored. Static data sits still.
2. **Data integrity.** Numbers do not ambiently re-tween. Count-ups only on user-triggered context switches (selecting a run, scrubbing). Ambient motion limited to: mission clock, critical pulse, particle flow.
3. **Camera is narrative.** Camera moves happen on story beats (landing) or explicit user action (follow-unit). Never idle-drifting in the command center — operators must trust spatial stability.
4. **One attention channel.** When a critical incident activates, non-essential motion system-wide dampens (particles slow, sparklines freeze) until acknowledged.
5. **Controlled urgency.** Urgency is a designed, bounded channel — never ambient chaos. Exactly three escalation instruments exist: (a) critical red pulse on the incident, (b) topbar mode/status chip, (c) ledger entry emphasis. Nothing else in the UI may escalate visually. Escalation always resolves to a clear terminal state (acknowledged / completed / failed); no perpetual alarm states. Urgency never overrides operator control — animations cannot block input, and the run launcher stays reachable during any emergency display.
6. **Exit faster than enter.**
7. **Interruptible everything.** No transition locks the UI; the run launcher is reachable within ≤1 click from any state.
8. **GPU-first.** Main thread does transform/opacity only; heavy work lives in the WebGL frame loop and ECharts canvas. Frame budget: 8ms JS.
9. **Honest latency.** Skeletons mirror final layout; any wait >400ms shows progress semantics (never an infinite naked spinner).
10. **Reduced-motion / reduced-audio are first-class.** Camera flythroughs become hard cuts; particles render as static field; pulses become steady borders; scroll acts snap without parallax. Tested explicitly.
11. **Glow is state, not style.** A glow appears only to mark live/critical/AI-active meaning. Headlines never glow.

### 2.3 Camera Stability Rules

The camera is an instrument. Operators build spatial memory of the city; gratuitous motion destroys trust.

| Rule | Specification |
|---|---|
| **No idle drift** | Command-center camera moves ONLY on explicit user input or an acknowledged story/demo beat. Zero autonomous motion at rest. |
| **Damped, deterministic easing** | All camera transitions use exponential damping (`lerp` factor ~`1 - e^(-dt·4)`); no springs, no overshoot, no shake — ever. |
| **Fixed focal grammar** | Three canonical framings only: `FIT` (whole city), `FOCUS` (district-level), `FOLLOW` (unit-locked). FOV is constant per framing; zoom happens via dolly, not FOV pumping. |
| **Follow disengages on input** | Any user drag/zoom breaks follow-mode immediately and predictably; a `RESUME FOLLOW` affordance appears, it never re-engages itself. |
| **Story beats are scoped** | Cinematic camera language exists ONLY on the landing page and in labeled DEMO playback. The live operational twin never plays director. |
| **Reduced motion** | All camera transitions become hard cuts between framings. |
| **Frame independence** | Camera math is delta-time based; identical behavior at 30/60/120fps. |

---

## 3. LANDING PAGE STORYBOARD — "THE CITY INTRODUCES ITSELF"

Total journey ~600vh. Act 0 plays automatically (~10–15s feel compressed into 3s); Acts 1–5 are **scroll-scrubbed** (GSAP ScrollTrigger, pin the shared WebGL canvas, snap points at act boundaries). One persistent canvas morphs across all acts — no page-long stack of separate sections.

**Global chrome during landing:** minimal top-left wordmark `AUREON`, top-right `[ ENTER COMMAND ]` ghost button + sound toggle. Progress rail on right edge: five ticks labeled `01 AWAKENING · 02 CITY · 03 PULSE · 04 DECISION · 05 COMMAND`.

### ACT 0 — SYSTEM AWAKENING (time-based, 0–3s, black → first light)

- Black. Mono telemetry types on, staggered:
  `AUREON` / `URBAN RESPONSE INTELLIGENCE`
  `> INITIALIZING CITY MODEL...`
  `BENGALURU 12.97°N 77.59°E`
  `NETWORK STATUS: CONNECTING ... LINKED`
  `DIGITAL TWIN: LOADING`
- A single titanium point blinks at Bangalore's coordinates — the seed of everything.
- **Audio concept (opt-in):** low sub drone (45Hz), distant filtered-noise siren swell (band-passed, reverberant — atmospheric, never alarm-like), soft telemetry ticks on each line reveal.
- Autoplay compliance: audio muted by default; `SOUND ON` affordance appears after first user gesture (browser policy honored); entire experience fully functional silent; both `prefers-reduced-motion` and mute persist to localStorage.
- `SKIP` button visible from 0.5s. On skip/complete → scroll unlocked at Act 1.

### ACT 1 — CITY MATERIALIZATION (scroll 0–25%)

- **Visual beats (scrub-linked):**
  1. Edges etch outward from the seed node along the road graph — copper-titanium traces, like a circuit board powering up (line-draw shader: `draw-range`/dash-offset driven by scroll progress).
  2. Nodes ignite in sequence: stations (teal), hospitals (titanium halo), district anchors (label fades: CBD, Whitefield, Electronic City, Hebbal…).
  3. Graticule + zone boundaries fade in beneath. Camera: top-down → 35° tilt (scrub-mapped dolly).
- **Copy overlay (left column, fades per beat):**
  `Every road. Every hospital. Every ambulance.` → `One living model of Bengaluru.` → `This is not a map. It is a twin.`
- Reduced-motion: single cut to fully materialized city; copy crossfades.

### ACT 2 — THE PULSE (scroll 25–45%)

- Traffic particles begin flowing along edges (density varies by congestion factor); six station units idle-pulse teal; hospital halos breathe gently with realistic occupancy skew.
- Sim clock starts ticking in the corner (`SIM 08:00:00`).
- **Copy:** `14 ambulances. 28 hospitals. 32 corridors.` → `Demand never stops arriving.` A faint Poisson ripple hints incidents forming in queue (subtle, pre-critical).
- Tech: instanced particle system, time-of-day tint shift (cool dawn → warm noon) driven by scroll.

### ACT 3 — THE DECISION (scroll 45–75%) — the emotional core

- **Beat 1:** Critical incident blooms at Koramangala — red ring, expanding pulse, world otherwise dims slightly (attention principle). Camera pushes toward it. Telemetry ticker: `INCIDENT C-1042 · MAJOR TRAUMA · ALS REQUIRED`.
- **Beat 2 — computation made visible:** violet scan sweeps the fleet; candidate units highlight with thin violet arcs to the incident; mono side-readouts evaluate: `ETA`, `CAPABILITY`, `COVERAGE IMPACT`, `HOSPITAL SUITABILITY`.
- **Beat 3 — the choice, staged honestly as a split:**

```
┌ NEAREST ──────────────┐   ┌ AUREON ────────────────────┐
│ AMB-03 · BLS          │   │ AMB-07 · ALS               │
│ ETA 4.2m ▲ fastest    │   │ ETA 4.8m  (+0.6m)          │
│ capability ✗          │   │ capability ✓ ALS match     │
│                       │   │ coverage preserved ✓       │
│                       │   │ hospital suitability 0.75  │
└───────────────────────┘   └────────────────────────────┘
```

  Nearest unit's gray route traces and stops; Aureon's teal route completes; a violet arc selects Aster CMI over a congested closer ER.
- **Verdict line fades in (display type):** *"The fastest response is not always the closest one."*
- Copy truthfulness rule: numbers shown must be *plausible values from the actual strategy vocabulary* (capability override within tolerance, coverage analyzer, suitability score) — the landing demo replays logic identical in spirit to `HybridAureonStrategy`, never magic.

### ACT 4 — EVIDENCE (scroll 75–90%)

- The Decision Ledger preview materializes as a floating card stack: three real-format entries (dispatch rationale, reason chips, hospital choice) — introducing the explainability system users will operate.
- Benchmark honesty chips (from Phase 6/7 reports — credibility through candor):
  `RESPONSE TIME — statistical parity with nearest-available`
  `CAPABILITY MATCH — +16.6pp under hospital congestion`
  `DESIGN GUARANTEE — bounded regression ceiling (≤1.5× nearest ETA)`
- **Copy:** `Every decision explains itself.` → `Measured. Audited. Honest.`

### ACT 5 — ENTRY (scroll 90–100%)

- City recedes to wide shot, dims to 30%; wordmark centers:
  `AUREON — URBAN INTELLIGENCE OPERATING SYSTEM`
- CTAs: `[ ENTER COMMAND CENTER ]` (solid teal) · `[ LAUNCH A SCENARIO ]` (ghost). Secondary line: `Digital twin · Adaptive dispatch · Explainable AI · Bengaluru`.
- Footer hairline: `SIMULATION ENGINE v0.1 · VALIDATED SEED 42 · 214 TESTS PASSING`.

**Scroll engineering:** pinned `<canvas>` behind transparent content sections; ScrollTrigger scrub=1 with act snapping; DOM overlays animate via FM/GSAP timelines bound to the same progress; deep-linkable act hashes; mobile fallback = vertical filmstrip (canvas scales down, beats remain, parallax removed).

---

## 4. COMMAND CENTER WIREFRAME (zero-scroll, full viewport)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ◉ 09:41:22 SIM │ MODE: NORMAL │ RUN: sim_4a2f ● RUNNING 62% │ ⏸ ⏭ 2× │ ◉ API │  TOPBAR 48px
├───────────────┬──────────────────────────────────────────────┬───────────────┤
│ LEFT 320px    │                                              │ RIGHT 360px   │
│               │            LIVING 3D CITY TWIN               │               │
│ INCIDENTS     │                                              │ // DECISION   │
│  ● C-1042 CRIT│      roads(titanium) congestion tint         │    LEDGER     │
│  ● C-1039 MOD │      units(teal) trails incidents(red)       │  feed, newest │
│  ○ queue (3)  │      hospital halos violet AI arcs           │  first; cards │
│───────────────│                                              │  expand →     │
│ FLEET 11/14   │         [camera: orbit / follow / fit]       │  INSPECTOR    │
│  AMB-07 ▶ en  │                                              │  selected:    │
│  AMB-03 ● idle│                                              │  entity meta, │
│  … rows       │                                              │  full rationale│
│───────────────│                                              │  raw JSON     │
│ HOSPITALS     │                                              │  toggle       │
│  Aster ▓▓▓░░  │                                              │               │
│  Vydehi ▓▓▓▓▓!│                                              │               │
├───────────────┴──────────────────────────────────────────────┴───────────────┤
│ TIMELINE 08:00━━━●━━━━━━━━━━09:30  markers ▮incidents ◆dispatches ▲admissions │  96px
│ METRICS  RT 4.6m │ P90 13.3m │ COMPLIANCE 71% │ CAP-MATCH 83% │ DIST 42km ▁▃▅ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Region Specs

| Region | Contents | Data source (today) |
|---|---|---|
| Topbar | Mission clock (`sim_time_formatted`), adaptive MODE badge (violet, only when reported), run selector + status chip, play/pause/speed (replay), API health dot (real `/health`) | `GET /simulation/{id}/state`, `/health` |
| Left: Incidents | Active incidents sorted severity-first; pending queue count orbit indicator; row click → select+camera focus | `active_incidents[]`, `pending_queue_count` |
| Left: Fleet | Grouped by status; capability tag ALS/BLS; missions completed; availability bar; click → follow-camera | `ambulances[]` |
| Left: Hospitals | Name + ER/ICU load bars (heat ramp), divert warning icon >80%, specialties on hover | `hospitals[]` occupancy strings |
| Center: Twin | Full WebGL scene (see §5 Twin components). Layers togglable: congestion tint / AI arcs / particles / labels | same state payload |
| Right: Decision Ledger | Chronological `DispatchCard`s: unit → incident, ETA gap chip, extracted reason chips (`nearest` / `capability override 8%` / `coverage fallback`), chosen hospital + suitability. Card click flashes involved entities on map + opens Inspector | `dispatch_log[].rationale` parsed into structured chips |
| Right: Inspector | Selected entity detail: ambulance (state timeline, odometer, current assignment), incident (timeline: reported→dispatched→arrived→hospital), hospital (occupancy history, specialties) | state payload + run result |
| Bottom: Timeline | Scrubbable sim-time axis built from run events; markers; playback speed; A/B toggle `BASELINE ⇄ AUREON` overlays paired persisted run | `GET /simulation/results/{id}` (persisted) |
| Bottom: Metrics strip | KPI chips + sparklines: mean/P90 RT, critical compliance, capability %, hospital suitability, fleet distance; click chip → expanded ECharts popover | `metrics.to_dict()` unwrapped correctly |

### State Matrix

| Mode | Trigger | Twin behavior | Panels |
|---|---|---|---|
| `IDLE` | fresh session | City at rest, ambient particles | Empty-state guidance ("Launch a scenario") |
| `LIVE` | run in progress, run-scoped state polling | Units move per tick, incidents bloom | Ledger streams; progress chip in topbar |
| `REPLAY` | open completed run from archive | Deterministic playback from stored events; scrubbable | Full panels; read-only |
| `DEMO` | one-click demo chip | **Deterministic showcase**: validated Seed 42 scenario set (Phase 7 scenarios A–H) replayed/run with pinned seed — identical outcome every time; camera beats allowed here only because it is labeled demo | Persistent `DEMO · SEED 42` chip; ledger highlights curated decisions (e.g., Scenario F capability override) |
| `COMPARE` | A/B toggle | Baseline ghost-units overlay aureon units | Metrics strip splits dual-series |

### 4.1 Demo Mode (Deterministic)

Trust requires reproducibility — every number shown on screen must be re-derivable.

- **Scenario source:** the validated Phase 7 scenario suite (`simulation/src/evaluation/phase7_scenarios.py`, scenarios A–H, seed 42, deterministic schedules).
- **Guarantees:** same seed + same schedule ⇒ identical incidents, dispatches, metrics, ledger entries. No randomness in presentation layer; no cherry-picking beyond what Phase 7 reports already document (including honest regressions like Scenario H).
- **Entry points:** landing Act 3 replays a recorded Seed 42 decision trace; command center offers `RUN DEMO` which executes scenario F (hospital congestion — the genuine differentiator) then E, labeled `DEMO · SEED 42`.
- **Exit:** any user interaction with run controls drops the demo label and switches to standard mode.

Keyboard: `Space` play/pause · `1/2/3` camera presets · `F` follow selection · `Esc` clear selection · `L` ledger focus. Responsive: ≥1440 full layout · 1024–1440 rails collapse to icon tabs · <1024 deferred (desktop-first tool, graceful stacked notice).

---

## 5. COMPONENT ARCHITECTURE

### Directory Plan

```
frontend/src/
├─ app/                      routes only (thin)
│   ├─ page.tsx             → Landing (cinematic scroll)
│   ├─ command/page.tsx     → Command Center shell
│   ├─ archive/page.tsx     → Runs archive (rebuilds /analytics)
│   └─ intelligence/page.tsx→ Strategy registry (rebuilds /models)
├─ design/
│   ├─ tokens.css           → §1 tokens (single source)
│   └─ theme/echarts.theme.ts
├─ components/
│   ├─ primitives/          Panel, StatChip, StatusDot, Badge, ReasonChip,
│   │                       TacticalButton, KeyHint, SkeletonBlock, Tooltip…
│   ├─ data/                MetricCard, Sparkline, LoadBar, GaugeBar,
│   │                       StreamingArea, DistributionChart, KpiStrip
│   ├─ twin/                TwinCanvas, GraphEdges, GraphNodes, DistrictLabels,
│   │                       UnitMeshes, IncidentRings, HospitalHalos,
│   │                       TrafficParticles, RouteTrails, AiArcs, CameraRig,
│   │                       SelectionFx, PostFx, ground-grid shader
│   ├─ landing/             AwakeningSequence, ScrollDirector, ActOverlays,
│   │                       AudioManager, ProgressRail
│   ├─ command/             TopBar, MissionClock, ModeBadge, IncidentQueuePanel,
│   │                       FleetPanel, HospitalPanel, DecisionLedger,
│   │                       DispatchCard, EntityInspector, TimelineScrubber,
│   │                       MetricsStrip, RunLauncherDialog, CompareToggle
│   └─ layout/              MarketingShell, CommandShell
├─ hooks/                   useHealthQuery, useCityState, useRunPolling (adaptive),
│                           useRunsList, useRunDetail, useDecisionFeed (rationale parser),
│                           usePlayback, useReducedMotion, useTwinAudio
├─ stores/                  twinStore (selection/camera/playback), uiStore (panels/modals)
├─ lib/                     api.ts (kept, extended), ws-adapter stub, geo.ts (latlng→scene),
│                           format.ts, rationale-parser.ts
└─ types/                   index.ts (kept, extended to full API contracts)
```

### Layering Rules
- `app/*` composes shells; pages contain no styling logic.
- `components/twin/*` are pure scene-graph consumers — they read `twinStore` + props, never fetch.
- All networking lives in hooks (TanStack Query); components subscribe to derived selectors only.
- Transport abstraction: `useRunPolling` wraps query fn so WebSocket can replace polling later without touching UI.
- `rationale-parser.ts` converts free-text `rationale` strings into `{decision, reasons[], hospital, scores}` — the Ledger renders structured chips with raw-string fallback.

### Existing Frontend Verdict (replace / rebuild / preserve)

| Asset | Verdict |
|---|---|
| `lib/api.ts`, `types/`, `constants.ts` | **Preserve + extend** (add run-status/state/archive endpoints, full metric types) |
| Token approach in `globals.css` | **Rebuild** contents per §1 (keep CSS-var mechanism) |
| `Navbar` (hardcoded "System Online") | **Rebuild** as `TopBar` with real health |
| `HeroSection`, `FeatureGrid`, `Footer` | **Replace** with Landing acts (§3) |
| `Scene3D` (decorative sphere, `@ts-nocheck`) | **Delete** — superseded by real twin |
| `SystemStatus` fake subsystem table | **Replace** with real `/health` + `/models` driven panel |
| `dashboard/page` | **Rebuild** as Command Center |
| `simulation/page` | Logic **preserve**, presentation rebuilt (`RunLauncherDialog` + progress) |
| `analytics/page` | **Rebuild** as Archive (clickable rows → replay) |
| `models/page` (static) | **Rebuild** wired to `/models` API |

---

## 6. REQUIRED DEPENDENCIES

| Package | Version dir. | Purpose |
|---|---|---|
| `three` | latest stable (pinned with R3F) | Twin runtime |
| `@react-three/fiber` | **^9** | React 19-compatible — removes `@ts-nocheck` hack |
| `@react-three/drei` | **^10** | Helpers (Html, Line, instances, easing) |
| `@react-three/postprocessing` | ^3 | Selective bloom (restrained) |
| `gsap` | ^3.12 (+ free ScrollTrigger) | Landing scroll direction, timelines |
| `lenis` | ^1 | Smooth scroll for landing only |
| `framer-motion` | ^12 (kept) | UI choreography |
| `zustand` | ^5 | Client UI state |
| `@tanstack/react-query` | ^5 | Server state + adaptive polling |
| `echarts` + `echarts-for-react` | ^5 | All charting (streaming/gauge/dist) |
| `@phosphor-icons/react` | ^2 | Icon system |
| Fonts via `next/font/google` | — | Space Grotesk, Inter, JetBrains Mono, IBM Plex Mono (self-hosted, zero CLS) |

Removals: nothing forced; drei usage from old Scene3D dies with the component.

---

## 7. BACKEND ENABLEMENT (honest scoping — flagged, not yet approved)

The audit found gaps that gate specific UX promises:

| ID | Finding | Required for | Proposal |
|---|---|---|---|
| **B1** | `/simulation/state` serves the *idle* default engine; background runs create separate engines — **no live state exists for a running run** | `LIVE` twin mode (§4) | Add `GET /simulation/{run_id}/state` snapshotting the active run's engine (registry already exists in service) |
| **B2** | Rate limiter (30 req/60s/path) kills 1 Hz status polling ≈30s into every run → UI currently reports false failures | Any polling UI | Exempt GET status/state from limiter or separate budget; keep POST protected |
| **B3** | Persisted results store only `dispatch_log[:15]` — Ledger/replay starved | Replay + Ledger depth | Raise persisted log cap (e.g., 500) |
| **B4** | `RunStore.delete_run()` exists but no route exposes it | Archive management | `DELETE /simulation/results/{run_id}` |
| **B5** | Known Phase 7 mode-tracking bug (batch dispatches don't record triggering mode) | MODE badge accuracy | Optional fix; badge hides gracefully meanwhile |

Client-side mitigations exist for B2 (adaptive backoff) but B1 has **no** client workaround — flagging as the single hard backend dependency of Phase 10.

---

## 8. IMPLEMENTATION ROADMAP (post-approval)

| Stage | Scope | Exit criteria (DoD) |
|---|---|---|
| **10A-BE Backend Enablement** | **B1 (`GET /simulation/{run_id}/state`) + B2 (rate-limit exemption for read-only polling) — shipped FIRST, before any frontend feature that depends on live simulation** | New endpoints tested; full backend suite green; 1 Hz polling survives indefinitely |
| **10A Foundations** | Deps + R3F v9 migration (delete ts-nocheck), token system, fonts, Query provider; fix: adaptive polling + limiter interplay, nested-metrics rendering, real health indicator | `npm run build && npm run lint && tsc --noEmit` clean; old routes still function |
| **10B Twin Core** | geo projection, GraphEdges/Nodes/Labels, CameraRig (per §2.3 stability rules), picking/selection, PostFx, perf budget | 60fps with full graph on M-class laptop; selection round-trip <100ms |
| **10C Landing Cinematic** | Awakening, materialization shaders, ScrollDirector (5 acts), AudioManager, deterministic Seed 42 demo trace for Act 3, reduced-motion paths | Acts scrub smoothly; LCP <2.5s; works silent & reduced-motion |
| **10D Command Shell** | TopBar, left-rail trio, Inspector, state matrix wiring, empty/loading/error states | All panels driven by live API; zero hardcoded status |
| **10E Intelligence Layer** | rationale-parser, DecisionLedger, TimelineScrubber, MetricsStrip (ECharts), REPLAY from persisted runs (+B3) | Replay fidelity: events align with stored metrics |
| **10F Live Runs & Compare** | RunLauncher in-command, run-scoped polling (consumes B1), live unit animation, BASELINE⇄AUREON compare overlay (+B4 archive mgmt), DEMO mode chip, a11y & perf audit | Full loop: launch → watch live → inspect ledger → replay → demo → compare |

Sequencing note: **10A-BE gates 10F** (and any live-twin work). 10A–10C and 10D are independent tracks; 10E depends on 10B+10D.

---

*Prepared for review. Implementation begins only after explicit approval of this blueprint.*
