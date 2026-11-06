/** Match keyboard navigation, excluding controls in closed details and disabled fieldsets. */
export function focusableWithin(container: HTMLElement | null) {
  return Array.from(container?.querySelectorAll<HTMLElement>('a[href], button, input, select, textarea, summary, [tabindex]') ?? [])
    .filter(element => element.tabIndex >= 0 && !element.matches(':disabled') && !element.closest('[inert]') && element.getClientRects().length > 0)
}
