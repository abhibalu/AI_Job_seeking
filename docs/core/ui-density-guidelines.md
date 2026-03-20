# UI Info Density Guidelines
> For Claude Code: apply these rules when sizing, spacing, or redesigning any UI component.

---

## The Core Rule

**Every pixel must justify itself.** Before adding whitespace, padding, or a container — ask: does this help the user read faster, or does it just look airy?

---

## Element Weights (Information Units)

Assign each element a weight. This is your gut-check vocabulary.

| Weight | Element types |
|--------|--------------|
| **×8** | Body text, paragraph content, data rows |
| **×6** | Lists, tables, code blocks |
| **×5** | Images, charts, graphs |
| **×4** | Headings, section titles |
| **×3** | Input fields, form controls |
| **×2** | Labels, buttons, badges, nav items |
| **×1** | Icons, dividers, decorative chrome |

---

## The Three Checks

Run these mentally before finalising any layout change.

### 1. Density check
> Is the total IU reasonable for the area consumed?

- Count up IU weights for all visible elements
- If a section uses >30% of vertical space but contributes <10% of total IU → it's a density sink. Shrink it or cut it.
- Common offenders: hero images, empty state placeholders, oversized headings, cards with one line of text

### 2. Efficiency check
> Are the elements that *are* there doing real work?

- Icons alone = ×1. Icons with a label = ×2+. Prefer the latter.
- A card that wraps a single badge is wasting its container
- If you can't articulate what decision the user makes from a section, question whether it belongs

### 3. Whitespace check
> Is whitespace *functional* or *decorative*?

- **Functional**: separates groups, guides the eye, creates hierarchy → keep it
- **Decorative**: padding added to "feel premium" without serving scanning → cut it
- Target: 40–60% coverage for dense UIs (dashboards, detail views), 25–45% for landing/marketing

---

## Verdict-Specific Rules (OotoCV Detail View)

Different verdict states have different density targets. Do not apply a uniform layout.

| Verdict | Density target | Why |
|---------|---------------|-----|
| `tailor` | High — max elements | User needs full context to act |
| `apply` | High — focused | Key details prominent, clutter removed |
| `skip` | Low — intentional | Minimal info needed, don't waste attention |
| `applied` | Medium | Status + history, not action |
| `interview` | High | Prep content, notes, timeline |

---

## Hard Rules for Claude Code

1. **Never add padding > 24px on a content container** without a written reason in the component comment
2. **Never render a Card with fewer than 3 IU worth of content** — flatten it instead
3. **Headings cost ×4 IU but consume far more space** — if a section has only one heading and one line of body text, remove the heading
4. **No decorative dividers** unless separating semantically distinct groups
5. **Every empty state must fit in ≤ 64px vertical height** — no full-panel empty states
6. **Accordions and progressive disclosure are preferred** over always-visible low-IU sections
7. **If a redesign reduces visible IU by more than 20% without removing a feature**, it's a regression — justify it or revert

---

## Quick Sizing Reference

When unsure how tall/wide a component should be:

```
min-height = (IU of content × 6px) + padding
```

Example: a card with a heading (×4) + 2 data rows (×16) + a button (×2) = 22 IU → min ~132px + padding. If your card is 240px for 22 IU, you have a density problem.

---

## What Good Looks Like

- User can extract the key fact from a section in **< 2 seconds**
- No section requires scrolling just to see if it has content
- The heaviest-IU elements are visually dominant (larger, higher contrast)
- Low-IU chrome (labels, icons, dividers) is visually subordinate
