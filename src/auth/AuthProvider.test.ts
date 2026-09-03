import { describe, expect, it, vi } from 'vitest'
import {
  identityFromAccessLookupError,
  identityFromAccessRead,
  planAuthEvent,
  resolveOwnAccess,
} from './authPolicy'
import type { AppUserProfile, AuthIdentity } from './authPolicy'

const authUserId = '018f7c2e-7b8a-7ab1-8d4a-1234567890ab'
const baseRow = {
  id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ac',
  auth_user_id: authUserId,
  full_name: 'Owner UAT',
  role_id: '018f7c2e-7b8a-7ab1-8d4a-1234567890ad',
  role_code: 'OWNER',
  role_name: 'Owner',
  is_active: true,
  row_version: 1,
  role_row_version: 1,
}

const baseAccess = {
  allowed: true,
  profile: baseRow,
  permissions: ['settings.access.manage', 'production.wip.view'],
  external_portals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
}

async function identityFor(data: unknown) {
  const fetcher = vi.fn(async () => ({ data, error: null }))
  const read = await resolveOwnAccess(fetcher, authUserId)
  expect(fetcher).toHaveBeenCalledExactlyOnceWith()
  return identityFromAccessRead(read)
}

describe('AuthProvider access policy with mocked facade responses', () => {
  it('blocks an Auth account without a mapped ERP user', async () => {
    await expect(identityFor({ allowed: false, reason: 'APP_USER_NOT_FOUND' })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'PROFILE_NOT_LINKED', errorCode: 'APP_USER_NOT_FOUND',
    })
  })

  it('distinguishes malformed or mismatched access bundles', async () => {
    await expect(identityFor({
      ...baseAccess,
      profile: { ...baseRow, auth_user_id: 'different-user' },
    })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'PROFILE_INVALID', errorCode: 'APP_ACCESS_BUNDLE_INVALID',
    })
    await expect(identityFor({ ...baseAccess, permissions: ['INVALID KEY'] })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'PROFILE_INVALID',
    })
  })

  it('blocks inactive users and missing or inactive roles', async () => {
    await expect(identityFor({ allowed: false, reason: 'APP_USER_INACTIVE' })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'ACCOUNT_INACTIVE',
    })
    await expect(identityFor({ allowed: false, reason: 'APP_ROLE_INACTIVE' })).resolves.toMatchObject({
      status: 'BLOCKED', reason: 'ROLE_INVALID',
    })
  })

  it('authorizes any valid active role bundle without a frontend role allowlist', async () => {
    const custom = {
      ...baseAccess,
      profile: { ...baseRow, role_code: 'CUSTOM_MULTI', role_name: 'Multi Modul' },
    }
    await expect(identityFor(custom)).resolves.toMatchObject({
      status: 'AUTHORIZED',
      profile: { authUserId, role: 'CUSTOM_MULTI', roleName: 'Multi Modul' },
      permissions: ['production.wip.view', 'settings.access.manage'],
      externalPortals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
    })
  })

  it('authorizes a valid active OWNER bundle', async () => {
    await expect(identityFor(baseAccess)).resolves.toMatchObject({
      status: 'AUTHORIZED',
      profile: { authUserId, fullName: 'Owner UAT', role: 'OWNER', isActive: true, rowVersion: 1 },
    })
  })

  it('normalizes PGRST106 into a fail-closed access lookup block', async () => {
    let caught: unknown
    try {
      await resolveOwnAccess(async () => ({ data: null, error: { code: 'PGRST106', message: 'schema unavailable' } }), authUserId)
    } catch (error) {
      caught = error
    }
    expect(identityFromAccessLookupError(caught)).toMatchObject({
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
    roleId: baseRow.role_id,
    role: 'OWNER',
    roleName: 'Owner',
    isActive: true,
    rowVersion: 1,
    roleRowVersion: 1,
  }
  const authorized: AuthIdentity = {
    status: 'AUTHORIZED',
    profile,
    permissions: baseAccess.permissions,
    externalPortals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
  }

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
