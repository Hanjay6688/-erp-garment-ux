import { createHash } from 'node:crypto'
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'
import { assertNoForbiddenBuildSecrets } from './build-preflight.mjs'

export const UAT_AUTH_RUNTIME_MODE = 'UAT_AUTH_SIMULATION'
export const ERP_ENTENG_UAT_URL = 'https://siimvrusnzxexizpyoib.supabase.co'
export const ERP_ENTENG_PUBLISHABLE_KEY_SHA256 = '4a393f01d18cf637ca1e38967790d4c76a2478d687335b6cb948a1bff8a017cf'

const mockKeyFlag = 'ERP_UAT_AUTH_ALLOW_MOCK_KEY'

const allowedSupabaseVariables = new Set([
  'VITE_SUPABASE_URL',
  'VITE_SUPABASE_PUBLISHABLE_KEY',
  'VITE_SUPABASE_ANON_KEY',
])

export class UatAuthEnvironmentError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'UatAuthEnvironmentError'
    this.code = code
  }
}

function environmentValue(environment, name) {
  const value = environment[name]
  return typeof value === 'string' ? value : ''
}

function fail(code, message) {
  throw new UatAuthEnvironmentError(code, message)
}

export function assertUatAuthBuildEnvironment(environment = process.env) {
  // This check reports variable names only and never reads a forbidden value
  // into an error message.
  assertNoForbiddenBuildSecrets(environment)

  const unexpectedSupabaseVariable = Object.entries(environment).find(([name, value]) => (
    name.startsWith('VITE_SUPABASE_')
    && typeof value === 'string'
    && value.trim() !== ''
    && !allowedSupabaseVariables.has(name)
  ))
  if (unexpectedSupabaseVariable) {
    fail(
      'UAT_UNEXPECTED_SUPABASE_VARIABLE',
      `Unexpected Supabase browser variable: ${unexpectedSupabaseVariable[0]}.`,
    )
  }

  const mode = environmentValue(environment, 'VITE_ERP_RUNTIME_MODE')
  if (mode !== UAT_AUTH_RUNTIME_MODE) {
    fail('UAT_RUNTIME_MODE_REQUIRED', 'UAT Auth build requires the explicit UAT_AUTH_SIMULATION mode.')
  }

  const supabaseUrl = environmentValue(environment, 'VITE_SUPABASE_URL')
  if (supabaseUrl !== ERP_ENTENG_UAT_URL) {
    fail('UAT_TARGET_INVALID', 'UAT Auth build target must be the exact ERP Enteng HTTPS endpoint.')
  }

  const legacyAnonKey = environmentValue(environment, 'VITE_SUPABASE_ANON_KEY')
  if (legacyAnonKey) {
    fail(
      'UAT_LEGACY_ANON_KEY_FORBIDDEN',
      'Dedicated UAT Auth artifacts require the modern publishable-key variable only.',
    )
  }

  const publishableKey = environmentValue(environment, 'VITE_SUPABASE_PUBLISHABLE_KEY')
  // Supabase publishable keys are case-sensitive and may contain uppercase
  // characters. Keep the prefix exact while accepting the documented opaque
  // key alphabet; identity is still pinned by SHA-256 below.
  if (!/^sb_publishable_[a-z0-9._-]{16,}$/i.test(publishableKey)) {
    fail(
      'UAT_PUBLISHABLE_KEY_INVALID',
      'Dedicated UAT Auth artifacts require one valid modern Supabase publishable key.',
    )
  }

  const mockKeyOptIn = environmentValue(environment, mockKeyFlag)
  if (mockKeyOptIn !== '' && mockKeyOptIn !== '1') {
    fail('UAT_MOCK_KEY_FLAG_INVALID', 'The local mock-key opt-in must be exactly 1 when used.')
  }

  const keyDigest = createHash('sha256').update(publishableKey, 'utf8').digest('hex')
  const usesPinnedKey = keyDigest === ERP_ENTENG_PUBLISHABLE_KEY_SHA256
  const usesExplicitMockKey = mockKeyOptIn === '1'
    && /^sb_publishable_mock_[a-z0-9._-]{16,}$/.test(publishableKey)

  if (mockKeyOptIn === '1' && !usesExplicitMockKey) {
    fail('UAT_MOCK_KEY_INVALID', 'The local mock-key opt-in only accepts an unmistakable mock publishable key.')
  }
  if (!usesPinnedKey && !usesExplicitMockKey) {
    fail(
      'UAT_PUBLISHABLE_KEY_IDENTITY_MISMATCH',
      'UAT Auth build requires the reviewed ERP Enteng publishable-key identity.',
    )
  }

  return Object.freeze({
    mode,
    supabaseUrl,
    publishableKey,
    keyIdentity: usesPinnedKey ? 'pinned' : 'mock',
  })
}

export function assertUatAuthReleaseEnvironment(environment = process.env) {
  const result = assertUatAuthBuildEnvironment(environment)
  if (result.keyIdentity !== 'pinned') {
    fail('UAT_MOCK_KEY_RELEASE_FORBIDDEN', 'Mock browser keys are restricted to local artifact verification.')
  }
  return result
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href
if (invokedDirectly) {
  const releaseCheck = process.argv.slice(2).includes('--release')
  const result = releaseCheck
    ? assertUatAuthReleaseEnvironment()
    : assertUatAuthBuildEnvironment()
  console.log(`UAT Auth build environment passed: fixed mode, fixed ERP Enteng target, ${result.keyIdentity} browser-key identity (value not printed).`)
}
