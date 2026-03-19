# Plan: OotoCV Frontend Rebuild

**Status:** 🟡 In Progress
**Created:** 2026-03-19
**Branch:** feature/ootocv-build
**Spec source:** `references/ootocv_src 2/ootocv_frontend_spec.docx`

## Goal

Rebuild the TailorAI frontend to match the OotoCV frontend spec — a dark, opinionated, personality-driven UI with verdict-conditional layouts, 4 distinct card formats, a sidebar shell, and a complete design system. Done looks like: every section of the spec (1–13) is implemented, the app compiles, and a user can navigate Feed → Detail → Tailor Review → Tracker with the correct layout/copy/animation for each verdict type. Backend/API layer is already built (phases 1–5); this work is purely frontend.

## Decisions Made

- **Incremental rebuild over greenfield**: Reuse existing hooks (`useJobs`, `useSSE`, `useResumeState`, `useJobSelection`), `apiClient.ts`, `types.ts`, and `utils/`. Replace component layer and styling.
- **Tailwind v4 + @theme**: Spec mandates CSS custom properties via `@theme` block, not Tailwind v3 config. Must install `@tailwindcss/vite` plugin.
- **No pages/ directory**: Spec uses `src/pages/` (Dashboard, JobDetail, TailoringReview, ApplicationTracker, SetupPage) + `src/components/` for shared pieces. Adopt this structure.
- **React Router v6**: Spec uses `BrowserRouter` + `Routes`. Current app uses hash-based `ViewMode` state. Migrate to proper routing.
- **motion/react (Framer Motion v11+)**: Required for card entrance, stagger, typewriter cursor, cron message fade, confetti button scale.
- **Preserve existing backend contract**: All API endpoints stay the same. Only frontend changes.
- **Phase ordering**: Foundation first (deps, design system, shell), then build outward (feed → detail → review → tracker → settings).

## Open Questions

- [x] Backend stubs vs build? → **Stick with what we have.** Note missing endpoints in a "Backend Gaps" section; don't build them in this plan.
- [x] Old component migration strategy? → **Build new alongside old, don't delete upfront.** Note what's gone outdated; clean up in Phase 8.
- [x] Ghost commentary? → **LLM + mapping based.** Evaluation process contributes ghost commentary during eval. Backend work — tracked in Backend Gaps, not this plan.
- [x] `src/data/jobs.ts` vs current `types.ts`? → **Keep current `types.ts` + `apiClient.ts` pattern.** Spec's `data/jobs.ts` was for its own mock setup; we have real API data. Extend `types.ts` with new types (Strength, Gap, VerdictType, etc.) as needed.

## Out of Scope

- Building new backend endpoints (tracked in Backend Gaps below — frontend stubs/skips where needed)
- Mobile responsive layout (spec says "below 1100px collapses" — implement later as polish)
- Gmail OAuth flow (requires backend OAuth endpoints not yet built)
- `prefers-reduced-motion` for confetti (spec explicitly defers to polish)
- Google Drive push integration (spec mentions it but backend not ready)

## Backend Gaps (needed eventually, not in this plan)

These endpoints are referenced by the spec but don't exist yet. Frontend should degrade gracefully (skip the UI element or use placeholder data).

| Endpoint | Used by | Frontend fallback |
|----------|---------|-------------------|
| `GET /system/status` → `{ configured: bool }` | Onboarding gate (App.tsx) | Default to `configured: true` (skip onboarding gate for now) |
| `GET /cron/status` → `{ state, next_run, last_message }` | Sidebar cron indicator | Hardcode `sleeping` state, hide "Next run" |
| `PATCH /pipeline/config` → stage mode toggles | Feed pipeline control | Render pills as read-only display, no toggle |
| `POST /settings/validate` → API key validation | SetupPage onBlur | Skip validation, just save |
| `POST /applications/sync` (Gmail) | Tracker Gmail sync button | Hide button until endpoint exists |
| Ghost commentary field on `GET /applications` | Tracker ghost text | Show days-since-applied fallback text client-side |
| `PATCH /runs/:run_id` (cancel) | TailoringStrip cancel | Hide cancel button until endpoint exists |

