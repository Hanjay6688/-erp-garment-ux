import { normalizeClientError } from '../lib/clientError'
import type { ClientAppError } from '../lib/clientError'

export type AppRole = 'OWNER' | 'ADMIN' | 'STAFF' | 'CUSTOMER'

export type AppUserProfile = {
  id: string
  authUserId: string
  fullName: string
  role: AppRole
  isActive: boolean
  rowVersion: number
}

type AnonymousIdentity = { status: 'ANONYMOUS'; error: ClientAppError | null }
type LoadingIdentity = { status: 'LOADING' }
type DemoIdentity = { status: 'DEMO' }
type AuthorizedIdentity = { status: 'AUTHORIZED'; profile: AppUserProfile }
type BlockedIdentity = {
  status: 'BLOCKED'
  reason: 'PROFILE_LOOKUP_FAILED' | 'PROFILE_NOT_LINKED' | 'PROFILE_INVALID' | 'ACCOUNT_INACTIVE' | 'ROLE_NOT_SUPPORTED'
  message: string
  errorCode: string | null
}

export type AuthIdentity = AnonymousIdentity | LoadingIdentity | DemoIdentity | AuthorizedIdentity | BlockedIdentity

type RawProfile = {
  id?: unknown
  auth_user_id?: unknown
  full_name?: unknown
  role?: unknown
  is_active?: unknown
  row_version?: unknown
}

export type ProfileReadResult =
  | { kind: 'MISSING' }
  | { kind: 'MALFORMED' }
  | { kind: 'FOUND'; profile: AppUserProfile }

export type ProfileFetcher = (authUserId: string) => Promise<{ data: unknown; error: unknown }>

function parseProfile(raw: RawProfile, expectedAuthUserId: string): AppUserProfile | null {
  const role = typeof raw.role === 'string' ? raw.role.toUpperCase() : ''
  const rowVersion = typeof raw.row_version === 'number' || typeof raw.row_version === 'string'
    ? Number(raw.row_version)
    : Number.NaN
  if (
    typeof raw.id !== 'string'
    || typeof raw.auth_user_id !== 'string'
    || raw.auth_user_id !== expectedAuthUserId
    || typeof raw.full_name !== 'string'
    || raw.full_name.trim() === ''
    || !['OWNER', 'ADMIN', 'STAFF', 'CUSTOMER'].includes(role)
    || typeof raw.is_active !== 'boolean'
    || !Number.isSafeInteger(rowVersion)
    || rowVersion < 1
  ) return null

  return {
    id: raw.id,
    authUserId: raw.auth_user_id,
    fullName: raw.full_name.trim(),
    role: role as AppRole,
    isActive: raw.is_active,
    rowVersion,
  }
}

export async function resolveOwnProfile(fetcher: ProfileFetcher, authUserId: string): Promise<ProfileReadResult> {
  const { data, error } = await fetcher(authUserId)
  if (error) throw normalizeClientError(error)
  if (!data) return { kind: 'MISSING' }
  if (typeof data !== 'object' || Array.isArray(data)) return { kind: 'MALFORMED' }
  const profile = parseProfile(data as RawProfile, authUserId)
  return profile ? { kind: 'FOUND', profile } : { kind: 'MALFORMED' }
}

export function identityFromProfileRead(result: ProfileReadResult): AuthIdentity {
  if (result.kind === 'MISSING') {
    return {
      status: 'BLOCKED',
      reason: 'PROFILE_NOT_LINKED',
      message: 'Akun Auth belum dipetakan ke profil ERP.',
      errorCode: 'APP_USER_NOT_FOUND',
    }
  }
  if (result.kind === 'MALFORMED') {
    return {
      status: 'BLOCKED',
      reason: 'PROFILE_INVALID',
      message: 'Profil ERP tidak lengkap atau tidak cocok dengan akun Auth.',
      errorCode: 'APP_USER_PROFILE_INVALID',
    }
  }

  const { profile } = result
  if (!profile.isActive) {
    return {
      status: 'BLOCKED',
      reason: 'ACCOUNT_INACTIVE',
      message: 'Akun ERP dinonaktifkan. Hubungi Owner untuk aktivasi.',
      errorCode: 'APP_USER_INACTIVE',
    }
  }
  if (profile.role !== 'OWNER' && profile.role !== 'ADMIN') {
    return {
      status: 'BLOCKED',
      reason: 'ROLE_NOT_SUPPORTED',
      message: `Role ${profile.role} belum boleh masuk karena UX dan RLS per-role belum dipadankan.`,
      errorCode: 'ROLE_UX_RLS_NOT_READY',
    }
  }
  return { status: 'AUTHORIZED', profile }
}

export function identityFromProfileLookupError(error: unknown): AuthIdentity {
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
  if (event === 'TOKEN_REFRESHED' && sameVerifiedUser) {
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
