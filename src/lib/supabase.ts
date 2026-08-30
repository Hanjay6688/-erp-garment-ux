import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import type { UatRuntimeConfig } from '../config/runtime'
import type { PreconnectDatabase } from '../types/database.preconnect'

let singleton: SupabaseClient<PreconnectDatabase> | null = null
let singletonFingerprint = ''

export function getUatSupabaseClient(config: UatRuntimeConfig): SupabaseClient<PreconnectDatabase> {
  const fingerprint = `${config.projectRef}:${config.supabaseUrl}:${config.browserKey}`
  if (singleton && singletonFingerprint !== fingerprint) {
    throw new Error('Supabase client sudah dikunci ke konfigurasi runtime lain.')
  }
  if (!singleton) {
    singleton = createClient<PreconnectDatabase>(config.supabaseUrl, config.browserKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
      },
      global: {
        headers: {
          'X-Client-Info': 'atelier-garment-erp-uat-auth-simulation',
        },
      },
    })
    singletonFingerprint = fingerprint
  }
  return singleton
}
