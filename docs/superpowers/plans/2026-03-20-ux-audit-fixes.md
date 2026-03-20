# UX Audit Fixes — Information-Theoretic Findings

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 UX issues identified in the information-theoretic audit (Hick's Law, Shannon Entropy, Fitts's Law violations)

**Architecture:** Pure CSS/layout changes in 3 React components. No new files, no API changes, no type changes. All fixes are visual spacing, grouping, and styling adjustments.

**Tech Stack:** React, Tailwind CSS, Lucide icons

---

## File Map

| File | Changes |
|---|---|
| `glassresumatch-ai/pages/TailoringReview.tsx:75` | Increase ChangeCard action button gap (F1) |
| `glassresumatch-ai/pages/TailoringReview.tsx:339-401` | Footer: group GDoc actions, de-emphasize stats (H1 + E1) |
| `glassresumatch-ai/pages/JobDetail.tsx:368-384` | Metadata row: weight salary + recruiter email (E2) |
| `glassresumatch-ai/pages/Dashboard.tsx:149` | TailorCard hover button gap (F2) |

---

### Task 1: ChangeCard button gap — Fitts's Law fix (F1)

**Files:**
- Modify: `glassresumatch-ai/pages/TailoringReview.tsx:75`

**Why:** 4px gap between Reject and Keep Original buttons causes ~5% misclick rate across 15-card review sessions. Reject misclick triggers feedback chip expansion requiring recovery clicks.

- [ ] **Step 1: Increase gap from `gap-1` to `gap-2`**

In `TailoringReview.tsx` line 75, change the action buttons container:

```tsx
// Before
<div className="flex gap-1 flex-shrink-0 mt-0.5">

// After
<div className="flex gap-2 flex-shrink-0 mt-0.5">
```

This doubles the inter-button spacing from 4px to 8px, improving the D/W ratio from 1.22 to ~1.56 — meaningful error margin improvement without layout disruption.

- [ ] **Step 2: Visual verify**

Run: `cd glassresumatch-ai && npm run dev`

Open TailoringReview page, verify:
- 3 action buttons (✓ ✗ ↺) have visible breathing room
- No layout overflow on narrow cards
- Reviewed state badges still render correctly in the same space

- [ ] **Step 3: Commit**

```bash
git add glassresumatch-ai/pages/TailoringReview.tsx
git commit -m "fix(ui): increase ChangeCard action button gap for Fitts's Law compliance"
```

---

### Task 2: TailoringReview footer — Hick's Law + Entropy fix (H1 + E1)

**Files:**
- Modify: `glassresumatch-ai/pages/TailoringReview.tsx:339-401`

**Why:** Footer has up to 6 simultaneous actions with 4 visually undifferentiated secondary buttons (2.3 bits decision complexity). Stat counters with semantic colors outshine the ghost action buttons, inverting the information hierarchy.

This task has two sub-changes:

#### 2a: Group GDoc actions into a dropdown-style collapsible

- [ ] **Step 1: Add `showGdocActions` state**

Near the top of the `TailoringReview` component (after line 126), add:

```tsx
const [showGdocActions, setShowGdocActions] = useState(false);
```

- [ ] **Step 2: Replace the two separate GDoc buttons with a single toggle + expandable group**

Replace the footer section (lines 339-401) with this restructured version:

