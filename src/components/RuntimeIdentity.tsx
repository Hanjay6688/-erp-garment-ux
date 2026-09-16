import { useAuth } from '../auth/AuthProvider'
import { isConnectedRuntime } from '../config/runtime'

function initials(fullName: string) {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  return (parts.slice(0, 2).map((part) => part[0]).join('') || 'ERP').toUpperCase()
}

export function RuntimeBadge() {
  const { runtime } = useAuth()
  return <div className={`sim-badge runtime-badge ${isConnectedRuntime(runtime) ? 'uat' : 'demo'}`}>
    <span />
    {runtime.mode === 'DISPOSABLE_TEST' ? 'UJI LOKAL · DATA SINTETIS' : runtime.mode === 'UAT_AUTH_SIMULATION' ? 'UAT · MODUL TERPILIH LIVE' : 'DEMO · DATA SIMULASI'}
  </div>
}

export function RuntimeEnvironmentCard() {
  const { runtime } = useAuth()
  return <div className="env-card">
    <div className="env-dot" />
    <div>
      <strong>{runtime.mode === 'DISPOSABLE_TEST' ? 'ERP · Pengujian lokal' : runtime.mode === 'UAT_AUTH_SIMULATION' ? 'ERP Enteng' : 'Mode Demo'}</strong>
      <span>{isConnectedRuntime(runtime) ? 'Akses, Pola, Potongan, Distribusi, WIP, BS, Laundry dan QC terhubung' : 'Tanpa koneksi backend'}</span>
    </div>
  </div>
}

export function RuntimeIdentity() {
  const { runtime, identity, signingOut, signOutError, signOut } = useAuth()
  const environmentLabel = runtime.mode === 'DISPOSABLE_TEST' ? 'Uji lokal' : 'UAT'

  if (identity.status !== 'AUTHORIZED') {
    return <div className="owner"><span>OH</span><div><strong>Owner</strong><small>Simulasi</small></div></div>
  }

  const logout = async () => {
    await signOut()
  }

  return <details className="auth-identity">
    <summary className="owner">
      <span>{initials(identity.profile.fullName)}</span>
      <div><strong>{identity.profile.fullName}</strong><small>{identity.profile.roleName} · {environmentLabel}</small></div>
      <b>⌄</b>
    </summary>
    <div className="auth-identity-menu">
      <small>{environmentLabel} · {identity.permissions.length} izin aktif</small>
      <button type="button" disabled={signingOut} onClick={() => void logout()}>{signingOut ? 'Keluar…' : 'Keluar'}</button>
      {signOutError && <p role="alert">{signOutError.message}</p>}
    </div>
  </details>
}
