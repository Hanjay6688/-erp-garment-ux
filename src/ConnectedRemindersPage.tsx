import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { cp6WibDateTimeInput, formatCp6WibDateTime } from './cp6BusinessTime'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { ProductionEnvelope } from './productionRecovery'
import {
  parseRemindersWorkspace, reminderCancelPayload, reminderCancelProblem, reminderDraftProblem, reminderFilterLabel, reminderFilters,
  reminderIdPayload, reminderPriorityLabel, reminderPriorities, reminderQuery, reminderRefusal, reminderSavePayload, validateReminderOutcome,
  withReminderRefusal, type ConnectedReminder, type ReminderDraft, type ReminderFilter, type ReminderPriority, type ReminderQuery, type RemindersWorkspace,
} from './remindersContract'
import './connected-reminders.css'

// R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): the Reminder menu on real data. Every row is a Native own-user manual
// reminder (erp.manual_reminders) read and written through the CP7 facade (erp_cp7_get_reminders_v1 / erp_cp7_save_reminder_v1),
// which checks the access catalog keys settings.reminder.view / .manage and keeps every Native rule. Writes carry one stable
// request UUID per attempt (useProductionMutation), so a lost reply is checked with the same UUID and never written twice.
const number = new Intl.NumberFormat('id-ID')
const empty: ReminderDraft = { title: '', note: '', dueWib: '', priority: 'NORMAL', module: 'Operasional' }
const dueLabel: Record<string, string> = { OVERDUE: 'Lewat jatuh tempo', TODAY: 'Hari ini', TOMORROW: 'Besok' }
type Editing = { id: string; rowVersion: number; original: ReminderDraft } | null