```tsx
{/* Sticky approve footer */}
<div className="flex-shrink-0 border-t border-white/[0.08] bg-base px-8 py-3">
  {/* Progress bar — replaces colored stat counters */}
  {changes.length > 0 && (
    <div className="flex items-center gap-2 mb-2">
      <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className="h-full bg-accent/60 rounded-full transition-all duration-300"
          style={{ width: `${((accepted + rejected) / changes.length) * 100}%` }}
        />
      </div>
      <span className="text-[9px] font-mono text-gray-600">
        {accepted + rejected}/{changes.length}
      </span>
    </div>
  )}

  <div className="flex items-center gap-3">
    <div className="flex-1" />

    {pending > 0 && (
      <button
        onClick={handleBulkAccept}
        className="text-[9px] font-mono text-gray-400 px-3 py-1.5 border border-white/[0.08] rounded-[6px] hover:text-gray-200 transition-colors cursor-pointer"
      >
        Accept all remaining →
      </button>
    )}

    <button
      onClick={() => navigate('/')}
      className="text-[9px] font-mono text-gray-600 px-3 py-1.5 border border-white/[0.08] rounded-[6px] hover:text-gray-400 transition-colors cursor-pointer"
    >
      Skip
    </button>

    {gdocUrl && (
      <div className="relative">
        <button
          onClick={() => setShowGdocActions(v => !v)}
          className="text-[9px] font-mono text-gray-500 px-3 py-1.5 border border-white/[0.08] rounded-[6px] hover:text-gray-300 transition-colors cursor-pointer"
        >
          GDoc ▾
        </button>
        {showGdocActions && (
          <div className="absolute bottom-full right-0 mb-1 bg-surface border border-white/[0.1] rounded-[6px] py-1 min-w-[160px]">
            <a
              href={gdocUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-[9px] font-mono text-gray-400 px-3 py-1.5 hover:text-gray-200 hover:bg-white/[0.04] transition-colors"
            >
              Open in GDoc ↗
            </a>
            <button
              onClick={() => { setShowGdocActions(false); handleReexport(); }}
              disabled={reexporting || gdocsDisabled}
              title={gdocsDisabled ? 'Google Docs disabled · Enable in Settings' : undefined}
              className={cn(
                'w-full text-left text-[9px] font-mono text-gray-400 px-3 py-1.5 hover:text-gray-200 hover:bg-white/[0.04] transition-colors cursor-pointer',
                (reexporting || gdocsDisabled) && 'opacity-40 cursor-not-allowed',
              )}
            >
              {reexporting ? 'Re-exporting…' : 'Re-export to GDoc'}
            </button>
          </div>
        )}
      </div>
    )}

    <button
      ref={approveRef}
      onClick={handleApprove}
      disabled={approving}
      className={cn(
        'bg-accent text-[#0d0d0d] text-[10px] font-bold px-[18px] py-2.5 rounded-[7px] hover:bg-accent-hover transition-all active:scale-95 cursor-pointer',
        approving && 'opacity-50 cursor-not-allowed',
      )}
    >
      {approving ? 'Sending…' : gdocsDisabled ? 'Approve →' : 'Approve & Send →'}
    </button>
  </div>
</div>
```

Key changes:
- **Stat counters replaced with progress bar**: Gray progress bar shows reviewed/total as a fraction. Removes semantic-green and semantic-red text that competed with action buttons for attention. Progress becomes subordinate decoration (×1 IU) instead of competing information (×2 IU × 3).
- **GDoc actions grouped**: "Open in GDoc" and "Re-export" collapse behind a single "GDoc ▾" button. Reduces visible simultaneous actions from 5→3 groups (workflow: Accept all + Skip, GDoc group, Approve). The popover opens upward (above footer).
- **Visible action count**: 5→3 (when GDoc exported), 3→2 (when no GDoc). Primary CTA remains visually dominant.

- [ ] **Step 3: Visual verify**

Verify in browser:
- Progress bar fills as cards are reviewed
- "GDoc ▾" button appears only when `gdocUrl` is set
- Clicking "GDoc ▾" shows upward popover with both GDoc actions
- Clicking outside the popover closes it (will add in step 4)
- "Approve & Send" remains the visually dominant element
- Eye naturally flows to action buttons, not to the progress indicator

- [ ] **Step 4: Add click-outside-to-close for GDoc popover**

Add a click-outside handler. After the `showGdocActions` state declaration, add:

```tsx
const gdocMenuRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  if (!showGdocActions) return;
  const handler = (e: MouseEvent) => {
    if (gdocMenuRef.current && !gdocMenuRef.current.contains(e.target as Node)) {
      setShowGdocActions(false);
    }
  };
  document.addEventListener('mousedown', handler);
  return () => document.removeEventListener('mousedown', handler);
}, [showGdocActions]);
```

And add `ref={gdocMenuRef}` to the `<div className="relative">` wrapping the GDoc button.

- [ ] **Step 5: Commit**

```bash
git add glassresumatch-ai/pages/TailoringReview.tsx
git commit -m "fix(ui): restructure TailoringReview footer — group GDoc actions, replace stat counters with progress bar"
```

---

