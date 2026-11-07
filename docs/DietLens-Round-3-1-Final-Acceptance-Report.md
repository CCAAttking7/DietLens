# DietLens Round 3.1 Final Acceptance Report

## Scope

This targeted patch starts from `6939ab0399ccdfd50cbf7bfc14c53e7313332f97` on `codex/dietlens-round-3-quality-gate` and is delivered on `codex/dietlens-round-3-1-final-acceptance`. It corrects verified acceptance defects without changing backend APIs, schemas, authentication, or meal business rules.

## P2 Closure

### P2-1 — Settings dialog fallback focus

Manual focus redirects now call `preventDefault()` in every fallback branch: no controls, focus outside the dialog, focus on the dialog container, and an unexpected focusable index. The existing busy-state capture handler remains unchanged in behavior. `check_delete_busy_web.cjs` now asserts direct dialog Tab and Shift+Tab, forced outside focus recovery, normal forward/reverse cycling, busy focus ownership, Escape consumption, and both successful and failed deletion flows.

### P2-2 — Deterministic visual evidence

`check_visual_web.cjs` creates a UTC browser context and calls `page.clock.setFixedTime(new Date('2026-11-07T12:00:00Z'))` before navigation. The baseline was regenerated from isolated commit `6939ab0`, and After was regenerated from this branch with the same harness, fixtures, browser, timezone, five viewports and screenshot directory configuration. Both logs report the Plan input as `2026-11-07` at every viewport. There are 55 symmetric Before/After PNG pairs with matching dimensions.

### P2-3 — CSS-sourced button contrast coverage

`check_contrast.cjs` continues to parse tokens from `web/src/styles/design-system.css` and now also parses the actual `.button-primary`, `.button-secondary`, and `.button-destructive` declarations. It resolves `var(--token)` references and validates white/brand, white/danger, and normal-text/secondary-surface combinations alongside the existing matrix. Missing selectors, declarations, or tokens fail the check.

## Corrections

| Original defect | Root cause | Exact fix | Regression evidence |
|---|---|---|---|
| Settings Delete Modal Tab navigation skipped interior movement and busy focus could escape | The handler prevented every Tab but only moved focus at boundaries; disabled controls left no focusable item | The trap now discovers visible enabled controls, allows native interior movement, wraps only at boundaries, focuses the dialog fallback when busy, and consumes busy Escape | `scripts/check_delete_busy_web.cjs`: idle sequence, busy Tab/Shift+Tab, Escape, success and failure all PASS |
| More Sheet route selection restored focus to a hidden menu item | `openPanel` recorded the clicked More Sheet item as the Drawer return target | More Sheet navigation explicitly records `#mobile-more-trigger`; Food, Inventory, and Settings close back to that trigger | `scripts/check_mobile_navigation_web.cjs`: route focus restoration, inert, scroll lock, backdrop, reverse trap and ARIA assertions PASS |
| Home manual-entry CTA wrapped Chinese text vertically | The text CTA inherited the fixed 36px `.quiet-button` dimensions | `.button-quiet` is now content-sized with 44px minimum touch height; icon-only controls have a separate `.icon-button-quiet` contract | `scripts/check_home_cta_web.cjs`: 375/390/768/1280/1440 PASS; width, height, nowrap, overflow and keyboard focus asserted |
| Plan screenshots captured the lazy skeleton | The visual harness captured immediately after opening the route | The harness waits for `.plan-form`, the real editor heading and the date input before the main screenshot | `scripts/check_visual_web.cjs`: all five viewport widths PASS with no page errors or overflow |
| Screenshot directory configuration only applied to Home | Route screenshots hardcoded `after/` | Every screenshot path uses `artifactRoot/screenshotDir`; baseline and current captures use the same fixture and browser matrix | 55 matching PNG pairs exist in `artifacts/dietlens-round-3/before` and `after` |
| Contrast test values could drift from CSS | The script duplicated token literals | Contrast validation now parses HEX custom properties directly from `web/src/styles/design-system.css :root` and checks semantic foreground/background pairs | `npm run qa:contrast` PASS; source path is printed in the result |
| Inventory and Settings skeletons differed mostly by count | Both routes shared generic card rows | Inventory now shows summary, item, quantity/unit and action geometry; Settings shows profile, groups, authorization/data-management geometry | `ToolLoader.tsx` and scoped skeleton styles reviewed; lazy loading semantics retained |

