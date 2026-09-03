import { describe, expect, it } from 'vitest'
import { authGateMode } from './AuthGate'
import type { AuthIdentity } from './AuthProvider'

describe('AuthGate policy', () => {
  it('allows only demo or a policy-authorized identity', () => {
    const authorized: AuthIdentity = {
      status: 'AUTHORIZED',
      profile: {
        id: 'profile-id',
        authUserId: 'auth-id',
        fullName: 'Owner',
        roleId: 'role-id',
        role: 'OWNER',
        roleName: 'Owner',
        isActive: true,
        rowVersion: 1,
        roleRowVersion: 1,
      },
      permissions: ['settings.access.manage'],
      externalPortals: { mandor: 'NOT CONNECTED', laundry: 'NOT CONNECTED', store: 'NOT CONNECTED' },
    }
    expect(authGateMode({ status: 'DEMO' })).toBe('ALLOW')
    expect(authGateMode(authorized)).toBe('ALLOW')
    expect(authGateMode({ status: 'LOADING' })).toBe('LOADING')
    expect(authGateMode({ status: 'ANONYMOUS', error: null })).toBe('LOGIN')
    expect(authGateMode({
      status: 'BLOCKED',
      reason: 'ROLE_INVALID',
      message: 'blocked',
      errorCode: 'ROLE_UX_RLS_NOT_READY',
    })).toBe('BLOCKED')
  })
})
