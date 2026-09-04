import { normalizeClientError } from '../lib/clientError'
import type { ClientAppError } from '../lib/clientError'
import type { PermissionKey } from './accessCatalog'

export type AppRole = string

export type AppUserProfile = {
  id: string
  authUserId: string
  fullName: string
  roleId: string
  role: AppRole
  roleName: string
  isActive: boolean
  rowVersion: number
  roleRowVersion: number
}

export type AuthorizedAccess = {
  profile: AppUserProfile
  permissions: readonly PermissionKey[]
  externalPortals: Readonly<Record<'mandor' | 'laundry' | 'store', 'NOT CONNECTED'>>
}

type AnonymousIdentity = { status: 'ANONYMOUS'; error: ClientAppError | null }
type LoadingIdentity = { status: 'LOADING' }
type DemoIdentity = { status: 'DEMO' }
type AuthorizedIdentity = { status: 'AUTHORIZED' } & AuthorizedAccess
type BlockedIdentity = {
  status: 'BLOCKED'
  reason: 'PROFILE_LOOKUP_FAILED' | 'PROFILE_NOT_LINKED' | 'PROFILE_INVALID' | 'ACCOUNT_INACTIVE' | 'ROLE_INVALID'
  message: string
  errorCode: string | null
}

export type AuthIdentity = AnonymousIdentity | LoadingIdentity | DemoIdentity | AuthorizedIdentity | BlockedIdentity

type RawAccess = {
  allowed?: unknown
  reason?: unknown
  profile?: unknown
  permissions?: unknown
  external_portals?: unknown
}

type RawProfile = {
  id?: unknown
  auth_user_id?: unknown
  full_name?: unknown
  role_id?: unknown
  role_code?: unknown
  role_name?: unknown
  is_active?: unknown
  row_version?: unknown
  role_row_version?: unknown
}

type DeniedReason = 'APP_USER_NOT_FOUND' | 'APP_USER_INACTIVE' | 'APP_ROLE_NOT_FOUND' | 'APP_ROLE_INACTIVE'

export type AccessReadResult =
  | { kind: 'DENIED'; reason: DeniedReason }
  | { kind: 'MALFORMED' }
  | ({ kind: 'FOUND' } & AuthorizedAccess)

export type AccessFetcher = () => Promise<{ data: unknown; error: unknown }>

function positiveInteger(value: unknown) {
  const parsed = typeof value === 'number' || typeof value === 'string' ? Number(value) : Number.NaN
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null
}

function parseProfile(raw: RawProfile, expectedAuthUserId: string): AppUserProfile | null {
  const rowVersion = positiveInteger(raw.row_version)
  const roleRowVersion = positiveInteger(raw.role_row_version)
  if (
    typeof raw.id !== 'string'
    || typeof raw.auth_user_id !== 'string'
    || raw.auth_user_id !== expectedAuthUserId
    || typeof raw.full_name !== 'string'
    || raw.full_name.trim() === ''
    || typeof raw.role_id !== 'string'
    || typeof raw.role_code !== 'string'
    || !/^[A-Z][A-Z0-9_]{1,31}$/.test(raw.role_code)
    || typeof raw.role_name !== 'string'
    || raw.role_name.trim() === ''
    || raw.is_active !== true
    || rowVersion === null
    || roleRowVersion === null
  ) return null

  return {
    id: raw.id,
    authUserId: raw.auth_user_id,
    fullName: raw.full_name.trim(),
    roleId: raw.role_id,
    role: raw.role_code,
    roleName: raw.role_name.trim(),
    isActive: true,
    rowVersion,
    roleRowVersion,
  }
}

function parsePermissions(raw: unknown) {
  if (!Array.isArray(raw)) return null
  if (raw.some((key) => typeof key !== 'string' || !/^[a-z][a-z0-9_.]+$/.test(key))) return null
  return [...new Set(raw as string[])].sort()
}

function parseExternalPortals(raw: unknown): AuthorizedAccess['externalPortals'] | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const value = raw as Record<string, unknown>
  if (value.mandor !== 'NOT CONNECTED' || value.laundry !== 'NOT CONNECTED' || value.store !== 'NOT CONNECTED') return null
  return { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' }
}

