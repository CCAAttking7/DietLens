# DietLens Round 3.1 Change Log

| File | Change | Reason |
|---|---|---|
| `web/src/components/SettingsScreen.tsx` | Conventional idle focus trap; busy dialog fallback; capture-phase Escape/Tab handling; focus-in guard | Keep focus inside the topmost delete dialog during asynchronous deletion |
| `web/src/App.tsx` | More Sheet route selection passes the More trigger as Drawer return target; manual-entry CTA uses text quiet variant | Restore usable focus and prevent vertical CTA wrapping |
| `web/src/styles/foundation.css` | Removed fixed dimensions from generic quiet buttons; added icon-only quiet contract | Separate icon controls from text actions |
| `web/src/styles/design-system.css` | Content-sized `.button-quiet`; inventory/settings skeleton geometry | Preserve readable labels and represent destination page structure |
| `web/src/components/ToolLoader.tsx` | Inventory summary/item/action and Settings profile/group/data-management skeletons | Reduce lazy-route layout ambiguity |
| `scripts/check_delete_busy_web.cjs` | Exact idle and busy active-element assertions | Prevent superficial modal visibility coverage |
| `scripts/check_mobile_navigation_web.cjs` | Route return focus, inert, scroll, backdrop and reverse-trap assertions | Verify complete More Sheet modal isolation |
| `scripts/check_home_cta_web.cjs` | New five-viewport CTA geometry and keyboard test | Protect manual entry readability |
| `scripts/check_visual_web.cjs` | Screenshot directory applied to every capture; Plan loaded-state waits | Make evidence reproducible and avoid skeleton screenshots as page proof |
| `scripts/check_contrast.cjs` | Reads tokens from `design-system.css` instead of duplicating values | Prevent CSS/test drift |
| `package.json` | Added `qa:home`; included it in `qa:browser` | Make the new regression gate explicit |
| `artifacts/dietlens-round-3/` | Regenerated 55 before/after pairs and test logs | Provide real acceptance evidence |
| `docs/DietLens-Round-3-1-Final-Acceptance-Report.md` | Final acceptance report | Record root causes, fixes, evidence and limitations |
| `web/src/components/SettingsScreen.tsx` | Added `preventDefault()` to every manual focus fallback | Prevent native Tab from running after scripted fallback focus redirects |
| `scripts/check_delete_busy_web.cjs` | Added direct-dialog and outside-focus active-element assertions | Protect P2 fallback focus behavior without weakening normal cycling |
| `scripts/check_visual_web.cjs` | Added UTC context and Playwright fixed time; reported Plan dates | Make Before/After dates deterministic and independently verifiable |
| `scripts/check_contrast.cjs` | Parsed semantic button selectors and resolved CSS variables | Cover actual primary, secondary and destructive button combinations |
| `artifacts/dietlens-round-3/` | Regenerated Before from `6939ab0` and After from this branch; added fixed-time logs | Correct the baseline and prove 55 synchronized pairs |
