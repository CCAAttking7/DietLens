# Implemented design system

Source: [web/src/styles/design-system.css](../../web/src/styles/design-system.css), imported from [web/src/styles/tokens.css](../../web/src/styles/tokens.css).

## Color tokens

| Token | Value |
|---|---|
| `--bg` | `#f7f6f2` |
| `--surface` | `#ffffff` |
| `--surface-subtle` | `#f1eee8` |
| `--surface-warm` | `#fbf8f1` |
| `--ink` | `#24231f` |
| `--ink-muted` | `#6f6b63` |
| `--ink-faint` | `#9a958b` |
| `--line` | `#dfdbd2` |
| `--brand` | `#b24e32` |
| `--brand-strong` | `#913b27` |
| `--brand-soft` | `#f3e1d9` |
| `--success` | `#4e765d` |
| `--warning` | `#9a6b1d` |
| `--danger` | `#a33e34` |
| `--info` | `#5e7598` |

## Typography

`--font-ui` is `-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", system-ui, sans-serif`. Display text uses the same stack. Sizes are `--text-xs: 11px`, `--text-sm: 13px`, `--text-md: 15px`, `--text-lg: 18px`, `--text-xl: 24px`, and `--text-display: clamp(36px, 5vw, 64px)`. Metrics and dates use tabular numerals.

## Spacing and shape

The scale is 4, 8, 12, 16, 24, 32, 40, 48, 64, 80px (`--space-1` through `--space-10`). Radii are 4px (`--radius-sm`), 8px (`--radius-control`), 12px (`--radius-md`), 16px (`--radius-card`), 24px (`--radius-feature`), and 999px for pills.

## Elevation

`--shadow-subtle: 0 1px 2px rgba(36,35,31,.04)`, `--shadow-raised: 0 8px 24px rgba(36,35,31,.08)`, and `--shadow-modal: 0 24px 64px rgba(36,35,31,.16)`.

## Components

Primary and destructive controls use brand/semantic fills and a 44px minimum height. Secondary controls use `--surface-subtle`; quiet controls stay transparent. Inputs, selects, cards, drawer tabs, statuses, and empty/error surfaces share the same border, radius, focus ring, and spacing contracts. Dialogs use `aria-modal`, labelled headings, focus trapping, Escape handling, and focus restoration in the existing component utilities.

## Motion and breakpoints

Control feedback is 180ms; drawer/modal transitions use the existing 240–320ms range. `prefers-reduced-motion: reduce` disables decorative and skeleton animation. The main responsive breakpoint is 760px, with the existing 600px compact layout retained. Mobile navigation includes `env(safe-area-inset-bottom)`.

## Icons

The current product uses its existing compact glyph/icon treatment. This pass preserves those handlers and labels while normalizing alignment; a future icon asset migration remains listed in remaining issues.
