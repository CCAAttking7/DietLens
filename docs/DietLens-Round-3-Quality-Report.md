# DietLens Round 3 Quality Gate Report

## Executive summary

Round 3 is a precision quality iteration based on the Round 2 commit `577bbfb4fc7f6aad45cbce90d7620ad833800e58`. It preserves the product architecture and business behavior while tightening dialog focus behavior, mobile modal isolation, browser-test selectors, Playwright dependency reproducibility, semantic button variants, contrast tokens, and route-specific loading geometry.

## Round 2 findings reviewed

- Delete-modal focus could escape when deletion disabled all controls.
- Parent Drawer listeners could observe nested dialog keyboard events.
- Mobile More Sheet was labelled as modal but did not inert its background.
- `aria-controls` referenced a conditionally unmounted element.
- Visual tests used one generic navigation selector and did not cover all requested widths.
- Browser scripts required an undeclared Playwright package.
- Button styling still depended on container selectors.
- Warning, information, faint, and success token combinations did not consistently meet AA.
- Route skeletons needed stronger structural differences.

## Exact defects corrected

### Delete dialog

`SettingsScreen.tsx` now gives the dialog a stable `tabIndex=-1` target and a ref. The key handler always consumes Escape while active; it only closes when idle. Idle Tab and Shift+Tab use native movement between interior enabled controls and wrap only at the dialog boundaries. When all controls are disabled, busy-state Tab and Shift+Tab are prevented and kept on the dialog fallback. The handler stops propagation so the Settings Drawer cannot close. Focus initialization depends only on opening, not `busy`, and focus restoration uses the original trigger.

The new `scripts/check_delete_busy_web.cjs` fixture delays `/api/delete` and asserts busy Tab, Shift+Tab, Escape, success, and failure behavior. It is executable when Chromium is installed.

### Mobile More Sheet

The sheet remains mounted with `hidden` when closed, making `aria-controls="mobile-more-sheet"` valid. When open, the sidebar, main content, and bottom navigation receive `inert`; the dialog itself remains active. Body overflow and scroll position are restored on close. Focus starts on the close button, wraps, consumes Escape, and returns to the trigger. Route selection closes the sheet before the destination Drawer takes focus.

`scripts/check_mobile_navigation_web.cjs` asserts the ARIA contract, initial focus containment, forward and reverse Tab wrapping, Escape, trigger restoration after Food/Inventory/Settings route drawers, scroll lock, backdrop dismissal, and Drawer isolation.

### Visual selectors and viewport coverage

`check_visual_web.cjs` now explicitly uses `.sidebar-bottom > button` for desktop Settings, `.side-nav button` for desktop tools, `.mobile-nav button` for mobile primary destinations, and `#mobile-more-sheet` for mobile secondary destinations. It covers 375, 390, 768, 1280, and 1440px, checks Drawer overflow and complete document dimensions, and writes actual screenshots to `artifacts/dietlens-round-3/after/` when it runs.

### Reproducible Playwright setup

A root QA package now declares `playwright@1.51.1` with a lockfile. Root commands are:

```bash
npm install
npx playwright install chromium
npm run qa:build
npm run qa:contrast
npm run qa:syntax
npm run qa:mobile
npm run qa:settings
npm run qa:delete
npm run qa:visual
npm run qa:browser
```

The root scripts resolve Playwright for every `scripts/check_*.cjs` file. A GitHub Actions workflow installs Node dependencies, Chromium, builds the frontend, runs contrast/syntax/browser gates, and uploads `artifacts/dietlens-round-3`.

### Semantic buttons

The design layer now uses `.button-primary`, `.button-secondary`, `.button-quiet`, and `.button-destructive`, while retaining legacy class aliases where components already use them. Container selectors no longer make every button in a Composer, Card, Plan, Search, or Inventory container brand-primary. Unclassified buttons receive a neutral control baseline; important actions were assigned explicit semantic classes. Disabled and focus-visible behavior remains shared.

### Contrast validation

`scripts/check_contrast.cjs` computes WCAG relative luminance and checks actual token/background pairs. Tokens were corrected to:

