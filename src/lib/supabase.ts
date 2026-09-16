import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import type { ConnectedRuntimeConfig, UatRuntimeConfig } from '../config/runtime'
import type { PreconnectDatabase } from '../types/database.preconnect'

let singleton: SupabaseClient<PreconnectDatabase> | null = null
let singletonFingerprint = ''
let inviteSingleton: SupabaseClient<PreconnectDatabase> | null = null
let inviteSingletonFingerprint = ''

export const UAT_INVITE_AUTH_OPTIONS = Object.freeze({
  storageKey: 'atelier-garment-erp-uat-invite-memory',
  autoRefreshToken: false,
  persistSession: false,
  detectSessionInUrl: false,
} as const)

export function getUatSupabaseClient(config: ConnectedRuntimeConfig): SupabaseClient<PreconnectDatabase> {
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
        ...(config.mode === 'DISPOSABLE_TEST' ? {
          fetch: (input: RequestInfo | URL, init?: RequestInit) => {
            const target = new URL(input instanceof Request ? input.url : String(input))
            if (target.origin !== config.supabaseUrl) throw new Error('Target jaringan disposable ditolak.')
            return fetch(input, { ...init, redirect: 'error' })
          },
        } : {}),
        headers: {
          'X-Client-Info': config.mode === 'DISPOSABLE_TEST'
            ? 'atelier-garment-erp-disposable-test'
            : 'atelier-garment-erp-uat-auth-simulation',
        },
      },
    })
    singletonFingerprint = fingerprint
  }
  return singleton
}

export function getUatInviteSupabaseClient(config: UatRuntimeConfig): SupabaseClient<PreconnectDatabase> {
  const fingerprint = `${config.projectRef}:${config.supabaseUrl}:${config.browserKey}`
  if (inviteSingleton && inviteSingletonFingerprint !== fingerprint) {
    throw new Error('Supabase invite client sudah dikunci ke konfigurasi runtime lain.')
  }
  if (!inviteSingleton) {
    inviteSingleton = createClient<PreconnectDatabase>(config.supabaseUrl, config.browserKey, {
      auth: UAT_INVITE_AUTH_OPTIONS,
      global: {
        headers: {
          'X-Client-Info': 'atelier-garment-erp-uat-invite-acceptance',
        },
      },
    })
    inviteSingletonFingerprint = fingerprint
  }
  return inviteSingleton
}