## Outdated Components (to remove in Phase 8)

These will be superseded by new pages/components. Keep them around during build so the app still works on the old routes. Delete once new equivalents are wired.

| Old component | Replaced by |
|---------------|-------------|
| `Header.tsx` | `Sidebar.tsx` |
| `FilterBar.tsx` | Feed header verdict pills in `Dashboard.tsx` |
| `StatsCard.tsx` | Feed header count pills |
| `JobListPanel.tsx` + `JobListItem.tsx` | `Dashboard.tsx` with 4 card format components |
| `JobCard.tsx` | Verdict-specific card components in `Dashboard.tsx` |
| `JobDetailView.tsx` (40KB) | `src/pages/JobDetail.tsx` (verdict-conditional) |
| `ApplicationTracker.tsx` | `src/pages/ApplicationTracker.tsx` |
| `Onboarding.tsx` | `src/pages/SetupPage.tsx` with `isOnboarding` prop |
| `Pagination.tsx` | Infinite scroll only (no pagination) |
| `GlassCard.tsx` | Not needed (no glass/blur in spec) |
| `BatchEvaluate.tsx` | Pipeline control in feed header |

---

## Implementation Checklist

### Phase 0: Dependencies & Build Setup
- [ ] Install Tailwind v4: `@tailwindcss/vite` plugin + `tailwindcss` package
- [ ] Install `motion` (Framer Motion v11+ — imported as `motion/react`)
- [ ] Install `react-router-dom` v6
- [ ] Install `canvas-confetti` + `@types/canvas-confetti`
- [ ] Install `clsx` + `tailwind-merge` (spec utility: `cn()` helper)
- [ ] Add Google Fonts (DM Sans variable + DM Mono 300/400/500) to `index.html` or CSS `@import`
- [ ] Update `vite.config.ts` with `@tailwindcss/vite` plugin
- [ ] Create `src/index.css` with `@import 'tailwindcss'` + `@theme` block (all color tokens from spec §1.1)
- [ ] Add `@keyframes pulseSlow` and animation utilities to index.css (spec §1.4)
- [ ] Create `src/lib/utils.ts` with `cn()` helper (clsx + twMerge)
- [ ] Verify build compiles with `npm run build`

### Phase 1: App Shell & Sidebar (spec §3, §4)
- [ ] Create `src/components/Sidebar.tsx` — three-circle SVG logo with `isolation: isolate` + `mix-blend-mode: screen`, nav items (Feed/Tracker/Settings), cron status indicator, actionable badge
- [ ] Create `CronIndicator` sub-component — dot (active/sleeping/error), rotating messages with `AnimatePresence`, hover reveal
- [ ] Restructure `App.tsx` — horizontal flex shell: `Sidebar (w-64)` + main wrapper (`FeedPane + DetailPane` side-by-side + `TailoringStrip` below)
- [ ] Add `BrowserRouter` + `Routes`: `/` (feed+detail), `/tracker`, `/settings`, `/onboarding`, `/tailoring/:id`
- [ ] Wire global state: `tailoringJob`, `actionableBadge`, `isConfigured`, `selectedJobId`
- [ ] Implement `isConfigured` check: `GET /system/status` on mount → redirect to `/onboarding` if false

### Phase 2: Feed Pane — Header & Cards (spec §5)
- [ ] Create `src/pages/Dashboard.tsx` — feed pane container (w-80, border-r, flex-col)
- [ ] Feed header: sticky, pulse dot, "Today's run" label, run time, "Next run in Xh Ym", count pills (TAILOR/APPLY DIRECT/BORDERLINE as toggle filters)
- [ ] Pipeline control row: 3-stage toggle pills (Scrape/Evaluate/Tailor) with auto/manual states
- [ ] Run separators: temporal grouping ("Today · 5:00 PM", "Yesterday · all done") with pending action counts
- [ ] **TAILOR card** (full weight): verdict block with `border-l-2 border-semantic-green/50`, signal dots row, "Lead with →" strength line, quick actions on hover (Skip + Tailor & Approve)
- [ ] **APPLY DIRECT card** (slim ~44px): single-row, role + company + italic take + "Apply →" accent pill
- [ ] **BORDERLINE card** (medium): verdict block with amber border, "deciding factor" chip row, no match dots
- [ ] **SKIP card** (micro ~30px): opacity-38, red accent bar, role + kill shot + SKIP badge, collapsed by default with "N hard passes hidden — show them?" expand toggle
- [ ] Card entrance animations: `motion.div` initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }}
- [ ] Feed sections order: Action Required (TAILOR + APPLY DIRECT interleaved) → Your Call (BORDERLINE) → Hard Passes (SKIP collapsed)
- [ ] Actioned cards: render dimmed (opacity-30) after their section, not removed
- [ ] Infinite scroll: preserve existing `useJobs` sentinel/observer pattern, adapt for new card components
- [ ] Verdict filter pills: client-side toggle, multiple active, URL param sync (`?verdict=TAILOR,BORDERLINE`)

