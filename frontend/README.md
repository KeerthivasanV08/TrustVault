# TrustVault — AML Operations Console

> Real-time Anti–Money-Laundering intelligence platform for fraud analysts, investigators, compliance officers, and banking risk teams.

A dark-themed, investigation-driven, operationally actionable AML war-room console — inspired by Feedzai, Unit21, Chainalysis, Stripe Radar, and enterprise SOC dashboards.

---

## ✨ Highlights

- **10 production-grade pages** — Command Center, Transaction Monitor, Alert Center, Graph Explorer, Officer Review, Cases, Reports, Account 360, Investigation Sandbox, Settings
- **Backend-driven realtime** — transactions, alerts, threat feed, SLA timers, queue movement stream from FastAPI SSE endpoints
- **Runtime health strip** — compact backend/model/Neo4j/SSE status in the header for demo readiness
- **Enterprise design system** — semantic OKLCH tokens, glassmorphism panels, terminal-grade typography, glow/pulse motion for critical states
- **Explainability built-in** — model contribution bars (Behavioral / Sequence / Graph / Rules) + decision timeline, surfaced in alerts, txns, officer review, cases
- **Operational workflows** — acknowledge, escalate, freeze, SAR, assign, close — all wired with toast feedback
- **Graph investigation** — interactive SVG cluster graph with risk filtering, propagation pulses, node inspection
- **No mock AML data** — all operational pages consume normalized backend API responses and SSE cache merges

---

## 🧱 Tech Stack

| Layer | Tool |
|---|---|
| Framework | TanStack Start (React 19) |
| Routing | TanStack Router (file-based) |
| Styling | Tailwind CSS v4 + custom design tokens |
| Charts | Recharts |
| State | Lightweight pub/sub store (`src/store/realtime.ts`) + SSE merge cache |
| Data fetching | TanStack Query v5 + normalized backend API client |
| Toasts | Sonner |
| Icons | Lucide React |
| Type safety | TypeScript strict |

---

## 📁 Folder Structure

```
src/
├── routes/                        # File-based routes
│   ├── __root.tsx                 # Shell: sidebar + header + right rail + Outlet
│   ├── index.tsx                  # /                 Command Center Dashboard
│   ├── transaction-flow.tsx       # /transaction-flow Transaction Intelligence Terminal
│   ├── alerts.tsx                 # /alerts           Alert Center
│   ├── graph.tsx                  # /graph            Graph Explorer
│   ├── officer-review.tsx         # /officer-review   Officer Review Workbench
│   ├── cases.tsx                  # /cases            Case Management
│   ├── reports.tsx                # /reports          Reports & Audit
│   ├── accounts.tsx               # /accounts         Account 360
│   ├── investigation.tsx          # /investigation    Investigation Sandbox
│   └── settings.tsx               # /settings         Console Settings
├── components/
│   └── aml/
│       ├── Sidebar.tsx            # Left nav with P1 badge
│       ├── Header.tsx             # Top bar: search, metrics, SSE status, officer
│       ├── Panel.tsx              # Glass panel + StatCard primitive
│       ├── Badges.tsx             # PriorityBadge, RiskScoreBadge, StatusBadge, DecisionBadge
│       ├── SLATimer.tsx           # Live countdown with breach pulse
│       ├── RealtimeThreatFeed.tsx # Streaming ticker
│       └── ExplainabilityPanel.tsx# Model contribution + decision timeline
├── store/
│   └── realtime.ts                # SSE-backed pub/sub store + live cache merge
└── styles.css                     # Design tokens + utility classes
```

---

## 🎨 Design System

Defined in `src/styles.css` using OKLCH for perceptual uniformity:

| Token | Use |
|---|---|
| `--background` `oklch(0.16 0.015 250)` | App background (near-black, slight blue) |
| `--primary` `oklch(0.7 0.18 240)` | Electric blue accents, links, selection |
| `--critical` `oklch(0.62 0.24 22)` | P1 alerts, blocks, SLA breach |
| `--warning` `oklch(0.78 0.17 75)` | Amber — review queue, escalation pending |
| `--success` `oklch(0.72 0.17 160)` | Closed, allowed, connection live |
| `--panel` / `--panel-border` | Glassmorphism surfaces |
| `--grid-line` | Subtle background grid texture |

**Utility classes:** `.grid-bg`, `.glass-panel`, `.mono`, `.pulse-critical`, `.pulse-dot`, `.row-enter`, `.scan-line`, `.glow-blue|red|amber`.

All components reference semantic tokens — **never** hard-coded colors.

---

## 🔴 Realtime Engine

`src/store/realtime.ts` holds the live operational state while `src/services/sse/transactionStream.ts` and `src/services/sse/alertStream.ts` connect to the backend SSE endpoints.

- `GET /api/transactions/realtime` streams transaction events.
- `GET /api/alerts/realtime` streams alert and queue events.
- `src/routes/__root.tsx` merges those events into both the realtime store and the TanStack Query cache.

