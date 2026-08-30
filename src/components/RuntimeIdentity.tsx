import { useState } from 'react'
import { useAuth } from '../auth/AuthProvider'

function initials(fullName: string) {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  return (parts.slice(0, 2).map((part) => part[0]).join('') || 'ERP').toUpperCase()
}

export function RuntimeBadge() {
  const { runtime } = useAuth()
  return <div className={`sim-badge runtime-badge ${runtime.mode === 'UAT_AUTH_SIMULATION' ? 'uat' : 'demo'}`}>
    <span />
    {runtime.mode === 'UAT_AUTH_SIMULATION' ? 'UAT AUTH + DATA SIMULASI' : 'DEMO · DATA SIMULASI'}
  </div>
}

export function RuntimeEnvironmentCard() {
  const { runtime } = useAuth()
  return <div className="env-card">
    <div className="env-dot" />
    <div>
      <strong>{runtime.mode === 'UAT_AUTH_SIMULATION' ? 'ERP Enteng' : 'Mode Demo'}</strong>
      <span>{runtime.mode === 'UAT_AUTH_SIMULATION' ? 'Auth UAT · data simulasi' : 'Tanpa koneksi backend'}</span>
    </div>
  </div>
}

export function RuntimeIdentity() {
  const { identity, signOut } = useAuth()
  const [signOutError, setSignOutError] = useState('')

  if (identity.status !== 'AUTHORIZED') {
    return <div className="owner"><span>OH</span><div><strong>Owner</strong><small>Simulasi</small></div></div>
  }

  const logout = async () => {
    setSignOutError('')
    const result = await signOut()
    if (!result.ok) setSignOutError(result.error.message)
  }

  return <details className="auth-identity">
    <summary className="owner">
      <span>{initials(identity.profile.fullName)}</span>
      <div><strong>{identity.profile.fullName}</strong><small>{identity.profile.role} · UAT</small></div>
      <b>⌄</b>
    </summary>
    <div className="auth-identity-menu">
      <small>ERP Enteng · Auth aktif</small>
      <button type="button" onClick={() => void logout()}>Keluar</button>
      {signOutError && <p role="alert">{signOutError}</p>}
    </div>
  </details>
}
