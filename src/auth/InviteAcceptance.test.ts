import { describe, expect, it, vi } from 'vitest'
import type { SupabaseClient } from '@supabase/supabase-js'
import type { PreconnectDatabase } from '../types/database.preconnect'
import { UAT_INVITE_AUTH_OPTIONS } from '../lib/supabase'
import {
  consumeInviteAcceptanceUrl,
  createInviteAcceptanceAttempt,
  isInviteAcceptancePath,
  isInviteSensitiveNavigation,
  parseInviteAcceptanceUrl,
  strongPasswordError,
} from './InviteAcceptance'

const tokenHash = 'hash-with-provider-format_1234567890/plus+symbols='

function location(search: string, hash = '', pathname = '/auth/accept') {
  return { pathname, search, hash } as Location
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolver) => { resolve = resolver })
  return { promise, resolve }
}

function client(options: {
  verifyOtp?: () => Promise<unknown>
  getUser?: () => Promise<unknown>
  updateUser?: () => Promise<unknown>
  signOut?: () => Promise<unknown>
}) {
  return {
    auth: {
      verifyOtp: vi.fn(options.verifyOtp ?? (async () => ({
        data: { session: { access_token: 'session-token' }, user: { id: 'user-id' } },
        error: null,
      }))),
      getUser: vi.fn(options.getUser ?? (async () => ({ data: { user: { id: 'user-id' } }, error: null }))),
      updateUser: vi.fn(options.updateUser ?? (async () => ({ data: { user: { id: 'user-id' } }, error: null }))),
      signOut: vi.fn(options.signOut ?? (async () => ({ error: null }))),
    },
  } as unknown as SupabaseClient<PreconnectDatabase>
}

describe('invite acceptance URL policy', () => {
  it('accepts only the exact invite route and two unique required parameters', () => {
    expect(isInviteAcceptancePath('/auth/accept')).toBe(true)
    expect(isInviteAcceptancePath('/auth/accept/')).toBe(true)
    expect(isInviteAcceptancePath('/some/auth/accept')).toBe(false)
    expect(parseInviteAcceptanceUrl(location(`?token_hash=${encodeURIComponent(tokenHash)}&type=invite`))).toEqual({
      ok: true,
      tokenHash,
    })
  })

  it('detects and scrubs misplaced invite secrets before runtime selection', () => {
    const misplaced = location(`?token_hash=${encodeURIComponent(tokenHash)}&type=invite`, '', '/unexpected')
    expect(isInviteSensitiveNavigation(misplaced)).toBe(true)
    expect(isInviteSensitiveNavigation(location('', '', '/'))).toBe(false)
    expect(isInviteSensitiveNavigation(location('', '#access_token=secret', '/unexpected'))).toBe(true)
    const replaceState = vi.fn()
    expect(consumeInviteAcceptanceUrl(misplaced, { replaceState })).toEqual({ ok: false, reason: 'WRONG_PATH' })
    expect(replaceState).toHaveBeenCalledExactlyOnceWith(null, '', '/unexpected')
  })

  it('pins the invite client to non-persistent, non-refreshing, non-URL-detecting Auth', () => {
    expect(UAT_INVITE_AUTH_OPTIONS).toEqual({
      storageKey: 'atelier-garment-erp-uat-invite-memory',
      autoRefreshToken: false,
      persistSession: false,
      detectSessionInUrl: false,
    })
  })

  it.each([
    ['missing token', '?type=invite', '', 'MISSING_PARAMETER'],
    ['wrong type', `?token_hash=${tokenHash}&type=recovery`, '', 'WRONG_TYPE'],
    ['redirect parameter', `?token_hash=${tokenHash}&type=invite&redirect_to=https://evil.test`, '', 'UNSUPPORTED_PARAMETER'],
    ['next parameter', `?token_hash=${tokenHash}&type=invite&next=https://evil.test`, '', 'UNSUPPORTED_PARAMETER'],
    ['duplicate type', `?token_hash=${tokenHash}&type=invite&type=invite`, '', 'UNSUPPORTED_PARAMETER'],
    ['fragment token', `?token_hash=${tokenHash}&type=invite`, '#access_token=secret', 'FRAGMENT_FORBIDDEN'],
    ['blank token', '?token_hash=&type=invite', '', 'INVALID_TOKEN'],
  ])('rejects %s', (_label, search, hash, reason) => {
    expect(parseInviteAcceptanceUrl(location(search, hash))).toEqual({ ok: false, reason })
  })

  it('scrubs the full query and fragment before returning the in-memory request', () => {
    const replaceState = vi.fn()
    const request = consumeInviteAcceptanceUrl(
      location(`?token_hash=${encodeURIComponent(tokenHash)}&type=invite`, '#must-not-survive'),
      { replaceState },
    )
    expect(request).toEqual({ ok: false, reason: 'FRAGMENT_FORBIDDEN' })
    expect(replaceState).toHaveBeenCalledExactlyOnceWith(null, '', '/auth/accept')
    expect(JSON.stringify(replaceState.mock.calls)).not.toContain(tokenHash)
  })
})

