import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const exactForbiddenNames = new Set([
  'SUPABASE_SERVICE_ROLE_KEY',
  'SUPABASE_SECRET_KEY',
  'VITE_SUPABASE_SERVICE_ROLE_KEY',
  'VITE_SUPABASE_SECRET_KEY',
])

export function isForbiddenBuildSecretName(name) {
  const upper = name.toUpperCase()
  if (exactForbiddenNames.has(upper)) return true
  if (!upper.startsWith('VITE_')) return false
  return /(?:SERVICE_?ROLE|SECRET(?:_?KEY)?|PRIVATE_?KEY)/.test(upper)
}

function isServerKeyValue(value) {
  if (/^sb_secret_/i.test(value)) return true
  const segments = value.split('.')
  if (segments.length !== 3) return false
  try {
    const payload = segments[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = payload.padEnd(Math.ceil(payload.length / 4) * 4, '=')
    return JSON.parse(Buffer.from(padded, 'base64').toString('utf8'))?.role === 'service_role'
  } catch {
    return false
  }
}

export function findForbiddenBuildSecrets(environment) {
  return Object.entries(environment)
    .filter(([name, value]) => {
      if (typeof value !== 'string' || value.trim() === '') return false
      if (isForbiddenBuildSecretName(name)) return true
      return ['VITE_SUPABASE_PUBLISHABLE_KEY', 'VITE_SUPABASE_ANON_KEY'].includes(name)
        && isServerKeyValue(value.trim())
    })
    .map(([name]) => name)
    .sort()
}

export function assertNoForbiddenBuildSecrets(environment = process.env) {
  const forbidden = findForbiddenBuildSecrets(environment)
  if (forbidden.length === 0) return
  throw new Error(
    `[FORBIDDEN_BUILD_SECRET] Refusing frontend build. Remove server-only environment variable(s): ${forbidden.join(', ')}. Values were not read or printed.`,
  )
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href
if (invokedDirectly) assertNoForbiddenBuildSecrets()
