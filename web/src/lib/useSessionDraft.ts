import { useEffect, useState } from 'react'

const memoryDrafts = new Map<string, unknown>()

export function writeSessionDraft<T>(key: string, value: T) {
  memoryDrafts.set(key, value)
  try { sessionStorage.setItem(`dietlens:${key}`, JSON.stringify(value)) } catch { /* Keep the tab usable when browser storage is blocked. */ }
}

export function removeSessionDraft(key: string) {
  memoryDrafts.delete(key)
  try { sessionStorage.removeItem(`dietlens:${key}`) } catch { /* Memory is still cleared. */ }
}

/** Per-tab, per-user drafts. Storage restrictions must never block the UI. */
export function useSessionDraft<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    if (memoryDrafts.has(key)) return memoryDrafts.get(key) as T
    try {
      const raw = sessionStorage.getItem(`dietlens:${key}`)
      return raw === null ? initial : JSON.parse(raw) as T
    } catch { return initial }
  })
  useEffect(() => {
    writeSessionDraft(key, value)
  }, [key, value])
  return [value, setValue] as const
}

export function clearSessionDrafts(userId: string) {
  for (const key of memoryDrafts.keys()) if (key.startsWith(`${userId}:`)) memoryDrafts.delete(key)
  try {
    const prefix = `dietlens:${userId}:`
    for (let i = sessionStorage.length - 1; i >= 0; i--) {
      const key = sessionStorage.key(i)
      if (key?.startsWith(prefix)) sessionStorage.removeItem(key)
    }
  } catch { /* Storage may be unavailable; in-memory state is reset by the caller. */ }
}
