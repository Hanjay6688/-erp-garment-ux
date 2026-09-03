import { describe, expect, it } from 'vitest'
import {
  ERP_ENTENG_UAT_PROJECT_REF,
  ERP_GARMENT_PRODUCTION_PROJECT_REF,
  parseRuntimeConfig,
  RuntimeConfigError,
} from './runtime'

const publishableKey = 'sb_publishable_12345678901234567890'

function errorCode(operation: () => unknown) {
  try {
    operation()
    return null
  } catch (error) {
    return error instanceof RuntimeConfigError ? error.code : 'UNEXPECTED_ERROR'
  }
}

function unsignedJwt(payload: Record<string, unknown>) {
  const encode = (value: object) => globalThis.btoa(JSON.stringify(value)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
  return `${encode({ alg: 'none' })}.${encode(payload)}.signature`
}

describe('parseRuntimeConfig', () => {
  it('defaults to an environment-free demo simulation', () => {
    expect(parseRuntimeConfig({})).toEqual({
      mode: 'DEMO_SIMULATION',
      authMode: 'DISABLED',
      businessDataMode: 'SIMULATION',
      businessRpcEnabled: false,
      accessControlMode: 'SIMULATION',
      patternMode: 'SIMULATION',
      cuttingMode: 'SIMULATION',
      distributionMode: 'SIMULATION',
      wipStatusMode: 'SIMULATION',
    })
  })

  it('does not silently ignore connection variables in demo', () => {
    expect(errorCode(() => parseRuntimeConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co' })))
      .toBe('DEMO_SUPABASE_ENV_FORBIDDEN')
  })

  it('only accepts the two declared runtime modes', () => {
    expect(errorCode(() => parseRuntimeConfig({ VITE_ERP_RUNTIME_MODE: 'PRODUCTION' })))
      .toBe('RUNTIME_MODE_UNSUPPORTED')
  })

  it('accepts ERP Enteng UAT with one publishable browser key', () => {
    const runtime = parseRuntimeConfig({
      VITE_ERP_RUNTIME_MODE: 'UAT_AUTH_SIMULATION',
      VITE_SUPABASE_URL: `https://${ERP_ENTENG_UAT_PROJECT_REF}.supabase.co/`,
      VITE_SUPABASE_PUBLISHABLE_KEY: publishableKey,
    })
    expect(runtime).toMatchObject({
      mode: 'UAT_AUTH_SIMULATION',
      projectRef: ERP_ENTENG_UAT_PROJECT_REF,
      businessDataMode: 'PARTIAL_CONNECTED',
      businessRpcEnabled: true,
      accessControlMode: 'CONNECTED',
      patternMode: 'CONNECTED',
      cuttingMode: 'CONNECTED',
      distributionMode: 'CONNECTED',
      wipStatusMode: 'CONNECTED',
    })
  })

  it('accepts a legacy anon browser key for ERP Enteng', () => {
    const runtime = parseRuntimeConfig({
      VITE_ERP_RUNTIME_MODE: 'UAT_AUTH_SIMULATION',
      VITE_SUPABASE_URL: `https://${ERP_ENTENG_UAT_PROJECT_REF}.supabase.co`,
      VITE_SUPABASE_ANON_KEY: unsignedJwt({ role: 'anon', ref: ERP_ENTENG_UAT_PROJECT_REF }),
    })
    expect(runtime.mode).toBe('UAT_AUTH_SIMULATION')
  })

  it('rejects the production project explicitly', () => {
    expect(errorCode(() => parseRuntimeConfig({
      VITE_ERP_RUNTIME_MODE: 'UAT_AUTH_SIMULATION',
      VITE_SUPABASE_URL: `https://${ERP_GARMENT_PRODUCTION_PROJECT_REF}.supabase.co`,
      VITE_SUPABASE_PUBLISHABLE_KEY: publishableKey,
    }))).toBe('PRODUCTION_TARGET_FORBIDDEN')
  })

  it('does not fall back when a UAT variable is missing', () => {
    expect(errorCode(() => parseRuntimeConfig({
      VITE_ERP_RUNTIME_MODE: 'UAT_AUTH_SIMULATION',
      VITE_SUPABASE_URL: `https://${ERP_ENTENG_UAT_PROJECT_REF}.supabase.co`,
    }))).toBe('UAT_BROWSER_KEY_REQUIRED')
  })

  it('rejects a legacy service-role credential placed in the anon-key slot', () => {
    expect(errorCode(() => parseRuntimeConfig({
      VITE_ERP_RUNTIME_MODE: 'UAT_AUTH_SIMULATION',
      VITE_SUPABASE_URL: `https://${ERP_ENTENG_UAT_PROJECT_REF}.supabase.co`,
      VITE_SUPABASE_ANON_KEY: unsignedJwt({ role: 'service_role', ref: ERP_ENTENG_UAT_PROJECT_REF }),
    }))).toBe('BROWSER_KEY_INVALID')
  })
})