### Phase 3: Detail Pane — Verdict-Conditional Layout (spec §6)
- [ ] Create `src/pages/JobDetail.tsx` — verdict-conditional section ordering
- [ ] **Hero section**: company row (logo placeholder + name + stage/size + Glassdoor), role title (22px bold), tags row, verdict block with typewriter (30ms/char, first-open only via `hasLoaded` ref)
- [ ] **MatchBrief component** (`src/components/MatchBrief.tsx`): signal dots, "Lead with these" strengths (req met/evidence/signal chips, stagger 80ms), "Handle these" gaps (minor/notable/significant chips + strategy lines)
- [ ] **The Job section**: two-column grid ("What you'd actually do" + "What they actually need"), Must/Nice/Ignore prefixes, "What they won't tell you" red flag items
- [ ] **Company Intel section**: 3-column grid (Glassdoor, team size, stage, role age, hiring pace, remote), intel summary with accent arrow
- [ ] **CV Diff section**: intent state (pre-tailor) or diff state (post-tailor) with original→tailored→reason per change
- [ ] **Sticky CTA footer**: hype copy (TAILOR only), Skip button, Original JD button, primary CTA varies by verdict:
  - TAILOR: "Tailor & Approve →" / "Review & Send →"
  - BORDERLINE: two equal buttons ("Tailor Anyway" + "Skip This One")
  - APPLY DIRECT: "Apply Direct →" only, full width
  - SKIP: "Override & Tailor" in ghost style
- [ ] **TAILOR detail order**: Hero → Brief → Job → Intel → CV Diff → CTA
- [ ] **BORDERLINE detail order**: Hero → Deciding Factor (prominent) → Brief → Job → Intel → CTA
- [ ] **APPLY DIRECT detail order**: Hero → Job (condensed, 3 lines) → Intel → CTA
- [ ] **SKIP detail order**: Hero → Kill Shot (prominent, red) → Job (muted, opacity-50) → Red Flags → CTA
- [ ] Verdict typewriter: 30ms/char on first open, `hasLoaded` ref per jobId, instant on revisit

### Phase 4: TailoringStrip & Tailoring Review (spec §7, §8)
- [ ] Create `src/components/TailoringStrip.tsx` — bottom bar (border-t, bg-surface, in-flow not fixed), job context left, divider, compact TypewriterWaitState, cancel button
- [ ] Adapt `TypewriterWaitState.tsx` — add `compact` prop (single line, no history), ensure all 3 bug fixes preserved (timer leak, onComplete ref, messages ref)
- [ ] SSE connection in TailoringStrip: messages from `/runs/:run_id/stream`, `onComplete` navigates to `/tailoring/:id`
- [ ] Cron announcement mode: pulse dot + "Run complete · time · N jobs · N ready" + "Review now →", auto-dismiss 8s
- [ ] Create `src/pages/TailoringReview.tsx` — full page (not split pane), max-w-4xl mx-auto
  - Header: role + company, tailoring metadata, overall confidence
  - Change items: section label, original (strikethrough), tailored, reason (accent arrow), confidence-based left border (amber < 0.6, green >= 0.6)
  - Accept/Reject buttons per change, reject → inline feedback prompt (3 chips: "Too formal" / "Not accurate" / "Other") → PATCH + regenerate
  - Cover letter preview below changes
  - Sticky approve footer: "N accepted · N pending · N rejected", Skip button, "Approve & Send →" with confetti hype moment
