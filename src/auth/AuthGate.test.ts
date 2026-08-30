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
        role: 'OWNER',
        isActive: true,
        rowVersion: 1,
      },
    }
    expect(authGateMode({ status: 'DEMO' })).toBe('ALLOW')
    expect(authGateMode(authorized)).toBe('ALLOW')
    expect(authGateMode({ status: 'LOADING' })).toBe('LOADING')
    expect(authGateMode({ status: 'ANONYMOUS', error: null })).toBe('LOGIN')
    expect(authGateMode({
      status: 'BLOCKED',
      reason: 'ROLE_NOT_SUPPORTED',
      message: 'blocked',
      errorCode: 'ROLE_UX_RLS_NOT_READY',
    })).toBe('BLOCKED')
  })
})