export default function ConnectedRemindersPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED' || !hasPermission(identity, 'settings.reminder.view'))
    return <section className="panel creminders-denied" role="alert">Hak melihat Reminder diperlukan untuk membuka pengingat.</section>
  return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function Workspace() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi pengingat belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('REMINDER')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const mayManage = hasPermission(identity, 'settings.reminder.manage')
  const serial = useRef(0), selected = useRef<ReminderQuery>(reminderQuery('ACTIVE')), titles = useRef(new Map<string, string>())
  const [data, setData] = useState<RemindersWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [filter, setFilter] = useState<ReminderFilter>('ACTIVE')
  const [draft, setDraft] = useState<ReminderDraft>(empty), [editing, setEditing] = useState<Editing>(null)
  const [cancelId, setCancelId] = useState(''), [reason, setReason] = useState('')

  const load = useCallback(async () => {
    const ticket = beginRead(), n = ++serial.current, query = selected.current
    setBusy(true); setError(''); setData(null)
    try {
      const reply = await client.rpc('erp_cp7_get_reminders_v1', { p_query: query })
      if (n !== serial.current || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      const parsed = parseRemindersWorkspace(reply.data, query)
      for (const r of parsed.items) titles.current.set(r.id, r.title)
      setData(parsed); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) { setData(null); setError(reminderRefusal((e as { message?: unknown })?.message) ?? normalizeClientError(e).message) }
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [beginRead, client, finishRead, isReadCurrent])
  useEffect(() => { void load() }, [load, recovery.scope])
  useEffect(() => () => { ++serial.current }, [])

  const choose = (next: ReminderFilter, offset = 0) => { setFilter(next); setDone(''); selected.current = reminderQuery(next, offset); void load() }
  const resetForm = () => { setDraft(empty); setEditing(null) }
  const handlers: ProductionMutationHandlers = {
    send: async (e: ProductionEnvelope) => {
      const reply = await client.rpc('erp_cp7_save_reminder_v1', { p_action: e.action, p_payload: e.payload, p_request: e.id,
        p_expected: e.expectedVersion === null ? null : String(e.expectedVersion) })
      return reply.error ? { data: reply.data, error: withReminderRefusal(reply.error) } : reply
    },
    validate: (value: unknown, e: ProductionEnvelope) => { validateReminderOutcome(value, e) },
    retire: (value: unknown, e: ProductionEnvelope) => {
      const r = validateReminderOutcome(value, e), payload = e.payload as { title?: unknown }
      const title = typeof payload.title === 'string' ? payload.title : titles.current.get(r.reminderId)
      const name = title ? `Pengingat "${title}"` : 'Pengingat'
      setDone(r.action === 'SAVE' ? (r.created ? `${name} ditambahkan.` : `Perubahan ${name.charAt(0).toLowerCase() + name.slice(1)} disimpan.`)
        : r.action === 'DONE' ? `${name} ditandai selesai.` : r.action === 'UNDONE' ? `${name} dibuka lagi.` : `${name} dibatalkan.`)
      if (r.action === 'SAVE' || editing?.id === r.reminderId) resetForm()
      if (cancelId === r.reminderId) { setCancelId(''); setReason('') }
      // A new reminder is OPEN: show it in the active list.
      if (r.created && !['ACTIVE', 'OPEN', 'ALL'].includes(selected.current.filter)) { selected.current = reminderQuery('ACTIVE'); setFilter('ACTIVE') }
    },
    reload: load,
  }
  const fresh = data !== null && !recovery.workspaceStale
  const writable = fresh && data.canManage && mayManage && !recovery.writerLocked && !busy
  const problem = reminderDraftProblem(draft)
  const unchanged = editing !== null && JSON.stringify(draft) === JSON.stringify(editing.original)
  const canSave = writable && problem === '' && !unchanged
  const save = () => {
    if (!canSave) return
    setDone('')
    void run('SAVE', reminderSavePayload(editing?.id ?? null, draft), editing?.rowVersion ?? null, handlers)
  }
  const act = (action: 'DONE' | 'UNDONE', r: ConnectedReminder) => { if (writable) { setDone(''); void run(action, reminderIdPayload(r.id), r.rowVersion, handlers) } }
  const cancel = (r: ConnectedReminder) => { if (writable && !reminderCancelProblem(reason)) { setDone(''); void run('CANCEL', reminderCancelPayload(r.id, reason), r.rowVersion, handlers) } }
  const edit = (r: ConnectedReminder) => {
    const original: ReminderDraft = { title: r.title, note: r.note, dueWib: cp6WibDateTimeInput(r.dueAt), priority: r.priority, module: r.module }
    setEditing({ id: r.id, rowVersion: r.rowVersion, original }); setDraft(original); setDone(''); setCancelId('')
  }
  const set = <K extends keyof ReminderDraft>(key: K, value: ReminderDraft[K]) => setDraft(current => ({ ...current, [key]: value }))

  return <main className="creminders" aria-label="Pengingat">
    <header className="panel creminders-head">
      <div><div className="eyebrow">PENGATURAN & AUDIT</div><h1>Pengingat</h1>
        <p>Pengingat kerja pribadi akun ini. Hanya akun ini yang melihatnya; tidak dikirim lewat WhatsApp, email, atau notifikasi.</p></div>
      <button type="button" disabled={busy} onClick={() => { setDone(''); void load() }}>Muat ulang pengingat</button>
    </header>
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="panel creminders-alert" reconcileLabel="Periksa hasil simpan pengingat"/> : null}
    {done ? <p className="panel creminders-done" role="status">{done}</p> : null}
    {error ? <p className="panel creminders-alert" role="alert">{error}</p> : null}
    {busy && !data ? <p className="panel creminders-loading" role="status">Memuat pengingat…</p> : null}
    {data ? <>
      <section className="panel creminders-summary" aria-label="Ringkasan pengingat">
        <p><strong>{number.format(data.counts.open)}</strong> belum selesai · <strong>{number.format(data.counts.done)}</strong> sudah selesai · <strong>{number.format(data.counts.cancelled)}</strong> dibatalkan</p>
        <p>{data.due.complete
          ? <>{number.format(data.due.overdue)} lewat jatuh tempo · {number.format(data.due.today)} jatuh tempo hari ini · {number.format(data.due.tomorrow)} besok (WIB)</>
          : <>Hitungan jatuh tempo belum lengkap karena ada lebih dari {number.format(200)} pengingat belum selesai.</>}</p>
        <small>Dibaca {formatCp6WibDateTime(data.readAt)}.</small>
      </section>
      <section className="reminder-layout">
        <section className="panel reminder-browser" aria-label="Daftar pengingat">
          <header><div><span>DAFTAR PENGINGAT · {reminderFilterLabel[data.filter].toUpperCase()}</span>
            <strong>{data.page.total === 0 ? 'Tidak ada pengingat' : `${number.format(data.page.offset + 1)}–${number.format(data.page.offset + data.page.shown)} dari ${number.format(data.page.total)}`}</strong></div>
            <div className="reminder-filters" role="group" aria-label="Saring pengingat">{reminderFilters.map(f =>
              <button type="button" key={f} className={filter === f ? 'active' : ''} aria-pressed={filter === f} disabled={busy} onClick={() => choose(f)}>{reminderFilterLabel[f]}</button>)}</div>
          </header>
          {data.page.beyondWindow > 0 ? <p className="creminders-window" role="note">{number.format(data.page.beyondWindow)} pengingat lain di daftar ini belum bisa ditampilkan (paling banyak {number.format(200)} per daftar). Selesaikan atau batalkan pengingat lama supaya sisanya muncul.</p> : null}
          <div className="reminder-list">
            {data.items.map(r => <Item key={r.id} r={r} writable={writable} manage={data.canManage && mayManage} cancelOpen={cancelId === r.id} reason={reason}
              onEdit={() => edit(r)} onDone={() => act('DONE', r)} onUndone={() => act('UNDONE', r)}
              onCancelOpen={() => { setCancelId(r.id); setReason(''); setDone('') }} onCancelClose={() => { setCancelId(''); setReason('') }}
              onReason={setReason} onCancel={() => cancel(r)}/>)}
            {data.items.length === 0 ? <div className="reminder-empty"><strong>Belum ada pengingat di daftar ini.</strong>
              <small>{data.canManage && mayManage ? 'Tambahkan pengingat lewat isian di samping, atau buka daftar lain.' : 'Buka daftar lain.'}</small></div> : null}
          </div>
          {data.page.offset > 0 || data.page.nextOffset !== null ? <div className="creminders-pages">
            <button type="button" disabled={busy || data.page.offset === 0} onClick={() => choose(data.filter, Math.max(0, data.page.offset - data.page.limit))}>Pengingat sebelumnya</button>
            <button type="button" disabled={busy || data.page.nextOffset === null} onClick={() => choose(data.filter, data.page.nextOffset ?? 0)}>Pengingat berikutnya</button>
          </div> : null}
        </section>
        {data.canManage && mayManage ? <aside className="panel reminder-editor" aria-label="Isian pengingat">
          <header><span>{editing ? 'UBAH PENGINGAT' : 'PENGINGAT BARU'}</span><strong>{editing ? 'Hanya pengingat yang belum selesai bisa diubah' : 'Tambahkan pengingat untuk akun ini'}</strong></header>
          <label><span>JUDUL · WAJIB</span><input aria-label="Judul pengingat" maxLength={200} value={draft.title} disabled={!writable} onChange={e => set('title', e.target.value)}/></label>
          <label><span>CATATAN</span><textarea aria-label="Catatan pengingat" maxLength={4000} value={draft.note} disabled={!writable} onChange={e => set('note', e.target.value)}/></label>
          <div className="reminder-editor-grid">
            <label><span>JATUH TEMPO (WIB)</span><input type="datetime-local" aria-label="Jatuh tempo pengingat (WIB)" value={draft.dueWib} disabled={!writable} onChange={e => set('dueWib', e.target.value)}/></label>
            <label><span>PRIORITAS</span><select aria-label="Prioritas pengingat" value={draft.priority} disabled={!writable} onChange={e => set('priority', e.target.value as ReminderPriority)}>
              {reminderPriorities.map(p => <option key={p} value={p}>{reminderPriorityLabel[p]}</option>)}</select></label>
          </div>
          <label><span>MODUL / KONTEKS</span><input aria-label="Modul pengingat" maxLength={80} value={draft.module} disabled={!writable} onChange={e => set('module', e.target.value)}/></label>
          {problem && (draft.title || draft.dueWib || editing) ? <p className="creminders-problem">{problem}</p> : unchanged ? <p className="creminders-problem">Belum ada yang diubah.</p> : null}
          <div className="reminder-editor-actions">
            {editing ? <button type="button" className="soft-btn" disabled={recovery.busy} onClick={resetForm}>Batal ubah</button> : null}
            <button type="button" className="primary-btn" disabled={!canSave} onClick={save}>{editing ? 'Simpan perubahan' : 'Tambah pengingat'}</button>
          </div>
        </aside> : <aside className="panel reminder-editor creminders-readonly" aria-label="Isian pengingat"><p>Akun ini hanya bisa melihat pengingat. Menambah dan mengubah butuh hak Kelola Reminder.</p></aside>}
      </section>
    </> : null}
  </main>
}

