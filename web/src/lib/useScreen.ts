import { useCallback, useEffect, useState } from 'react'

export type Screen = 'care' | 'plan' | 'food' | 'inventory' | 'workbench' | 'settings'
export const screenLabels: Record<Screen, string> = {
  care: '今日饮食', plan: '饮食计划', food: '食品资料', inventory: '食材库存',
  workbench: '饮食回顾', settings: '设置',
}

function readScreen(): Screen {
  const value = window.location.hash.slice(1)
  return Object.hasOwn(screenLabels, value) ? value as Screen : 'care'
}

/** Keep panel navigation shareable and compatible with browser Back / Forward. */
export function useScreen() {
  const [screen, updateScreen] = useState<Screen>(readScreen)
  const navigate = useCallback((next: Screen) => {
    if (readScreen() !== next) {
      const url = new URL(window.location.href)
      url.hash = next === 'care' ? '' : next
      window.history.pushState(null, '', url)
    }
    updateScreen(next)
  }, [])
  useEffect(() => {
    const sync = () => updateScreen(readScreen())
    window.addEventListener('popstate', sync)
    window.addEventListener('hashchange', sync)
    return () => {
      window.removeEventListener('popstate', sync)
      window.removeEventListener('hashchange', sync)
    }
  }, [])
  return [screen, navigate] as const
}
