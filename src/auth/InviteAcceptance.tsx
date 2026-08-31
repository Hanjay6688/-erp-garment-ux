import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { SupabaseClient } from '@supabase/supabase-js'
import { ShieldCheck } from 'lucide-react'
import type { PreconnectDatabase } from '../types/database.preconnect'

export const INVITE_ACCEPTANCE_PATH = '/auth/accept' as const

export type InviteAcceptanceRequest =
  | { ok: true; tokenHash: string }
  | { ok: false; reason: 'WRONG_PATH' | 'MISSING_PARAMETER' | 'UNSUPPORTED_PARAMETER' | 'WRONG_TYPE' | 'INVALID_TOKEN' | 'FRAGMENT_FORBIDDEN' }

export type InviteStepResult = { ok: true } | { ok: false; message: string }

type InviteClient = SupabaseClient<PreconnectDatabase>

export type InviteAcceptanceAttempt = {
  hasValidRequest: boolean
  verify: () => Promise<InviteStepResult>
  setPassword: (password: string) => Promise<InviteStepResult>
  abandon: () => Promise<void>
}

export type InviteAcceptanceOptions = {
  clearApplicationSession?: () => Promise<unknown>
}

const INVALID_LINK_MESSAGE = 'Tautan undangan tidak valid atau sudah kedaluwarsa. Minta Owner mengirim undangan baru.'
const ABANDONED_MESSAGE = 'Penerimaan undangan dibatalkan. Buka kembali undangan baru untuk melanjutkan.'

export function isInviteAcceptancePath(pathname: string) {
  return pathname === INVITE_ACCEPTANCE_PATH || pathname === `${INVITE_ACCEPTANCE_PATH}/`
}

