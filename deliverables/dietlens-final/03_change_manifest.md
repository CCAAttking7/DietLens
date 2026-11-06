# Change manifest

| File | Change Type | Description | Reason | Regression Risk |
|---|---|---|---|---|
| `web/src/styles/design-system.css` | Added | Final visual tokens, shared contracts, responsive mobile nav, skeletons | Establish one visible design language | Medium: CSS cascade affects all screens |
| `web/src/styles/tokens.css` | Modified | Imports the authoritative design system layer | Centralize design-system entrypoint | Low |
| `web/src/App.tsx` | Modified | Clear nav labels, mobile nav/sheet, labelled drawer | IA, mobile usability, dialog semantics | Medium: route presentation only |
| `web/src/lib/useScreen.ts` | Modified | Shared screen labels | Keep hash routes and UI wording aligned | Low |
| `web/src/components/ToolLoader.tsx` | Modified | Contextual route title skeleton | Preserve page identity during lazy load | Low |
| `web/src/components/SettingsScreen.tsx` | Modified | Delete dialog focus lifecycle and description | Keyboard and screen-reader safety | Medium: modal interaction |
| `scripts/check_*web.cjs` (7 files) | Modified | Updated selectors for renamed navigation labels | Keep existing browser harness aligned | Low |

No backend API, database schema, authentication boundary, nutrition value, or confirmation behavior was changed.