- [ ] `canvas-confetti` integration: burst from approve button, button scale-95→100, total < 600ms

### Phase 5: Application Tracker (spec §9)
- [ ] Create `src/pages/ApplicationTracker.tsx` — full page, max-w-3xl mx-auto
- [ ] Page header: "Applications" h1, subtext "N applied · N in progress · N ghosting"
- [ ] Application cards: border border-white/5 bg-surface rounded-xl p-5, three-column (job info / status / ghost commentary)
- [ ] Status badges: applied (green), ghosting (amber), replied (teal), interview (accent), rejected (red), offer (green pulse)
- [ ] Ghost commentary: font-mono italic right-aligned, server-generated (stub with static strings until backend ready)
- [ ] Status override: dropdown on badge click, fires PATCH `/applications/:id`
- [ ] Gmail sync button: top right, ghost style, POST `/applications/sync` (stub until backend OAuth ready)
- [ ] Empty state: "No applications yet. That changes today."

### Phase 6: Settings & Onboarding (spec §11)
- [ ] Create `src/pages/SetupPage.tsx` with `isOnboarding: boolean` prop
- [ ] Onboarding layout: full page, no sidebar, centered, max-w-lg, hype first-line copy, progress steps
- [ ] Settings layout: standard page with sidebar, all fields visible at once
- [ ] Fields: OpenRouter API key (validate on blur), Apify API key (validate on blur), Google Drive OAuth button, Gmail OAuth button, base CV upload (.pdf/.json), job source checkboxes, cron time picker
- [ ] First-run copy: "Let's be real. Job hunting is awful..." (spec §2.9)
- [ ] Route `/onboarding` → `isOnboarding=true`, `/settings` → `isOnboarding=false`
- [ ] `isConfigured` gate in App.tsx: fetch `/system/status`, redirect to onboarding if false

### Phase 7: Voice, Copy & Polish (spec §2, §13)
- [ ] Wire verdict reasons/takes from API data (not hardcoded) — ensure font-mono rendering, no quotes, no italic
- [ ] Red flag format: split on em dash, bold label + muted explanation
- [ ] Strategy lines: font-mono, accent arrow prefix
- [ ] Empty states: feed empty, all actioned, tracker empty (spec §2.6 copy)
- [ ] Error states: API error, cron failed, Drive push failed (spec §2.7 copy)
- [ ] Hype CTA copy: per-job, context-aware (spec §2.8)
- [ ] Audit all `bg-accent` buttons use `text-[#0d0d0d]` not `text-base` (spec §13 known bug)
- [ ] Audit semantic colors are -400 level, not pastel (spec §13 known bug)
- [ ] Audit logo SVG has `isolation: isolate` (spec §13 known bug)
- [ ] No shadows, no blur, no gradients anywhere (spec §1.5)

### Phase 8: Cleanup & Migration
- [ ] Remove old components no longer used: `Header.tsx`, `FilterBar.tsx`, `StatsCard.tsx`, `JobListPanel.tsx`, `JobListItem.tsx`, `JobCard.tsx`, `Pagination.tsx`, `GlassCard.tsx`, `BatchEvaluate.tsx`
- [ ] Remove old `JobDetailView.tsx` (replaced by `src/pages/JobDetail.tsx`)
- [ ] Remove old `ApplicationTracker.tsx`, `Onboarding.tsx` (replaced by pages/)
- [ ] Update `glassresumatch-ai/CLAUDE.md` to reflect new component/page structure
- [ ] Update root `CLAUDE.md` active tasks list
- [ ] Verify all existing functionality still works: job feed, detail, tailor review, tracker, onboarding
- [ ] Run `npm run build` — zero errors

### Backend
No backend work in this plan. See "Backend Gaps" section above for what's needed eventually.

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Plan created. Current frontend has 0 of the spec's core dependencies (no Tailwind, no Framer Motion, no React Router, no canvas-confetti). Hooks and apiClient are solid and reusable. Estimated 8 phases.