Components subscribe via `useStore(selector)` — only re-render when their slice changes. The `PAUSE` toggle in the header freezes local view updates without fabricating new AML data.

---

## 🧠 Explainability

The `ExplainabilityPanel` is the operational core, surfaced everywhere a risk decision exists:

- Final risk score + decision chip
- 4 model contribution bars: **Behavioral · Sequence · Graph · Rules**
- Per-model triggered signal chips
- Decision timeline (T+0ms → T+18ms) showing how the scoring pipeline reached its verdict

Used in: Transaction drawer, Alert drawer, Officer Review center column.

---

## 📄 Page Tour

### 1. Command Center (`/`)
8 KPI tiles (Txn, Blocked, Review, P1, Cases, SAR, Mules, Network risk), risk/alert trend area chart, risk distribution donut, channel risk stacked bars, fraud heatmap (7×24), live transaction stream, active investigations list.

### 2. Transaction Monitor (`/transaction-flow`)
Bloomberg-style terminal — 12-column table with Behavioral / Sequence / Graph sub-scores, signal chips, risk-tier row tinting, range filter for min risk, pause control, click-to-open detail drawer with full explainability.

### 3. Alert Center (`/alerts`)
Queue-tab nav (ALL / P1 / ESCALATED / EDD / GENERAL), inline SLA countdown with breach pulse, 5 quick-action icons per row (Ack, Escalate, Freeze, SAR, Close), drawer with explainability.

### 4. Graph Explorer (`/graph`)
3-column layout — filter panel (node type + risk slider + metrics) · interactive SVG graph built from the latest 25 SSE transactions, propagation pulse animation, type-color legend · cluster summary with selected-node intel.

### 5. Officer Review (`/officer-review`)
True 3-column workbench: Left = queues + queue list. Center = investigation card + evidence timeline + explainability. Right = 6 operational action buttons + linked alerts. All actions trigger toast feedback.

### 6. Case Management (`/cases`)
Case registry with priority, linked alert count, officer, SLA, escalation level. Drawer shows investigation timeline + audit trail.

### 7. Reports & Audit (`/reports`)
SAR/STR KPIs, officer workload bar chart, risk distribution donut, 30-day audit log with export buttons (JSON / CSV / PDF).

### 8. Account 360 (`/accounts`)
Searchable directory with tier filter · profile panel with sanctions/PEP chips · risk intelligence bars (Device / Onboarding / Graph / SIM / VPN / Suspicious-30d) · onboarding explainability signals · suspicious relationships list.

### 9. Investigation Sandbox (`/investigation`)
Side-by-side entity comparison · shared signal matching grid · Venn-diagram graph overlap · transaction overlap list.

### 10. Settings (`/settings`)
Local UI preferences for risk threshold sliders (Review / Block), auto-escalation toggles, queue ordering (FIFO / RISK_DESC / SLA_ASC), realtime preferences, notification channels, session info.

---

## 🧩 Reusable AML Components

| Component | Purpose |
|---|---|
| `PriorityBadge` | P1/P2/P3 chip — P1 pulses critical |
| `RiskScoreBadge` | Color-graded score chip (success/info/warning/critical bands) |
| `StatusBadge` | Generic status chip (OPEN/ACK/ESCALATED/CLOSED/SAR_FILED/…) |
| `DecisionBadge` | ALLOW / REVIEW / BLOCK chip |
| `SLATimer` | Live HH:MM:SS countdown — urgent at <5m, pulses red after breach |
| `Panel` / `StatCard` | Glass panel + KPI tile primitives |
| `RealtimeThreatFeed` | Streaming ticker with level-coded entries |
| `ExplainabilityPanel` | Model contribution + signals + decision timeline |
| `Sidebar` / `Header` | Shell chrome with live SSE & P1 indicators |

---

## ▶️ Running

```bash
bun install     # already installed in this template
bun run dev     # http://localhost:5173
bun run build   # production build
```

Routes auto-register from `src/routes/` — do **not** edit `src/routeTree.gen.ts`.

---

## 🛡️ Mock Data

There is no production mock AML dataset in this frontend. Operational pages normalize backend responses from the FastAPI APIs and render empty/error states when the backend is unavailable.

---

## 🔌 Extending

- **Add a new backend endpoint** — add a client in `src/services/api/`, normalize the response, then wire it into a page hook.
- **Add a page** — drop a file in `src/routes/`, add to the `NAV` array in `Sidebar.tsx`.
- **Add a metric tile** — extend `state.metrics` in the store, render with `<StatCard />`.
- **New badge tone** — extend `Badges.tsx` switch; tokens already exist.

---

## 📐 Design Principles Followed

✅ Dense but readable · ✅ realtime indicators everywhere · ✅ investigation-first workflows · ✅ semantic tokens only · ✅ glow/pulse only on critical states · ✅ mono typography for IDs and metrics · ✅ no empty states, no marketing fluff.

Built for analysts who live in the console all day.