describe('invite acceptance controller', () => {
  it('does not consume a valid invitation until explicit verification and sends only invite OTP fields', async () => {
    const authClient = client({})
    const attempt = createInviteAcceptanceAttempt(authClient, { ok: true, tokenHash })
    expect(authClient.auth.verifyOtp).not.toHaveBeenCalled()

    await expect(attempt.verify()).resolves.toEqual({ ok: true })
    expect(authClient.auth.verifyOtp).toHaveBeenCalledExactlyOnceWith({ token_hash: tokenHash, type: 'invite' })
    expect(attempt.verify()).toBe(attempt.verify())
  })

  it('clears any persistent application session before invite verification', async () => {
    const cleared = deferred<unknown>()
    const clearApplicationSession = vi.fn(() => cleared.promise)
    const authClient = client({})
    const attempt = createInviteAcceptanceAttempt(authClient, { ok: true, tokenHash }, { clearApplicationSession })
    const verifying = attempt.verify()

    expect(clearApplicationSession).toHaveBeenCalledTimes(1)
    expect(authClient.auth.verifyOtp).not.toHaveBeenCalled()
    cleared.resolve({ error: null })
    await expect(verifying).resolves.toEqual({ ok: true })
    expect(authClient.auth.verifyOtp).toHaveBeenCalledTimes(1)
  })

  it('does not consume the invite when the persistent application session cannot be cleared', async () => {
    const authClient = client({})
    const attempt = createInviteAcceptanceAttempt(authClient, { ok: true, tokenHash }, {
      clearApplicationSession: async () => ({ error: { message: 'storage unavailable' } }),
    })
    await expect(attempt.verify()).resolves.toMatchObject({ ok: false })
    expect(authClient.auth.verifyOtp).not.toHaveBeenCalled()
    expect(authClient.auth.signOut).toHaveBeenCalledExactlyOnceWith({ scope: 'local' })
  })

  it('rejects an invalid or expired invite without logging provider details and clears the local session', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    const authClient = client({
      verifyOtp: async () => ({ data: { session: null, user: null }, error: { message: `expired ${tokenHash}` } }),
    })
    const attempt = createInviteAcceptanceAttempt(authClient, { ok: true, tokenHash })

    await expect(attempt.verify()).resolves.toMatchObject({ ok: false })
    expect(authClient.auth.signOut).toHaveBeenCalledExactlyOnceWith({ scope: 'local' })
    expect(consoleError).not.toHaveBeenCalled()
    expect(consoleLog).not.toHaveBeenCalled()
  })

  it('deduplicates password updates and does not reopen a session after abandonment wins a verification race', async () => {
    const verification = deferred<unknown>()
    const passwordUpdate = deferred<unknown>()
    const authClient = client({
      verifyOtp: () => verification.promise,
      updateUser: () => passwordUpdate.promise,
    })
    const attempt = createInviteAcceptanceAttempt(authClient, { ok: true, tokenHash })
    const verifying = attempt.verify()
    await attempt.abandon()
    verification.resolve({ data: { session: { access_token: 'session-token' }, user: { id: 'user-id' } }, error: null })
    await expect(verifying).resolves.toMatchObject({ ok: false })
    expect(authClient.auth.signOut).toHaveBeenCalledWith({ scope: 'local' })
    expect(authClient.auth.updateUser).not.toHaveBeenCalled()

    const secondClient = client({ updateUser: () => passwordUpdate.promise })
    const secondAttempt = createInviteAcceptanceAttempt(secondClient, { ok: true, tokenHash })
    await secondAttempt.verify()
    await expect(secondAttempt.setPassword('weak')).resolves.toMatchObject({ ok: false })
    expect(secondClient.auth.updateUser).not.toHaveBeenCalled()
    const first = secondAttempt.setPassword('StrongPassword!42')
    const second = secondAttempt.setPassword('StrongPassword!42')
    expect(first).toBe(second)
    await Promise.resolve()
    await Promise.resolve()
    expect(secondClient.auth.updateUser).toHaveBeenCalledTimes(1)
    passwordUpdate.resolve({ data: { user: { id: 'user-id' } }, error: null })
    await expect(Promise.all([first, second])).resolves.toEqual([{ ok: true }, { ok: true }])
    expect(secondClient.auth.signOut).toHaveBeenCalledExactlyOnceWith({ scope: 'local' })
  })

  it('closes an in-memory verified session when the user leaves before setting a password', async () => {
    const authClient = client({})
    const attempt = createInviteAcceptanceAttempt(authClient, { ok: true, tokenHash })
    await expect(attempt.verify()).resolves.toEqual({ ok: true })
    await attempt.abandon()
    expect(authClient.auth.signOut).toHaveBeenCalledExactlyOnceWith({ scope: 'local' })
    await expect(attempt.setPassword('StrongPassword!42')).resolves.toMatchObject({ ok: false })
    expect(authClient.auth.updateUser).not.toHaveBeenCalled()
  })

  it('fails closed if the authenticated user changes before password update', async () => {
    const authClient = client({
      getUser: async () => ({ data: { user: { id: 'different-user' } }, error: null }),
    })
    const attempt = createInviteAcceptanceAttempt(authClient, { ok: true, tokenHash })
    await attempt.verify()
    await expect(attempt.setPassword('StrongPassword!42')).resolves.toMatchObject({ ok: false })
    expect(authClient.auth.updateUser).not.toHaveBeenCalled()
    expect(authClient.auth.signOut).toHaveBeenCalledExactlyOnceWith({ scope: 'local' })
  })

  it('fails closed after a scrubbed invite URL is reloaded', async () => {
    const authClient = client({})
    const reloadedRequest = parseInviteAcceptanceUrl(location(''))
    const attempt = createInviteAcceptanceAttempt(authClient, reloadedRequest)
    await expect(attempt.verify()).resolves.toMatchObject({ ok: false })
    expect(authClient.auth.verifyOtp).not.toHaveBeenCalled()
    expect(authClient.auth.signOut).toHaveBeenCalledExactlyOnceWith({ scope: 'local' })
  })
})

describe('strong invite password policy', () => {
  it('requires length, case, number, symbol, no whitespace, and matching server-safe maximum', () => {
    expect(strongPasswordError('Short!1A')).toContain('12')
    expect(strongPasswordError('alllowercase!42')).toContain('huruf besar')
    expect(strongPasswordError('Has Space!42Aa')).toContain('spasi')
    expect(strongPasswordError('A'.repeat(129))).toContain('128')
    expect(strongPasswordError('StrongPassword!42')).toBeNull()
  })
})