export function isInviteSensitiveNavigation(location: Pick<Location, 'pathname' | 'search' | 'hash'>) {
  if (isInviteAcceptancePath(location.pathname)) return true
  const parameters = new URLSearchParams(location.search)
  if (parameters.has('token_hash') || parameters.getAll('type').includes('invite')) return true
  return /(?:^|[?&#])(?:access_token|refresh_token|token_hash)=/i.test(location.hash)
    || /(?:^|[?&#])type=invite(?:&|$)/i.test(location.hash)
}

export function parseInviteAcceptanceUrl(location: Pick<Location, 'pathname' | 'search' | 'hash'>): InviteAcceptanceRequest {
  if (!isInviteAcceptancePath(location.pathname)) return { ok: false, reason: 'WRONG_PATH' }
  if (location.hash !== '') return { ok: false, reason: 'FRAGMENT_FORBIDDEN' }

  const parameters = new URLSearchParams(location.search)
  const entries = [...parameters.entries()]
  const tokenValues = parameters.getAll('token_hash')
  const typeValues = parameters.getAll('type')

  if (tokenValues.length === 0 || typeValues.length === 0) return { ok: false, reason: 'MISSING_PARAMETER' }
  if (entries.length !== 2 || tokenValues.length !== 1 || typeValues.length !== 1) {
    return { ok: false, reason: 'UNSUPPORTED_PARAMETER' }
  }
  if (typeValues[0] !== 'invite') return { ok: false, reason: 'WRONG_TYPE' }

  const tokenHash = tokenValues[0]
  if (tokenHash.length === 0 || tokenHash.length > 4096 || /[\s\u0000-\u001f\u007f]/.test(tokenHash)) {
    return { ok: false, reason: 'INVALID_TOKEN' }
  }
  return { ok: true, tokenHash }
}

export function consumeInviteAcceptanceUrl(
  location: Pick<Location, 'pathname' | 'search' | 'hash'>,
  history: Pick<History, 'replaceState'>,
): InviteAcceptanceRequest {
  const request = parseInviteAcceptanceUrl(location)
  history.replaceState(null, '', location.pathname)
  return request
}

async function safeLocalSignOut(client: InviteClient) {
  try {
    await client.auth.signOut({ scope: 'local' })
  } catch {
    // Supabase local sign-out is best effort here; never expose provider details.
  }
}

function isUnrecoverableSessionError(error: unknown) {
  if (!error || typeof error !== 'object') return false
  const candidate = error as { code?: unknown; status?: unknown }
  const code = typeof candidate.code === 'string' ? candidate.code.toLowerCase() : ''
  return candidate.status === 401
    || candidate.status === 403
    || ['session_not_found', 'auth_session_missing', 'bad_jwt', 'invalid_token', 'refresh_token_not_found'].includes(code)
}

export function createInviteAcceptanceAttempt(
  client: InviteClient,
  request: InviteAcceptanceRequest,
  options: InviteAcceptanceOptions = {},
): InviteAcceptanceAttempt {
  let abandoned = false
  let verified = false
  let verifiedUserId: string | null = null
  let completed = false
  let abandonInFlight: Promise<void> | null = null
  let verificationInFlight: Promise<InviteStepResult> | null = null
  let updateInFlight: Promise<InviteStepResult> | null = null
  const applicationSessionCleared = (async () => {
    if (!options.clearApplicationSession) return true
    try {
      const outcome = await options.clearApplicationSession()
      if (outcome && typeof outcome === 'object' && 'error' in outcome && (outcome as { error?: unknown }).error) {
        return false
      }
      return true
    } catch {
      // Fail closed without surfacing provider details; invite operations wait for this attempt.
      return false
    }
  })()

  const abandon = () => {
    abandoned = true
    verified = false
    verifiedUserId = null
    if (!abandonInFlight) abandonInFlight = (async () => {
      await applicationSessionCleared
      await safeLocalSignOut(client)
    })()
    return abandonInFlight
  }

  const verify = (): Promise<InviteStepResult> => {
    if (verificationInFlight) return verificationInFlight
    verificationInFlight = (async (): Promise<InviteStepResult> => {
      if (!await applicationSessionCleared) {
        await abandon()
        return { ok: false, message: 'Sesi aplikasi lama tidak dapat ditutup. Muat ulang lalu coba undangan kembali.' }
      }
      if (abandoned) return { ok: false, message: ABANDONED_MESSAGE }
      if (!request.ok) {
        await abandon()
        return { ok: false, message: INVALID_LINK_MESSAGE }
      }

      try {
        const { data, error } = await client.auth.verifyOtp({
          token_hash: request.tokenHash,
          type: 'invite',
        })
        if (error || !data.session?.access_token || !data.user?.id) {
          await abandon()
          return { ok: false, message: INVALID_LINK_MESSAGE }
        }
        if (abandoned) {
          await safeLocalSignOut(client)
          return { ok: false, message: ABANDONED_MESSAGE }
        }
        verified = true
        verifiedUserId = data.user.id
        return { ok: true }
      } catch {
        await abandon()
        return { ok: false, message: INVALID_LINK_MESSAGE }
      }
    })()
    return verificationInFlight
  }

  const setPassword = (password: string): Promise<InviteStepResult> => {
    const policyError = strongPasswordError(password)
    if (policyError) return Promise.resolve({ ok: false, message: policyError })
    if (completed) return Promise.resolve({ ok: true })
    if (updateInFlight) return updateInFlight

    const operation = (async (): Promise<InviteStepResult> => {
      const verificationResult = await verify()
      if (!verificationResult.ok || !verified || abandoned) return verificationResult.ok
        ? { ok: false, message: ABANDONED_MESSAGE }
        : verificationResult

      try {
        const { data: currentUserData, error: currentUserError } = await client.auth.getUser()
        if (currentUserError || !verifiedUserId || currentUserData.user?.id !== verifiedUserId) {
          await abandon()
          return { ok: false, message: 'Sesi undangan sudah berakhir. Minta Owner mengirim undangan baru.' }
        }
        const { data, error } = await client.auth.updateUser({ password })
        if (error) {
          if (isUnrecoverableSessionError(error)) {
            await abandon()
            return { ok: false, message: 'Sesi undangan sudah berakhir. Minta Owner mengirim undangan baru.' }
          }
          return { ok: false, message: 'Kata sandi belum tersimpan. Periksa koneksi UAT lalu coba lagi.' }
        }
        if (!data.user?.id || data.user.id !== verifiedUserId) {
          await abandon()
          return { ok: false, message: 'Sesi undangan berubah. Masuk ulang melalui undangan baru.' }
        }
        if (abandoned) {
          await safeLocalSignOut(client)
          return { ok: false, message: ABANDONED_MESSAGE }
        }
        completed = true
        verified = false
        verifiedUserId = null
        await safeLocalSignOut(client)
        return { ok: true }
      } catch (error) {
        const unrecoverable = isUnrecoverableSessionError(error)
        if (unrecoverable) await abandon()
        return { ok: false, message: unrecoverable
          ? 'Sesi undangan sudah berakhir. Minta Owner mengirim undangan baru.'
          : 'Kata sandi belum tersimpan. Periksa koneksi UAT lalu coba lagi.' }
      }
    })()

    updateInFlight = operation
    const release = () => {
      if (updateInFlight === operation) updateInFlight = null
    }
    void operation.then(release, release)
    return operation
  }

  return { hasValidRequest: request.ok, verify, setPassword, abandon }
}

export function strongPasswordError(password: string) {
  if (password.length < 12) return 'Gunakan minimal 12 karakter.'
  if (password.length > 128) return 'Gunakan maksimal 128 karakter.'
  if (/\s/.test(password)) return 'Kata sandi tidak boleh memakai spasi.'
  if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
    return 'Gabungkan huruf besar, huruf kecil, angka, dan simbol.'
  }
  return null
}

export function InviteAcceptancePage({
  attempt,
  onComplete,
  onExit,
}: {
  attempt: InviteAcceptanceAttempt
  onComplete: () => void
  onExit: () => void
}) {
  const [phase, setPhase] = useState<'PENDING' | 'VERIFYING' | 'READY' | 'FAILED' | 'COMPLETE'>(attempt.hasValidRequest ? 'PENDING' : 'VERIFYING')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [abandoning, setAbandoning] = useState(false)
  const submitInFlight = useRef(false)
  const verifyInFlight = useRef(false)
  const abandonInFlight = useRef(false)

  useEffect(() => {
    if (attempt.hasValidRequest) return
    let active = true
    void attempt.verify().then((result) => {
      if (!active) return
      setMessage(result.ok ? INVALID_LINK_MESSAGE : result.message)
      setPhase('FAILED')
    })
    return () => { active = false }
  }, [attempt])

  const verify = async () => {
    if (verifyInFlight.current || phase !== 'PENDING') return
    verifyInFlight.current = true
    setPhase('VERIFYING')
    const result = await attempt.verify()
    if (result.ok) setPhase('READY')
    else {
      setMessage(result.message)
      setPhase('FAILED')
    }
  }

  const exit = async () => {
    if (abandonInFlight.current) return
    abandonInFlight.current = true
    setAbandoning(true)
    setPassword('')
    setConfirmation('')
    try {
      await attempt.abandon()
    } finally {
      onExit()
    }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (submitInFlight.current || phase !== 'READY') return
    setMessage('')
    const policyError = strongPasswordError(password)
    if (policyError) {
      setMessage(policyError)
      return
    }
    if (password !== confirmation) {
      setMessage('Konfirmasi kata sandi belum sama.')
      return
    }

    submitInFlight.current = true
    setSubmitting(true)
    try {
      const result = await attempt.setPassword(password)
      setPassword('')
      setConfirmation('')
      if (result.ok) {
        setPhase('COMPLETE')
      } else {
        setMessage(result.message)
      }
    } finally {
      submitInFlight.current = false
      setSubmitting(false)
    }
  }

  return <main className="auth-shell">
    <section className="auth-card">
      <div className="auth-mark"><ShieldCheck aria-hidden="true" /></div>
      <span className="auth-eyebrow">ERP ENTENG · UAT AUTH</span>
      <h1>Terima undangan akun</h1>

      {phase === 'PENDING' && <>
        <p>Tautan sensitif sudah dibersihkan. Lanjutkan hanya jika Anda memang meminta undangan akun ERP UAT.</p>
        <div className="auth-actions auth-actions-stack">
          <button type="button" className="auth-primary" onClick={() => void verify()}>Verifikasi undangan</button>
          <button type="button" className="auth-secondary" disabled={abandoning} onClick={() => void exit()}>{abandoning ? 'Mengakhiri sesi…' : 'Batalkan dan keluar'}</button>
        </div>
      </>}

      {phase === 'VERIFYING' && <>
        <div className="auth-progress" role="status" aria-live="polite" aria-label="Memverifikasi undangan" />
        <p>Undangan sedang diverifikasi. ERP tetap terkunci sampai proses selesai.</p>
        <button type="button" className="auth-secondary auth-exit" disabled={abandoning} onClick={() => void exit()}>{abandoning ? 'Mengakhiri sesi…' : 'Batalkan dan keluar'}</button>
      </>}

      {phase === 'READY' && <>
        <p>Undangan valid. Tetapkan kata sandi baru untuk akun ERP UAT ini.</p>
        <form className="auth-form" onSubmit={submit}>
          <label>Kata sandi baru
            <input type="password" required autoFocus autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} aria-describedby="invite-password-help" />
          </label>
          <label>Ulangi kata sandi
            <input type="password" required autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
          </label>
          <small id="invite-password-help" className="auth-password-help">Minimal 12 karakter dengan huruf besar, huruf kecil, angka, dan simbol; tanpa spasi.</small>
          {message && <div className="auth-error" role="alert" aria-live="assertive">{message}</div>}
          <button type="submit" className="auth-primary" disabled={submitting || abandoning}>{submitting ? 'Menyimpan…' : 'Simpan kata sandi'}</button>
          <button type="button" className="auth-secondary" disabled={submitting || abandoning} onClick={() => void exit()}>{abandoning ? 'Mengakhiri sesi…' : 'Batalkan dan keluar'}</button>
        </form>
      </>}

      {phase === 'FAILED' && <>
        <div className="auth-error" role="alert" aria-live="assertive">{message}</div>
        <button type="button" className="auth-secondary auth-exit" disabled={abandoning} onClick={() => void exit()}>{abandoning ? 'Mengakhiri sesi…' : 'Kembali ke halaman masuk'}</button>
      </>}

      {phase === 'COMPLETE' && <>
        <div className="auth-success" role="status" aria-live="polite">Kata sandi berhasil disimpan.</div>
        <p>Sesi undangan sudah ditutup. Masuk ulang agar profil dan role ERP diverifikasi sebelum aplikasi dibuka.</p>
        <button type="button" className="auth-primary auth-exit" onClick={onComplete}>Lanjut ke halaman masuk</button>
      </>}

      <small className="auth-footnote">Tautan undangan hanya dipakai untuk UAT Auth. Data bisnis tetap simulasi.</small>
    </section>
  </main>
}
