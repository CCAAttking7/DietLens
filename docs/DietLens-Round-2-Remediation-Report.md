# DietLens Round 2 Remediation Report

## Executive summary

Round 2 is a targeted refinement of the existing DietLens React/Vite product. The implementation preserves Supabase authentication, API contracts, draft recovery, explicit confirmation, nutrition provenance, and inventory conflict behavior. It focuses on the audit findings that could create real interaction or verification risk: nested dialog Escape propagation, modal focus lifecycle, mobile navigation semantics, misleading responsive visual coverage, generic route loading, nutrition hierarchy, and CSS specificity debt.

## Issues addressed

### P0: nested modal and drawer interaction

- The Settings delete dialog now stops Escape and Tab propagation before the parent drawer listener can act.
- Focus initialization runs when the dialog opens, rather than rerunning on every `busy` state transition.
- A ref-backed busy value keeps asynchronous deletion behavior current without resetting focus.
- Escape closes the delete dialog only; the Settings drawer remains open.
- The existing dialog semantics, initial focus, trapping, and restoration are retained and tightened.

### P0: mobile More Sheet

- The existing mobile navigation now exposes `aria-expanded`, `aria-controls`, `role="dialog"`, `aria-modal`, `aria-labelledby`, a visible close button, focus trapping, Escape dismissal, body scroll locking, and focus restoration.
- `aria-current="page"` is applied to selected secondary destinations.
- The sheet is hidden while a route drawer is open so two navigation layers cannot compete.
- Existing safe-area padding and bottom navigation content clearance remain in place.

### P0: responsive visual verification

`scripts/check_visual_web.cjs` now covers 1440, 1280, 768, 390, and 375px. It selects desktop navigation above 760px and bottom navigation/More Sheet at mobile widths. It checks both the drawer and the complete document dimensions (`scrollWidth` versus `clientWidth`) and writes browser screenshots to `artifacts/dietlens-round-2/after/` when Playwright is available.

### P0: route-specific loading

`ToolLoader.tsx` now renders Food, Inventory, Plan, Review, Settings, and fallback skeleton geometry based on the destination title. Each skeleton includes loading semantics (`role="status"`, `aria-busy="true"`), restrained animation, and reduced-motion support.

### P1: design system cleanup

The authoritative design layer now uses a higher-contrast faint text token and removes unnecessary `!important` declarations from legacy button, state, and component rules. The remaining reduced-motion overrides are intentional safety overrides. Existing behavior-specific styles remain in place; this is a controlled specificity cleanup, not a rewrite.

### P1: food information hierarchy

Nutrition values and their source basis now appear at first level in every Food result when available. Unknown fields remain explicitly `未知`; provenance and field completeness details remain expandable. No data conversion or inferred nutrition was added.

## Verification

- Frontend build: PASS (`npm run build` in `web/`).
- Python regression suite: PASS, 227 tests passed.
- JavaScript syntax checks: PASS for all `scripts/check_*.cjs` files.
- `git diff --check`: PASS.
- Browser/Playwright execution: BLOCKED in this environment because the Playwright package and Chromium executable are unavailable. No browser results or screenshots are claimed as passed.
- Automated axe execution: NOT AVAILABLE; source-level semantic and keyboard review is documented in the change log.

## Screenshots

The visual harness writes actual before/after screenshots to `artifacts/dietlens-round-2/` when run with Playwright. In this environment capture is BLOCKED. The existing baseline PNGs from the previous handoff remain under `deliverables/dietlens-final/screenshots/before/`; no generated or fabricated after images were added.

## Known issues and regression assessment

- Authenticated Supabase browser flows remain unverified because no authenticated fixture/session is available.
- No backend, schema, authentication, authorization, or data behavior was changed.
- Legacy CSS files remain for incremental migration; shared output is controlled by the final token layer.
- Icon glyph migration and automated color contrast tooling remain follow-up work.

## Modified files

See [DietLens-Round-2-Change-Log.md](./DietLens-Round-2-Change-Log.md) for the complete file list and rationale.
