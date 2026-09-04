import { CheckCircle2, LockKeyhole, ShieldCheck } from 'lucide-react'

export type Cp6Capability = {
  allowed: boolean
  label: string
  requirement: string
}

export function Cp6PermissionNotice({ roleName, capabilities }: {
  roleName: string
  capabilities: readonly Cp6Capability[]
}) {
  return <section className="clq-permissions" aria-label="Hak akses aktif">
    <header><ShieldCheck/><span><strong>Hak kerja · {roleName}</strong><small>Server memeriksa ulang izin pada setiap aksi.</small></span></header>
    <ul>{capabilities.map((capability) => <li className={capability.allowed ? 'allowed' : 'locked'} key={capability.label}>
      {capability.allowed ? <CheckCircle2/> : <LockKeyhole/>}
      <span><strong>{capability.label}</strong><small>{capability.allowed ? 'Diizinkan' : `Terkunci · perlu ${capability.requirement}`}</small></span>
    </li>)}</ul>
  </section>
}

export function Cp6ActionBlocked({ allowed, action, requirement }: {
  allowed: boolean
  action: string
  requirement: string
}) {
  return allowed ? null : <div className="clq-access-blocked" role="status">
    <LockKeyhole/><span><strong>Mode lihat saja untuk {action}.</strong><small>Role Anda belum punya {requirement}. Form dikunci; data tetap bisa dilihat.</small></span>
  </div>
}
