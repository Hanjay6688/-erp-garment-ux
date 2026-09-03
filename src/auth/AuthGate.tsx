import { useState } from 'react'
import type { FormEvent, PropsWithChildren } from 'react'
import { ShieldCheck } from 'lucide-react'
import { useAuth } from './AuthProvider'
import type { AuthIdentity } from './AuthProvider'
import { RuntimeConfigError } from '../config/runtime'

export type AuthGateMode = 'ALLOW' | 'LOADING' | 'BLOCKED' | 'LOGIN'

export function authGateMode(identity: AuthIdentity): AuthGateMode {
  if (identity.status === 'DEMO' || identity.status === 'AUTHORIZED') return 'ALLOW'
  if (identity.status === 'LOADING') return 'LOADING'
  if (identity.status === 'BLOCKED') return 'BLOCKED'
  return 'LOGIN'
}

export function AuthGate({ children }: PropsWithChildren) {
  const { identity, signingOut, signOutError, signIn, signOut, retryIdentity } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [retrying, setRetrying] = useState(false)
  const gateMode = authGateMode(identity)
  const identityError = identity.status === 'ANONYMOUS' ? identity.error : null

  if (gateMode === 'ALLOW') return children

  if (gateMode === 'LOADING') {
    return <AuthFrame eyebrow="UAT AUTH" title={signingOut ? 'Mengakhiri sesi…' : 'Memverifikasi sesi…'}>
      <div className="auth-progress" role="status" aria-live="polite" aria-label={signingOut ? 'Mengakhiri sesi' : 'Memverifikasi sesi'} />
      <p>{signingOut
        ? 'Akses ERP dikunci sampai proses keluar selesai.'
        : 'ERP belum dibuka sampai identitas, role aktif, dan bundle izin selesai diverifikasi.'}</p>
    </AuthFrame>
  }

  const retry = async () => {
    if (retrying) return
    setRetrying(true)
    try {
      await retryIdentity()
    } finally {
      setRetrying(false)
    }
  }

  if (gateMode === 'BLOCKED' && identity.status === 'BLOCKED') {
    return <AuthFrame eyebrow="AKSES DIBLOKIR" title="Akun belum lolos guardrail">
      <p>{identity.message}</p>
      {identity.errorCode && <code>{identity.errorCode}</code>}
      {signOutError && <div className="auth-error" role="alert">{signOutError.message}</div>}
      <div className="auth-actions">
        <button type="button" className="auth-secondary" disabled={retrying} onClick={() => void retry()}>{retrying ? 'Memeriksa…' : 'Periksa ulang'}</button>
        <button type="button" className="auth-primary" disabled={signingOut} onClick={() => void signOut()}>{signingOut ? 'Keluar…' : 'Keluar'}</button>
      </div>
    </AuthFrame>
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError('')
    setSubmitting(true)
    try {
      const result = await signIn(email, password)
      setPassword('')
      if (!result.ok) setSubmitError(result.error.message)
    } finally {
      setSubmitting(false)
    }
  }

  return <AuthFrame eyebrow="ERP ENTENG · UAT AUTH" title="Masuk ke Atelier ERP">
    <p>Auth, hak akses, Master Pola, dan status WIP memakai UAT. Modul bisnis lain tetap diberi batas data simulasi.</p>
    <form className="auth-form" onSubmit={submit}>
      <label>Email akun ERP<input type="email" required autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label>Kata sandi<input type="password" required autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {(submitError || identityError) && <div className="auth-error" role="alert">{submitError || identityError?.message}</div>}
      <button type="submit" className="auth-primary" disabled={submitting}>{submitting ? 'Memverifikasi…' : 'Masuk'}</button>
      {identityError?.retryable && <button type="button" className="auth-secondary" disabled={retrying} onClick={() => void retry()}>{retrying ? 'Memeriksa sesi…' : 'Coba verifikasi sesi lagi'}</button>}
    </form>
    <small className="auth-footnote">Tidak ada pendaftaran akun dari aplikasi. Hanya pengguna terpetakan dengan role aktif yang dapat masuk.</small>
  </AuthFrame>
}

function AuthFrame({ eyebrow, title, children }: PropsWithChildren<{ eyebrow: string; title: string }>) {
  return <main className="auth-shell">
    <section className="auth-card">
      <div className="auth-mark"><ShieldCheck aria-hidden="true" /></div>
      <span className="auth-eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      {children}
    </section>
  </main>
}

export function RuntimeConfigurationFailure({ error }: { error: unknown }) {
  const configError = error instanceof RuntimeConfigError ? error : null
  return <AuthFrame eyebrow="RUNTIME DIBLOKIR" title="Konfigurasi koneksi tidak aman">
    <p>{configError?.message ?? 'Runtime tidak dapat divalidasi.'}</p>
    <code>{configError?.code ?? 'RUNTIME_CONFIG_INVALID'}</code>
    <small className="auth-footnote">Aplikasi sengaja tidak melakukan fallback ke demo atau proyek lain.</small>
  </AuthFrame>
}
