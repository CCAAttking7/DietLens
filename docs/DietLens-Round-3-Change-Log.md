# DietLens Round 3 Change Log

| File | Meaningful change | Rationale |
|---|---|---|
| `web/src/components/SettingsScreen.tsx` | Stable dialog fallback focus, busy-safe Tab/Shift+Tab, Escape isolation | Prevent focus escape and parent Drawer closure during asynchronous deletion |
| `web/src/App.tsx` | Mounted More Sheet, inert background ownership, scroll restoration, ARIA states | Make mobile navigation a real modal interaction |
| `web/src/components/ToolLoader.tsx` | Food/Inventory/Plan/Review/Settings skeleton structures | Preserve destination geometry during lazy loading |
| `web/src/components/FoodScreen.tsx` | Explicit primary/secondary button semantics | Prevent container CSS from determining intent |
| `web/src/components/InventoryScreen.tsx` | Explicit primary/secondary action classes | Same semantic button contract |
| `web/src/components/MealJournal.tsx` | Explicit primary/secondary action classes | Same semantic button contract |
| `web/src/components/PlanScreen.tsx` | Explicit primary/secondary action classes | Same semantic button contract |
| `web/src/components/SavedPlans.tsx` | Explicit button classes | Same semantic button contract |
| `web/src/components/SettingsScreen.tsx` | Explicit primary/secondary/destructive classes | Same semantic button contract |
| `web/src/components/ShoppingPanel.tsx` | Explicit secondary class | Preserve non-primary action intent |
| `web/src/components/WorkbenchScreen.tsx` | Explicit semantic action classes | Preserve review action intent |
| `web/src/styles/design-system.css` | Semantic button variants, neutral baseline, contrast token corrections, skeleton styles | Complete the design system without another global override layer |
| `web/src/styles/foundation.css` | Removed container-based action button styling; semantic status tokens | Reduce broad selector coupling |
| `web/src/styles/theme.css` | Semantic success token use | Keep state colors aligned with the contrast matrix |
| `scripts/check_contrast.cjs` | New luminance/ratio gate | Make contrast verification repeatable |
| `scripts/check_delete_busy_web.cjs` | New delayed deletion fixture | Cover mandatory async modal behavior |
| `scripts/check_mobile_navigation_web.cjs` | More Sheet accessibility test | Cover background isolation and focus behavior |
| `scripts/check_settings_web.cjs` | Nested dialog assertions | Protect Escape and focus restoration |
| `scripts/check_visual_web.cjs` | Explicit responsive selectors and page overflow | Remove false mobile/Settings assumptions |
| `package.json`, `package-lock.json` | Root Playwright QA package and commands | Make browser setup reproducible |
| `.github/workflows/dietlens-quality-gate.yml` | Build, contrast, syntax, browser QA, artifact upload | Provide repeatable CI verification |
| `artifacts/dietlens-round-3/` | Before/after/comparison/test-results structure | Reserve verifiable screenshot evidence locations |
