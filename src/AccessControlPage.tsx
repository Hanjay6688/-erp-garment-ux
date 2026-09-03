import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Check, Copy, LockKeyhole, RefreshCw, Save, Search, ShieldCheck, UserRound, X } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import './access-control.css'
import './access-control-cp45.css'

type PermissionRow = {
  key: string
  module_key: string
  module_label: string
  action: string
  action_label: string
  description: string
  high_risk: boolean
  sort_order: number
}

type RoleRow = {
  id: string
  code: string
  name: string
  description: string | null
  is_system: boolean
  is_protected: boolean
  is_active: boolean
  row_version: number
  active_user_count: number
  permissions: string[]
  updated_at: string
  updated_by: string | null
}

type UserRow = {
  id: string
  auth_user_id: string | null
  full_name: string
  role_id: string
  role_code: string
  role_name: string
  is_active: boolean
  mapped: boolean
  row_version: number
  last_sign_in_at: string | null
}

type AuditRow = {
  id: number
  entity_type: string
  action: string
  change_reason: string
  changed_at: string
  changed_by: string | null
}

type AccessAdminData = { permissions: PermissionRow[]; roles: RoleRow[]; users: UserRow[]; audit: AuditRow[] }

const demoPermissions: PermissionRow[] = [
  { key: 'production.wip.view', module_key: 'production.wip', module_label: 'WIP & Sewing', action: 'view', action_label: 'Lihat', description: 'Melihat status WIP authoritative.', high_risk: false, sort_order: 1 },
  { key: 'production.wip.adjust', module_key: 'production.wip', module_label: 'WIP & Sewing', action: 'adjust', action_label: 'Koreksi', description: 'Mengoreksi blocker WIP.', high_risk: true, sort_order: 2 },
  { key: 'master.pattern.view', module_key: 'master.pattern', module_label: 'Pola', action: 'view', action_label: 'Lihat', description: 'Melihat Master Pola.', high_risk: false, sort_order: 3 },
  { key: 'master.pattern.manage', module_key: 'master.pattern', module_label: 'Pola', action: 'manage', action_label: 'Kelola', description: 'Mengelola Master Pola.', high_risk: true, sort_order: 4 },
  { key: 'finance.payroll.approve', module_key: 'finance.payroll', module_label: 'Payroll & Kasbon', action: 'approve', action_label: 'Approve', description: 'Menyetujui payroll.', high_risk: true, sort_order: 5 },
  { key: 'finance.payroll.pay', module_key: 'finance.payroll', module_label: 'Payroll & Kasbon', action: 'pay', action_label: 'Bayar', description: 'Membayar payroll yang disetujui.', high_risk: true, sort_order: 6 },
]

const demoData: AccessAdminData = {
  permissions: demoPermissions,
  roles: [
    { id: 'demo-owner', code: 'OWNER', name: 'Owner', description: 'Akses penuh permanen.', is_system: true, is_protected: true, is_active: true, row_version: 1, active_user_count: 1, permissions: demoPermissions.map((item) => item.key), updated_at: '2026-09-02T00:00:00Z', updated_by: 'Owner' },
    { id: 'demo-view', code: 'AUDITOR_VIEW_ONLY', name: 'Auditor · View Only', description: 'Template baca-saja.', is_system: true, is_protected: false, is_active: true, row_version: 1, active_user_count: 0, permissions: ['production.wip.view', 'master.pattern.view'], updated_at: '2026-09-02T00:00:00Z', updated_by: 'System' },
  ],
  users: [{ id: 'demo-user', auth_user_id: null, full_name: 'Contoh Pengguna', role_id: 'demo-owner', role_code: 'OWNER', role_name: 'Owner', is_active: true, mapped: false, row_version: 1, last_sign_in_at: null }],
  audit: [],
}

function asArray(value: unknown) { return Array.isArray(value) ? value : [] }

export function parseAccessAdminData(value: unknown): AccessAdminData {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Respons hak akses tidak valid.')
  const raw = value as Record<string, unknown>
  return {
    permissions: asArray(raw.permissions) as PermissionRow[],
    roles: asArray(raw.roles) as RoleRow[],
    users: asArray(raw.users) as UserRow[],
    audit: asArray(raw.audit) as AuditRow[],
  }
}

export function groupPermissionRows(rows: PermissionRow[]) {
  const grouped = new Map<string, { label: string; rows: PermissionRow[] }>()
  rows.forEach((row) => {
    const current = grouped.get(row.module_key) ?? { label: row.module_label, rows: [] }
    current.rows.push(row)
    grouped.set(row.module_key, current)
  })
  return [...grouped.entries()].map(([key, group]) => ({ key, label: group.label, rows: group.rows.sort((a, b) => a.sort_order - b.sort_order) }))
}

