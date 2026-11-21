# DietLens Round 2 Change Log

| File | Change | Reason |
|---|---|---|
| `web/src/App.tsx` | Mobile More Sheet semantics, focus trap, Escape handling, body scroll lock, drawer Escape guard | Keep only the topmost interaction active and make mobile navigation keyboard accessible |
| `web/src/components/SettingsScreen.tsx` | Stable delete-dialog focus lifecycle and event isolation | Prevent parent drawer closure and focus reset during async deletion |
| `web/src/components/ToolLoader.tsx` | Destination-specific skeleton geometry for five tools | Preserve page structure during lazy loading |
| `web/src/components/FoodScreen.tsx` | First-level nutrition summary with expandable field status | Make available nutrition immediately useful while preserving unknowns |
| `web/src/styles/design-system.css` | Contrast token, skeleton geometry, nutrition summary and More Sheet styling | Support the new contracts without a CSS rewrite |
| `web/src/styles/foundation.css` | Removed unnecessary button `!important` declarations | Reduce cascade conflicts |
| `web/src/styles/workspace.css` | Removed unnecessary state `!important` declarations | Reduce cascade conflicts |
| `web/src/styles/flows.css` | Removed unnecessary component `!important` declarations | Reduce cascade conflicts |
| `scripts/check_visual_web.cjs` | 5 viewports, visible navigation selectors, full-document overflow, artifact screenshots | Prevent false mobile failures and test actual page dimensions |
| `scripts/check_settings_web.cjs` | Nested delete dialog Escape, focus trap, and parent drawer regression assertions | Cover the P0 interaction failure mode |
| `scripts/check_mobile_navigation_web.cjs` | New More Sheet keyboard and semantics regression script | Cover mobile navigation independently |
| `artifacts/dietlens-round-2/*` | Added capture directories and limitation manifest | Provide a stable location for actual browser evidence |