| Token | Value |
|---|---|
| `--ink-muted` | `#625c56` |
| `--ink-faint` | `#655f58` |
| `--success` | `#3f654d` |
| `--warning` | `#85570f` |
| `--info` | `#425c86` |

The automated matrix currently passes all listed normal-text pairs at 4.5:1 or higher. Disabled controls remain visually subdued; the report does not claim disabled text is a normal-text AA pass.

### Route skeletons

`ToolLoader.tsx` now differentiates Food search/results/nutrition rows, Inventory list/action rows, Plan date and meal sections, Review metrics/timeline, and Settings groups. All preserve `role="status"`, `aria-busy`, geometry, restrained animation, and reduced-motion behavior.

## Files modified

- `.gitignore`, `package.json`, `package-lock.json`
- `.github/workflows/dietlens-quality-gate.yml`
- `web/src/App.tsx`
- `web/src/components/FoodScreen.tsx`
- `web/src/components/InventoryScreen.tsx`
- `web/src/components/MealJournal.tsx`
- `web/src/components/PlanScreen.tsx`
- `web/src/components/SavedPlans.tsx`
- `web/src/components/SettingsScreen.tsx`
- `web/src/components/ShoppingPanel.tsx`
- `web/src/components/ToolLoader.tsx`
- `web/src/components/WorkbenchScreen.tsx`
- `web/src/styles/design-system.css`
- `web/src/styles/foundation.css`
- `web/src/styles/theme.css`
- `scripts/check_contrast.cjs`
- `scripts/check_delete_busy_web.cjs`
- `scripts/check_mobile_navigation_web.cjs`
- `scripts/check_settings_web.cjs`
- `scripts/check_visual_web.cjs`
- `artifacts/dietlens-round-3/` evidence structure

## Test results

| Category | Status | Evidence |
|---|---|---|
| Frontend production build | PASS | `npm run qa:build` |
| Python regression suite | PASS | 227 passed |
| JavaScript syntax | PASS | `npm run qa:syntax` |
| Contrast matrix | PASS | `npm run qa:contrast` |
| Mobile browser tests | PASS | `test-results/mobile.log` |
| Settings browser tests | PASS | `test-results/settings.log` |
| Async delete browser tests | PASS | `test-results/delete.log` |
| Responsive visual screenshots | PASS | 55 before/after pairs, including Home, in `artifacts/dietlens-round-3/` |
| Authenticated Supabase tests | BLOCKED | No authenticated fixture/session |
| CI workflow | NOT RUN | Branch is pushed; CI runs after GitHub Actions pickup |

Playwright is reproducibly declared and `npx playwright --version` returns `1.51.1`. Chromium was installed and all listed browser gates executed successfully.

## Browser and viewport matrix

The visual harness is configured for 375, 390, 768, 1280, and 1440px. At mobile widths it selects actual bottom navigation and More Sheet controls; at desktop widths it selects the sidebar and the separate Settings location. The configured page set is Home, Food, Plan, Inventory, Review, and Settings, with journal/saved-plan states retained from the existing visual harness.

## Before/After screenshots

`artifacts/dietlens-round-3/{before,after,comparison}` contains 55 actual matching PNG pairs, including Home at every viewport. Before was rendered from `b5dd6e2`; After was rendered from this Round 3 branch with the same fixtures and viewport matrix. `comparison/index.md` links each pair.

## Known issues and remaining blocked items

- Authenticated Supabase flows require a safe authenticated fixture and remain blocked.
- The automated contrast matrix checks the declared semantic pairs, not every arbitrary legacy literal in the historical CSS files.
- A pixel-level image-diff heatmap is not generated; `comparison/index.md` provides paired inspection links and avoids treating every pixel change as a regression.

## Regression assessment

No backend API, schema, authentication, authorization, draft persistence, meal confirmation, nutrition provenance, inventory conflict, export, deletion business rule, or URL hash contract was changed. The only behavior changes are interaction isolation and presentation/testability improvements described above.