function Item({ r, writable, manage, cancelOpen, reason, onEdit, onDone, onUndone, onCancelOpen, onCancelClose, onReason, onCancel }: {
  r: ConnectedReminder; writable: boolean; manage: boolean; cancelOpen: boolean; reason: string
  onEdit: () => void; onDone: () => void; onUndone: () => void; onCancelOpen: () => void; onCancelClose: () => void; onReason: (value: string) => void; onCancel: () => void
}) {
  const reasonProblem = reminderCancelProblem(reason)
  return <article className={`${r.status.toLowerCase()} ${r.priority.toLowerCase()}`} aria-label={`Pengingat ${r.title}`}>
    <div className="reminder-copy">
      <span>{r.module} · {reminderPriorityLabel[r.priority]}</span>
      <strong>{r.title}</strong>
      <p>{r.note || 'Tidak ada catatan.'}</p>
      <small>Jatuh tempo {formatCp6WibDateTime(r.dueAt)}{r.dueState && dueLabel[r.dueState] ? <b className={`creminders-due ${r.dueState.toLowerCase()}`}>{dueLabel[r.dueState]}</b> : null}</small>
      <small className="creminders-status">{r.status === 'OPEN' ? 'Belum selesai'
        : r.status === 'DONE' ? `Selesai ${formatCp6WibDateTime(r.completedAt ?? '')}`
        : `Dibatalkan ${formatCp6WibDateTime(r.cancelledAt ?? '')}: ${r.cancellationReason ?? ''}`}</small>
    </div>
    {manage && r.status !== 'CANCELLED' ? <div className="reminder-actions">
      {r.status === 'OPEN' ? <>
        <button type="button" aria-label={`Tandai selesai ${r.title}`} disabled={!writable} onClick={onDone}>Tandai selesai</button>
        <button type="button" aria-label={`Ubah ${r.title}`} disabled={!writable} onClick={onEdit}>Ubah</button>
      </> : <button type="button" aria-label={`Buka lagi ${r.title}`} disabled={!writable} onClick={onUndone}>Buka lagi</button>}
      <button type="button" className="danger" aria-label={`Batalkan ${r.title}`} disabled={!writable || cancelOpen} onClick={onCancelOpen}>Batalkan</button>
    </div> : null}
    {cancelOpen ? <div className="creminders-cancel" role="group" aria-label={`Batalkan pengingat ${r.title}`}>
      <label>Alasan batal<input aria-label={`Alasan batal ${r.title}`} maxLength={1000} value={reason} disabled={!writable} onChange={e => onReason(e.target.value)}/></label>
      <p className="creminders-problem">{reasonProblem || 'Pengingat yang dibatalkan tidak bisa dibuka lagi.'}</p>
      <div><button type="button" className="danger" disabled={!writable || reasonProblem !== ''} onClick={onCancel}>Batalkan pengingat</button>
        <button type="button" onClick={onCancelClose}>Tutup</button></div>
    </div> : null}
  </article>
}