export async function resolveOwnAccess(fetcher: AccessFetcher, expectedAuthUserId: string): Promise<AccessReadResult> {
  const { data, error } = await fetcher()
  if (error) throw normalizeClientError(error)
  if (!data || typeof data !== 'object' || Array.isArray(data)) return { kind: 'MALFORMED' }
  const raw = data as RawAccess

  if (raw.allowed === false) {
    const reason = String(raw.reason)
    if (['APP_USER_NOT_FOUND', 'APP_USER_INACTIVE', 'APP_ROLE_NOT_FOUND', 'APP_ROLE_INACTIVE'].includes(reason)) {
      return { kind: 'DENIED', reason: reason as DeniedReason }
    }
    return { kind: 'MALFORMED' }
  }
  if (raw.allowed !== true || !raw.profile || typeof raw.profile !== 'object' || Array.isArray(raw.profile)) {
    return { kind: 'MALFORMED' }
  }

  const profile = parseProfile(raw.profile as RawProfile, expectedAuthUserId)
  const permissions = parsePermissions(raw.permissions)
  const externalPortals = parseExternalPortals(raw.external_portals)
  if (!profile || !permissions || !externalPortals) return { kind: 'MALFORMED' }
  return { kind: 'FOUND', profile, permissions, externalPortals }
}

export function identityFromAccessRead(result: AccessReadResult): AuthIdentity {
  if (result.kind === 'MALFORMED') {
    return {
      status: 'BLOCKED',
      reason: 'PROFILE_INVALID',
      message: 'Bundle akses ERP tidak lengkap atau tidak cocok dengan akun Auth.',
      errorCode: 'APP_ACCESS_BUNDLE_INVALID',
    }
  }
  if (result.kind === 'DENIED') {
    if (result.reason === 'APP_USER_NOT_FOUND') {
      return {
        status: 'BLOCKED',
        reason: 'PROFILE_NOT_LINKED',
        message: 'Akun Auth belum dipetakan ke pengguna ERP.',
        errorCode: result.reason,
      }
    }
    if (result.reason === 'APP_USER_INACTIVE') {
      return {
        status: 'BLOCKED',
        reason: 'ACCOUNT_INACTIVE',
        message: 'Akun ERP dinonaktifkan. Hubungi Owner untuk aktivasi.',
        errorCode: result.reason,
      }
    }
    return {
      status: 'BLOCKED',
      reason: 'ROLE_INVALID',
      message: 'Role ERP tidak ada atau sedang dinonaktifkan.',
      errorCode: result.reason,
    }
  }
  return {
    status: 'AUTHORIZED',
    profile: result.profile,
    permissions: result.permissions,
    externalPortals: result.externalPortals,
  }
}

export function identityFromAccessLookupError(error: unknown): AuthIdentity {
  const normalized = normalizeClientError(error)
  return {
    status: 'BLOCKED',
    reason: 'PROFILE_LOOKUP_FAILED',
    message: normalized.message,
    errorCode: normalized.code,
  }
}

export type AuthEventPlan = {
  immediateIdentity: AuthIdentity | null
  invalidatePending: boolean
  refreshAfterCallback: boolean
}

export function planAuthEvent(
  current: AuthIdentity,
  event: string,
  sessionAuthUserId: string | null,
): AuthEventPlan {
  if (event === 'SIGNED_OUT' || !sessionAuthUserId) {
    return {
      immediateIdentity: { status: 'ANONYMOUS', error: null },
      invalidatePending: true,
      refreshAfterCallback: false,
    }
  }

  const sameVerifiedUser = current.status === 'AUTHORIZED'
    && current.profile.authUserId === sessionAuthUserId
  // Supabase broadcasts a same-session SIGNED_IN event across browser tabs.
  // Keep the already verified UI mounted so an operator's unsubmitted form is
  // not destroyed, while still re-reading the profile and permissions. A
  // different user remains synchronously locked below.
  if (sameVerifiedUser && (event === 'TOKEN_REFRESHED' || event === 'SIGNED_IN')) {
    return {
      immediateIdentity: null,
      invalidatePending: true,
      refreshAfterCallback: true,
    }
  }

  return {
    immediateIdentity: { status: 'LOADING' },
    invalidatePending: true,
    refreshAfterCallback: true,
  }
}
