# Remaining issues

## P0

- None identified from the implementation pass. Authenticated browser verification remains blocked by tooling rather than bypassed.

## P1

- Run the existing Playwright harness against a real demo/authenticated session and capture the required after screenshots at 1440, 1280, 768, 390, and 375px.
- Complete a real screen-reader pass and automated axe scan once browser tooling is available.
- Migrate the remaining legacy CSS files into the new design-system source over a follow-up refactor; the final layer currently normalizes their shared output without removing them.

## P2

- Replace remaining improvised text glyphs with a consistent SVG icon set while preserving accessible labels.
- Add a dedicated visual regression job and a lint script to `web/package.json`.
- Validate WCAG contrast with the final rendered font stack and browser zoom settings.

No known business-logic or authorization regression was introduced by this pass.