### Task 3: JobDetail metadata row — Entropy fix (E2)

**Files:**
- Modify: `glassresumatch-ai/pages/JobDetail.tsx:368-384`

**Why:** Salary and recruiter email have higher decision-making value than "2d ago" or applicant count, but all 4 items use identical `text-[10px] font-mono text-gray-500` styling. This creates flat entropy — equal visual weight for unequal information value.

- [ ] **Step 1: Give salary and recruiter email higher visual weight**

In `JobDetail.tsx`, modify the metadata item construction (lines 369-374):

```tsx
const metaItems: React.ReactNode[] = [];
const freshness = formatTimeAgo(job.posted_at);
if (freshness) metaItems.push(<span key="posted" className="flex items-center gap-1"><Clock className="w-3 h-3" />{freshness}</span>);
if (job.applicants_count && job.applicants_count > 0) metaItems.push(<span key="applicants" className="flex items-center gap-1"><Users className="w-3 h-3" />{job.applicants_count} applicants</span>);
if (job.salary_info) metaItems.push(<span key="salary" className="flex items-center gap-1 text-gray-400"><DollarSign className="w-3 h-3" />{job.salary_info}</span>);
if (eval_.recruiter_email) metaItems.push(<a key="recruiter" href={`mailto:${eval_.recruiter_email}`} className="flex items-center gap-1 text-gray-400 hover:text-gray-300"><Mail className="w-3 h-3" />{eval_.recruiter_email}</a>);
```

Changes:
- Salary: `text-gray-500` → `text-gray-400` (one step brighter = slightly more salient)
- Recruiter email: `text-gray-500` → `text-gray-400` + hover `text-gray-300` (interactive affordance)
- Posted time + applicants: unchanged (correctly subordinate)

The parent container still uses `text-[10px] font-mono text-gray-500` as the base, so salary and recruiter override with `text-gray-400` via specificity.

- [ ] **Step 2: Visual verify**

Verify in browser:
- Salary and recruiter email are subtly brighter than posted time and applicants
- Recruiter email brightens further on hover (interactive signal)
- The difference is subtle, not jarring — a scanning gradient, not a hierarchy break

- [ ] **Step 3: Commit**

```bash
git add glassresumatch-ai/pages/JobDetail.tsx
git commit -m "fix(ui): emphasize salary and recruiter in metadata row for scanning gradient"
```

---

### Task 4: TailorCard hover button gap — Fitts's Law polish (F2)

**Files:**
- Modify: `glassresumatch-ai/pages/Dashboard.tsx:149`

**Why:** Skip and Tailor CV hover-reveal buttons have 6px gap. Low severity (hover-reveal means cursor is already close, Skip is non-destructive), but easy polish.

- [ ] **Step 1: Increase gap from `gap-1.5` to `gap-3`**

In `Dashboard.tsx` line 149, change:

```tsx
// Before
<div className="absolute bottom-3 right-3 flex gap-1.5 opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300">

// After
<div className="absolute bottom-3 right-3 flex gap-3 opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300">
```

6px → 12px gap. Doubles the perceptual boundary between Skip (ghost) and Tailor CV (accent fill).

- [ ] **Step 2: Visual verify**

Verify in browser:
- Hover over a TailorCard in the Dashboard feed
- Skip and Tailor CV buttons have comfortable spacing
- Buttons don't overflow the card bounds on narrow cards

- [ ] **Step 3: Commit**

```bash
git add glassresumatch-ai/pages/Dashboard.tsx
git commit -m "fix(ui): increase TailorCard hover button gap for Fitts's Law comfort"
```

---

## Verification Checklist

After all 4 tasks:

- [ ] `npm run build` passes with no errors
- [ ] TailoringReview: ChangeCard buttons have 8px gap, no layout overflow
- [ ] TailoringReview: Footer shows progress bar (not colored stat text), GDoc actions collapsed behind "GDoc ▾"
- [ ] TailoringReview: "Approve & Send" is the most visually dominant footer element
- [ ] JobDetail: Salary and recruiter email are subtly brighter than posted time
- [ ] Dashboard: TailorCard hover buttons have 12px gap
- [ ] No visual regressions on SetupPage, Sidebar, MatchBrief, or ApplicationTracker
