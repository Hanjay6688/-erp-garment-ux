import { describe, expect, it, vi } from 'vitest'
import {
  identityFromProfileLookupError,
  identityFromProfileRead,
  planAuthEvent,
  resolveOwnProfile,
} from './authPolicy'
import type { AppUserProfile, AuthIdentity } from './authPolicy'

const authUserId = '018f7c2e-7b8a-7ab1-8d4a-1234567890ab'
const baseRow = {
  id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ac',
  auth_user_id: authUserId,
  full_name: 'Owner UAT',
  role: 'OWNER',
  is_active: true,
  row_version: 1,
}

async function identityFor(data: unknown) {
  const fetcher = vi.fn(async () => ({ data, error: null }))
  const read = await resolveOwnProfile(fetcher, authUserId)
  expect(fetcher).toHaveBeenCalledExactlyOnceWith(authUserId)
  return identityFromProfileRead(read)
}

describe('AuthProvider profile policy with mocked facade responses', () => {
  it('blocks an Auth account without a mapped profile', async () => {
    await expect(identityFor(null)).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'PROFILE_NOT_LINKED', errorCode: 'APP_USER_NOT_FOUND',
    })
  })

  it('distinguishes malformed or mismatched profile data', async () => {
    await expect(identityFor({ ...baseRow, auth_user_id: 'different-user' })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'PROFILE_INVALID', errorCode: 'APP_USER_PROFILE_INVALID',
    })
    await expect(identityFor({ ...baseRow, full_name: '' })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'PROFILE_INVALID',
    })
  })

  it('blocks inactive and STAFF profiles', async () => {
    await expect(identityFor({ ...baseRow, is_active: false })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'ACCOUNT_INACTIVE',
    })
    await expect(identityFor({ ...baseRow, role: 'STAFF' })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'ROLE_NOT_SUPPORTED',
    })
  })

  it('authorizes a valid active OWNER profile', async () => {
    await expect(identityFor(baseRow)).resolves.toMatchObject({
      status: 'AUTHORIZED',
      profile: { authUserId, fullName: 'Owner UAT', role: 'OWNER', isActive: true, rowVersion: 1 },
    })
  })

  it('normalizes PGRST106 into a fail-closed profile lookup block', async () => {
    let caught: unknown
    try {
      await resolveOwnProfile(async () => ({ data: null, error: { code: 'PGRST106', message: 'schema unavailable' } }), authUserId)
    } catch (error) {
      caught = error
    }
    expect(identityFromProfileLookupError(caught)).toMatchObject({
      status: 'BLOCKED',
      reason: 'PROFILE_LOOKUP_FAILED',
      errorCode: 'PROFILE_API_SCHEMA_UNAVAILABLE',
    })
  })
})

describe('Auth subscription ordering', () => {
  const profile: AppUserProfile = {
    id: baseRow.id,
    authUserId,
    fullName: baseRow.full_name,
    role: 'OWNER',
    isActive: true,
    rowVersion: 1,
  }
  const authorized: AuthIdentity = { status: 'AUTHORIZED', profile }

  it('locks SIGNED_OUT synchronously and invalidates an older profile response', () => {
    let identity: AuthIdentity = authorized
    let sequence = 4
    const staleRequestSequence = sequence
    const plan = planAuthEvent(identity, 'SIGNED_OUT', null)
    if (plan.invalidatePending) sequence += 1
    if (plan.immediateIdentity) identity = plan.immediateIdentity

    // This simulates a getUser/profile request that started before SIGNED_OUT.
    if (staleRequestSequence === sequence) identity = authorized
    expect(identity).toEqual({ status: 'ANONYMOUS', error: null })
    expect(plan.refreshAfterCallback).toBe(false)
  })

  it('preserves UI only for TOKEN_REFRESHED on the same verified user', () => {
    expect(planAuthEvent(authorized, 'TOKEN_REFRESHED', authUserId)).toEqual({
      immediateIdentity: null,
      invalidatePending: true,
      refreshAfterCallback: true,
    })
    expect(planAuthEvent(authorized, 'TOKEN_REFRESHED', 'switched-user')).toMatchObject({
      immediateIdentity: { status: 'LOADING' },
      refreshAfterCallback: true,
    })
  })

  it('locks account-switch events before scheduling the verified refresh', () => {
    expect(planAuthEvent(authorized, 'SIGNED_IN', 'switched-user')).toEqual({
      immediateIdentity: { status: 'LOADING' },
      invalidatePending: true,
      refreshAfterCallback: true,
    })
  })
})