function localDate(value: string | null) {
  if (!value) return 'Belum pernah'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? 'Tidak tersedia' : parsed.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })
}

export default function AccessControlPage() {
  const { runtime, identity } = useAuth()
  const connected = runtime.mode === 'UAT_AUTH_SIMULATION'
  const canManage = identity.status === 'DEMO' || (identity.status === 'AUTHORIZED' && hasPermission(identity, 'settings.access.manage'))
  const client = useMemo(
    () => runtime.mode === 'UAT_AUTH_SIMULATION' ? getUatSupabaseClient(runtime) : null,
    [runtime],
  )
  const [data, setData] = useState<AccessAdminData | null>(connected ? null : demoData)
  const [loading, setLoading] = useState(connected)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null)
  const [draftName, setDraftName] = useState('')
  const [draftDescription, setDraftDescription] = useState('')
  const [draftPermissions, setDraftPermissions] = useState<string[]>([])
  const [changeReason, setChangeReason] = useState('')
  const [highRiskConfirmed, setHighRiskConfirmed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [moduleQuery, setModuleQuery] = useState('')

  const load = async () => {
    if (!client) { setData(demoData); return }
    setLoading(true)
    setError('')
    const { data: response, error: loadError } = await client.rpc('erp_get_access_admin_v1')
    if (loadError) setError(normalizeClientError(loadError).message)
    else {
      try { setData(parseAccessAdminData(response)) } catch (parseError) { setError(String(parseError)) }
    }
    setLoading(false)
  }

  useEffect(() => { void load() }, [client]) // eslint-disable-line react-hooks/exhaustive-deps

  const roles = data?.roles.filter((role) => `${role.name} ${role.code}`.toLowerCase().includes(query.toLowerCase())) ?? []
  const selectedRole = data?.roles.find((role) => role.id === selectedRoleId) ?? null
  const isDuplicate = selectedRoleId?.startsWith('duplicate:') ?? false
  const editorSource = isDuplicate
    ? data?.roles.find((role) => role.id === selectedRoleId?.slice('duplicate:'.length)) ?? null
    : selectedRole
  const dirty = Boolean(editorSource) && (
    draftName !== (isDuplicate ? `${editorSource?.name} · Salinan` : editorSource?.name)
    || draftDescription !== (editorSource?.description ?? '')
    || [...draftPermissions].sort().join('|') !== [...(editorSource?.permissions ?? [])].sort().join('|')
  )

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault() }
    globalThis.addEventListener('beforeunload', warn)
    return () => globalThis.removeEventListener('beforeunload', warn)
  }, [dirty])

  const openRole = (role: RoleRow, duplicate = false) => {
    if (dirty && !globalThis.confirm('Perubahan role belum disimpan. Lanjutkan?')) return
    setSelectedRoleId(duplicate ? `duplicate:${role.id}` : role.id)
    setDraftName(duplicate ? `${role.name} · Salinan` : role.name)
    setDraftDescription(role.description ?? '')
    setDraftPermissions([...role.permissions])
    setChangeReason('')
    setHighRiskConfirmed(false)
  }

  const grouped = groupPermissionRows(data?.permissions ?? []).filter((module) => `${module.label} ${module.key}`.toLowerCase().includes(moduleQuery.toLowerCase()))
  const selectedHasHighRisk = (data?.permissions ?? []).some((permission) => permission.high_risk && draftPermissions.includes(permission.key))

  const togglePermission = (key: string) => setDraftPermissions((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key])
  const toggleModule = (keys: string[], enabled: boolean) => setDraftPermissions((current) => enabled
    ? [...new Set([...current, ...keys])]
    : current.filter((key) => !keys.includes(key)))

  const save = async () => {
    if (!editorSource || !canManage || saving) return
    if (!draftName.trim() || !changeReason.trim()) { setError('Nama role dan alasan perubahan wajib diisi.'); return }
    if (selectedHasHighRisk && !highRiskConfirmed) { setError('Konfirmasi izin berisiko tinggi terlebih dahulu.'); return }
    if (!client) { setError('DATA SIMULASI · perubahan tidak dikirim ke backend.'); return }
    setSaving(true)
    setError('')
    const code = isDuplicate
      ? `CUSTOM_${globalThis.crypto.randomUUID().replaceAll('-', '').slice(0, 12).toUpperCase()}`
      : editorSource.code
    const { error: saveError } = await client.rpc('erp_save_role_v1', {
      p_payload: {
        ...(isDuplicate ? {} : { id: editorSource.id }), code, name: draftName.trim(),
        description: draftDescription.trim(), permission_keys: draftPermissions,
        confirm_high_risk: highRiskConfirmed, change_reason: changeReason.trim(),
      },
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: isDuplicate ? null : editorSource.row_version,
    })
    if (saveError) setError(normalizeClientError(saveError).message)
    else { setSelectedRoleId(null); await load() }
    setSaving(false)
  }

  const changeUserRole = async (user: UserRow, roleId: string) => {
    if (!client || !canManage) return
    const reason = globalThis.prompt('Alasan perubahan akses pengguna:')?.trim()
    if (!reason) return
    setError('')
    const { error: saveError } = await client.rpc('erp_save_app_user_v3', {
      p_payload: {
        id: user.id, full_name: user.full_name, auth_user_id: user.auth_user_id,
        role_id: roleId, is_active: user.is_active, change_reason: reason,
      },
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: user.row_version,
    })
    if (saveError) setError(normalizeClientError(saveError).message)
    else await load()
  }

  const changeUserActive = async (user: UserRow) => {
    if (!client || !canManage) return
    const nextActive = !user.is_active
    const reason = globalThis.prompt(`Alasan ${nextActive ? 'mengaktifkan' : 'menonaktifkan'} ${user.full_name}:`)?.trim()
    if (!reason) return
    setError('')
    const { error: saveError } = await client.rpc('erp_save_app_user_v3', {
      p_payload: {
        id: user.id, full_name: user.full_name, auth_user_id: user.auth_user_id,
        role_id: user.role_id, is_active: nextActive, change_reason: reason,
      },
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: user.row_version,
    })
    if (saveError) setError(normalizeClientError(saveError).message)
    else await load()
  }

  const deactivateRole = async (role: RoleRow) => {
    if (!client || !canManage || role.is_system || role.is_protected || !role.is_active) return
    const reason = globalThis.prompt(`Alasan menonaktifkan role ${role.name}:`)?.trim()
    if (!reason) return
    setError('')
    const { error: deactivateError } = await client.rpc('erp_deactivate_role_v1', {
      p_role_id: role.id,
      p_reason: reason,
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: role.row_version,
    })
    if (deactivateError) setError(normalizeClientError(deactivateError).message)
    else await load()
  }

  if (loading) return <section className="access-state" role="status"><RefreshCw className="spin"/><strong>Memuat hak akses authoritative…</strong></section>

  return <section className="access-page">
    <header className="access-hero">
      <div><span>PENGATURAN · SERVER-ENFORCED</span><h1>Pengguna & Hak Akses</h1><p>Satu pengguna memiliki satu role. Perubahan izin berlaku pada request server berikutnya.</p></div>
      <button onClick={() => void load()}><RefreshCw/> Refresh</button>
    </header>
    <div className={`truth-strip ${connected ? 'connected' : 'simulation'}`}><ShieldCheck/><strong>{connected ? 'UAT BACKEND CONNECTED' : 'DATA SIMULASI'}</strong><span>Portal Mandor, Laundry, dan Toko: NOT CONNECTED</span></div>
    {error && <div className="access-error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')} aria-label="Tutup"><X/></button></div>}

    <div className="access-grid">
      <section className="access-panel roles-panel">
        <header><div><span>ROLE</span><strong>{data?.roles.length ?? 0} definisi</strong></div><label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari role…"/></label></header>
        <div className="role-list">{roles.map((role) => <article key={role.id} className={!role.is_active ? 'inactive' : ''}>
          <div className="role-title"><span><strong>{role.name}</strong><small>{role.code}</small></span><div>{role.is_system && <em>SYSTEM</em>}{role.is_protected && <em className="locked"><LockKeyhole/> TERKUNCI</em>}{!role.is_active && <em>NONAKTIF</em>}</div></div>
          <p>{role.description || 'Tanpa deskripsi.'}</p>
          <dl><div><dt>Pengguna aktif</dt><dd>{role.active_user_count}</dd></div><div><dt>Terakhir diubah</dt><dd>{localDate(role.updated_at)} · {role.updated_by || 'System'}</dd></div></dl>
          <footer><button onClick={() => openRole(role, true)}><Copy/> Duplikat</button><button disabled={!canManage || role.is_system || role.is_protected || !role.is_active} onClick={() => openRole(role)}>{role.is_protected ? <LockKeyhole/> : <ShieldCheck/>} Edit</button>{!role.is_system && <button disabled={!canManage || !connected || !role.is_active} onClick={() => void deactivateRole(role)}><X/> Nonaktifkan</button>}</footer>
        </article>)}</div>
      </section>

      <section className="access-panel users-panel">
        <header><div><span>PENGGUNA</span><strong>{data?.users.length ?? 0} akses</strong></div><UserRound/></header>
        <div className="user-list">{(data?.users ?? []).map((user) => <article key={user.id}>
          <span className="user-avatar">{user.full_name.slice(0, 2).toUpperCase()}</span>
          <div><strong>{user.full_name}</strong><small>{user.mapped ? 'TERPETAKAN' : 'BELUM TERPETAKAN'} · {user.is_active ? 'AKTIF' : 'NONAKTIF'}</small><small>Masuk terakhir: {localDate(user.last_sign_in_at)}</small></div>
          <div className="user-access-actions"><select aria-label={`Role ${user.full_name}`} value={user.role_id} disabled={!canManage || !connected} onChange={(event) => void changeUserRole(user, event.target.value)}>{(data?.roles ?? []).filter((role) => role.is_active).map((role) => <option value={role.id} key={role.id}>{role.name}</option>)}</select><button disabled={!canManage || !connected} onClick={() => void changeUserActive(user)}>{user.is_active ? 'Nonaktifkan' : 'Aktifkan'}</button></div>
        </article>)}</div>
      </section>
    </div>

    <section className="access-panel audit-panel"><header><div><span>AUDIT IMMUTABLE</span><strong>100 perubahan terakhir</strong></div><ShieldCheck/></header><div>{(data?.audit ?? []).slice(0, 8).map((entry) => <article key={entry.id}><strong>{entry.entity_type} · {entry.action}</strong><span>{entry.change_reason}</span><small>{localDate(entry.changed_at)} · {entry.changed_by || 'System'}</small></article>)}{(data?.audit.length ?? 0) === 0 && <p>Belum ada perubahan akses.</p>}</div></section>

    {editorSource && <div className="role-editor-layer" role="presentation" onMouseDown={() => !dirty && setSelectedRoleId(null)}><section className="role-editor" role="dialog" aria-modal="true" aria-labelledby="role-editor-title" onMouseDown={(event) => event.stopPropagation()}>
      <header><div><span>{isDuplicate ? 'DUPLIKAT ROLE' : 'EDIT ROLE'}</span><h2 id="role-editor-title">{editorSource.name}</h2><p>{editorSource.is_protected ? 'OWNER memiliki semua izin dan tidak dapat dilemahkan.' : 'Pilih aksi yang benar-benar dibutuhkan.'}</p></div><button onClick={() => setSelectedRoleId(null)} aria-label="Tutup"><X/></button></header>
      <div className="role-fields"><label>Nama role<input value={draftName} disabled={editorSource.is_protected && !isDuplicate} onChange={(event) => setDraftName(event.target.value)}/></label><label>Deskripsi<input value={draftDescription} disabled={editorSource.is_protected && !isDuplicate} onChange={(event) => setDraftDescription(event.target.value)}/></label><label className="module-search">Cari modul<Search/><input value={moduleQuery} onChange={(event) => setModuleQuery(event.target.value)} placeholder="WIP, Payroll, Gudang…"/></label></div>
      <div className="permission-matrix">{grouped.map((module) => {
        const keys = module.rows.map((row) => row.key)
        const all = keys.every((key) => draftPermissions.includes(key))
        return <article key={module.key}><header><div><strong>{module.label}</strong><small>{module.key}</small></div><button disabled={editorSource.is_protected && !isDuplicate} onClick={() => toggleModule(keys, !all)}>{all ? 'Kosongkan modul' : 'Pilih semua modul'}</button></header><div>{module.rows.map((permission) => <label key={permission.key} className={permission.high_risk ? 'high-risk' : ''}><input type="checkbox" checked={draftPermissions.includes(permission.key)} disabled={editorSource.is_protected && !isDuplicate} onChange={() => togglePermission(permission.key)}/><span><strong>{permission.action_label}{permission.high_risk && ' · Risiko tinggi'}</strong><small>{permission.description}</small></span></label>)}</div></article>
      })}</div>
      <aside className="sidebar-preview"><strong>Preview modul terlihat</strong><span>{[...new Set((data?.permissions ?? []).filter((permission) => draftPermissions.includes(permission.key) && permission.action === 'view').map((permission) => permission.module_label))].join(' · ') || 'Tidak ada modul'}</span></aside>
      {!editorSource.is_protected || isDuplicate ? <footer><label>Alasan perubahan<textarea value={changeReason} onChange={(event) => setChangeReason(event.target.value)} placeholder="Wajib untuk audit immutable."/></label>{selectedHasHighRisk && <label className="high-risk-confirm"><input type="checkbox" checked={highRiskConfirmed} onChange={(event) => setHighRiskConfirmed(event.target.checked)}/><span><AlertTriangle/><strong>Saya memahami izin berisiko tinggi yang dipilih.</strong></span></label>}<div><button onClick={() => setSelectedRoleId(null)}>Batal</button><button disabled={!canManage || saving || !dirty && !isDuplicate} onClick={() => void save()}><Save/> {saving ? 'Menyimpan…' : 'Simpan role'}</button></div></footer>
      : <footer className="owner-lock"><LockKeyhole/><span><strong>OWNER terkunci</strong><small>Gunakan Duplikat untuk membuat role baru tanpa mengubah OWNER.</small></span><Check/></footer>}
    </section></div>}
  </section>
}
