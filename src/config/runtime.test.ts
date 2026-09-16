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
      bsResolutionMode: 'SIMULATION',
      laundryMode: 'SIMULATION',
      qcFinalMode: 'SIMULATION',
      fgHandoffMode: 'SIMULATION',
    })
  })

  it('does not silently ignore connection variables in demo', () => {
    expect(errorCode(() => parseRuntimeConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co' })))
      .toBe('DEMO_SUPABASE_ENV_FORBIDDEN')
  })

  it('rejects undeclared runtime modes', () => {
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
      bsResolutionMode: 'CONNECTED',
      laundryMode: 'CONNECTED',
      qcFinalMode: 'CONNECTED',
      fgHandoffMode: 'BLOCKED_UNTIL_AUTHORITATIVE',
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

describe('owner-authorized disposable application target', () => {
  const build = { mode: 'cp6-disposable-test', pageOrigin: 'http://127.0.0.1:4176' }
  const environment = {
    VITE_ERP_RUNTIME_MODE: 'DISPOSABLE_TEST',
    VITE_SUPABASE_URL: 'http://127.0.0.1:54328',
    VITE_SUPABASE_ANON_KEY: unsignedJwt({ role: 'anon', iss: 'supabase-demo' }),
  }

  it('opens the same connected modules only in the exact disposable build and page origin', () => {
    expect(parseRuntimeConfig(environment, build)).toMatchObject({
      mode: 'DISPOSABLE_TEST', projectRef: 'cp6-disposable', authMode: 'LOCAL_SUPABASE',
      laundryMode: 'CONNECTED', qcFinalMode: 'CONNECTED', fgHandoffMode: 'BLOCKED_UNTIL_AUTHORITATIVE',
    })
    expect(errorCode(() => parseRuntimeConfig(environment))).toBe('DISPOSABLE_BUILD_REQUIRED')
    expect(errorCode(() => parseRuntimeConfig(environment, { ...build, mode: 'production' })))
      .toBe('DISPOSABLE_BUILD_REQUIRED')
    expect(errorCode(() => parseRuntimeConfig(environment, { ...build, pageOrigin: 'https://example.test' })))
      .toBe('DISPOSABLE_BUILD_REQUIRED')
  })

  it.each([
    `https://${ERP_ENTENG_UAT_PROJECT_REF}.supabase.co`,
    `https://${ERP_GARMENT_PRODUCTION_PROJECT_REF}.supabase.co`,
    'http://localhost:54328', 'http://127.1:54328', 'http://2130706433:54328',
    'http://127.0.0.1:54321', 'http://127.0.0.1:54328/',
    'http://127.0.0.1:54328@evil.example', 'http://127.0.0.1:54328?target=hosted',
    'https://127.0.0.1:54328',
  ])('rejects every target other than the fixed disposable API: %s', (url) => {
    expect(errorCode(() => parseRuntimeConfig({ ...environment, VITE_SUPABASE_URL: url }, build)))
      .toBe('DISPOSABLE_TARGET_FORBIDDEN')
  })

  it.each([
    unsignedJwt({ role: 'service_role' }), unsignedJwt({ role: 'authenticated' }),
    unsignedJwt({ role: 'anon', ref: ERP_ENTENG_UAT_PROJECT_REF }),
    unsignedJwt({ role: 'anon', ref: ERP_GARMENT_PRODUCTION_PROJECT_REF }),
    'sb_secret_not_a_browser_credential', publishableKey,
  ])('rejects privileged, hosted or unidentified browser credentials', (key) => {
    expect(errorCode(() => parseRuntimeConfig({ ...environment, VITE_SUPABASE_ANON_KEY: key }, build)))
      .toBe('DISPOSABLE_BROWSER_KEY_INVALID')
  })

  it('does not loosen the original UAT target guard', () => {
    expect(errorCode(() => parseRuntimeConfig({ ...environment, VITE_ERP_RUNTIME_MODE: 'UAT_AUTH_SIMULATION' }, build)))
      .toBe('UAT_URL_INVALID')
  })
})