## Modal and focus behavior

The delete dialog has a stable `tabIndex=-1` fallback. Idle keyboard behavior is conventional: first → second → first with Tab, and first → last → first with Shift+Tab. During deletion the window capture handler prevents Tab and returns focus to the dialog; Escape is consumed and does not close the dialog or parent Drawer. A focus-in guard covers programmatic or browser focus movement while the asynchronous request is pending.

The More Sheet remains mounted while hidden so `aria-controls` always references a real element. Its background regions receive `inert`, body overflow is locked and restored, the previous scroll position is restored, and route selection records the More trigger as the Drawer return target.

## Tests and commands

| Check | Status | Evidence |
|---|---|---|
| Frontend production build | PASS | `round-3-1-build.log` |
| Python regression suite | PASS | `PYTHONPATH=. .venv/bin/pytest -q`, 227 passed |
| JavaScript syntax | PASS | `round-3-1-syntax.log` |
| CSS-sourced contrast matrix | PASS | `round-3-1-contrast.log` |
| More Sheet browser test | PASS | `moreSheetSemantics`, `routeFocusRestoration`, `scrollLock`, `backdrop`, `drawerIsolation` |
| Home CTA browser test | PASS | Five required viewports |
| Settings browser test | PASS | Existing recovery and nested dialog coverage |
| Async deletion browser test | PASS | Idle/busy focus, Escape, success and failure |
| Responsive visual matrix | PASS | Five widths, fixed UTC time, synchronized Plan dates, no page errors or overflow |
| Authenticated Supabase workflows | BLOCKED | No safe authenticated fixture/session is available |
| GitHub Actions result | NOT VERIFIED | Workflow is preserved/configured; unauthenticated API/CLI access prevented verification |

Canonical commands:

```bash
npm install
npx playwright install chromium
npm run qa:build
PYTHONPATH=. .venv/bin/pytest -q
npm run qa:syntax
npm run qa:contrast
npm run qa:browser
```

## Before/After evidence

The comparison index is [artifacts/dietlens-round-3/comparison/index.md](../artifacts/dietlens-round-3/comparison/index.md). It links 55 matching browser-rendered pairs, including Home, Food, Plan, Inventory, Review, Settings, Journal, Saved Plans and detail states at 375, 390, 768, 1280 and 1440px. Before uses isolated commit `6939ab0`; After uses this acceptance branch. Both runs use fixed UTC time `2026-11-07T12:00:00Z`; all Plan date assertions are `2026-11-07`, all image dimensions match, and the Plan pairs were captured only after the real `.plan-form` editor became visible.

## Remaining limitations

- Authenticated Supabase flows remain BLOCKED because no safe test session is committed or available.
- GitHub Actions is configured in `.github/workflows/dietlens-quality-gate.yml`, but its remote result is NOT VERIFIED from this unauthenticated environment.
- Contrast validation covers the declared semantic token matrix and does not claim to prove every arbitrary legacy literal in historical CSS.
- No pixel-diff heatmap is generated; the comparison index provides same-name, same-viewport evidence for human review.

## Regression assessment

No backend API or schema changed. Authentication boundaries, draft persistence, meal confirmation, plan/actual separation, provenance, unknown nutrition values, inventory conflict handling, export, deletion safeguards and URL navigation remain intact. Changes are limited to focus ownership, semantic presentation, loading geometry, test assertions and evidence generation.
