import type { SupabaseClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined
let pending: Promise<SupabaseClient | null> | null = null
export function getSupabase(): Promise<SupabaseClient | null> {
  if (!url || !key) return Promise.resolve(null)
  if (!pending) pending = import('@supabase/supabase-js').then(({createClient}) => createClient(url, key)).catch(error => { pending = null; throw error })
  return pending
}
