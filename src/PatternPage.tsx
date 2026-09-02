import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Check, History, Plus, RefreshCw, Save, Search, SlidersHorizontal, X } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { parsePatternRows, parsePatternTotal, sortPatternRows, type PatternRow } from './patternModel'
import './pattern-page.css'

const demoPatterns: PatternRow[] = [
  { id: 'demo-1', code: 'REG', revision: 'R1', name: 'Regular', sort_order: 10, is_active: true, row_version: 1, updated_at: '2026-09-02T00:00:00Z', updated_by: 'Owner', usage_count: 3 },
  { id: 'demo-2', code: 'SLIM', revision: 'R2', name: 'Slim', sort_order: 20, is_active: true, row_version: 1, updated_at: '2026-09-02T00:00:00Z', updated_by: 'Owner', usage_count: 1 },
  { id: 'demo-3', code: 'OLD', revision: 'R1', name: 'Pola Lama', sort_order: 90, is_active: false, row_version: 2, updated_at: '2026-08-01T00:00:00Z', updated_by: 'Owner', usage_count: 8 },
]


function localDate(value: string) {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? 'Tidak tersedia' : parsed.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' })
}

export default function PatternPage() {
  const { runtime, identity } = useAuth()
  const connected = runtime.mode === 'UAT_AUTH_SIMULATION'
  const client = useMemo(() => runtime.mode === 'UAT_AUTH_SIMULATION' ? getUatSupabaseClient(runtime) : null, [runtime])
  const canManage = identity.status === 'DEMO' || (identity.status === 'AUTHORIZED' && hasPermission(identity, 'master.pattern.manage'))
  const [rows, setRows] = useState<PatternRow[]>(connected ? [] : demoPatterns)
  const [total, setTotal] = useState(connected ? 0 : demoPatterns.length)
  const [loading, setLoading] = useState(connected)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [stateFilter, setStateFilter] = useState<'ACTIVE' | 'INACTIVE' | 'ALL'>('ACTIVE')
  const [editing, setEditing] = useState<PatternRow | 'NEW' | null>(null)
  const [code, setCode] = useState('')
  const [revision, setRevision] = useState('R1')
  const [name, setName] = useState('')
  const [sortOrder, setSortOrder] = useState('100')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [offset, setOffset] = useState(0)
  const pageSize = 100

  const load = useCallback(async () => {
    if (!client) { setRows(demoPatterns); setTotal(demoPatterns.length); return }
    setLoading(true)
    setError('')
    const { data, error: loadError } = await client.rpc('erp_list_patterns_v1', {
      p_status: stateFilter, p_query: query.trim() || null, p_limit: pageSize, p_offset: offset,
    })
    if (loadError) setError(normalizeClientError(loadError).message)
    else {
      try {
        const parsed = parsePatternRows(data)
        setRows(parsed)
        setTotal(parsePatternTotal(data, parsed))
      } catch (parseError) { setError(String(parseError)) }
    }
    setLoading(false)
  }, [client, offset, query, stateFilter])

  useEffect(() => {
    const timer = globalThis.setTimeout(() => { void load() }, connected ? 180 : 0)
    return () => globalThis.clearTimeout(timer)
  }, [connected, load])
  useEffect(() => { setOffset(0) }, [query, stateFilter])

  const visible = sortPatternRows(connected ? rows : rows
    .filter((row) => stateFilter === 'ALL' || (stateFilter === 'ACTIVE' ? row.is_active : !row.is_active))
    .filter((row) => `${row.code} ${row.revision} ${row.name}`.toLowerCase().includes(query.toLowerCase())))

  const openEditor = (row: PatternRow | 'NEW') => {
    setEditing(row)
    setCode(row === 'NEW' ? '' : row.code)
    setRevision(row === 'NEW' ? 'R1' : row.revision)
    setName(row === 'NEW' ? '' : row.name)
    setSortOrder(String(row === 'NEW' ? 100 : row.sort_order))
    setReason('')
    setError('')
  }

  const save = async () => {
    if (!editing || !canManage || saving) return
    const parsedSort = Number(sortOrder)
    if (!code.trim() || !revision.trim() || !name.trim() || !Number.isInteger(parsedSort) || parsedSort < 0 || !reason.trim()) {
      setError('Kode, revisi, nama, urutan nonnegatif, dan alasan perubahan wajib diisi.')
      return
    }
    if (!client) { setError('DATA SIMULASI · perubahan Pola tidak dikirim ke backend.'); return }
    setSaving(true)
    const current = editing === 'NEW' ? null : editing
    const { error: saveError } = await client.rpc('erp_save_pattern_v1', {
      p_payload: {
        ...(current ? { id: current.id } : {}), code: code.trim().toUpperCase(),
        revision: revision.trim().toUpperCase(), name: name.trim(), sort_order: parsedSort, change_reason: reason.trim(),
      },
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: current?.row_version ?? null,
    })
    if (saveError) setError(normalizeClientError(saveError).message)
    else { setEditing(null); await load() }
    setSaving(false)
  }

  const deactivate = async (row: PatternRow) => {
    if (!client || !canManage || !globalThis.confirm(`Nonaktifkan Pola ${row.code}? Riwayat pemakaian tetap dipertahankan.`)) return
    const changeReason = globalThis.prompt('Alasan menonaktifkan Pola:')?.trim()
    if (!changeReason) return
    const { error: deactivateError } = await client.rpc('erp_deactivate_pattern_v1', {
      p_pattern_id: row.id,
      p_reason: changeReason,
      p_client_request_id: globalThis.crypto.randomUUID(),
      p_expected_version: row.row_version,
    })
    if (deactivateError) setError(normalizeClientError(deactivateError).message)
    else await load()
  }

  return <section className="pattern-page">
    <header className="pattern-hero"><div><span>MASTER DATA · METADATA PRODUKSI</span><h1>Pola</h1><p>Pola hanya mengatur kontrol, filter, dan urutan tampilan. Pola tidak mengubah stok, HPP, payroll, jurnal, atau identitas Final SKU.</p></div><button disabled={!canManage} onClick={() => openEditor('NEW')}><Plus/> Pola baru</button></header>
    <div className={`pattern-truth ${connected ? 'connected' : 'simulation'}`}><SlidersHorizontal/><strong>{connected ? 'UAT BACKEND CONNECTED' : 'DATA SIMULASI'}</strong><span>Histori lama tanpa Pola tetap terbaca · Potongan baru wajib memakai pattern_id</span></div>
    {error && <div className="pattern-error" role="alert"><AlertTriangle/><span>{error}</span><button onClick={() => setError('')}><X/></button></div>}
    <section className="pattern-workspace">
      <header><label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari kode, revisi, atau nama Pola…"/></label><div role="tablist" aria-label="Status Pola">{(['ACTIVE', 'INACTIVE', 'ALL'] as const).map((filter) => <button className={stateFilter === filter ? 'active' : ''} onClick={() => setStateFilter(filter)} key={filter}>{filter === 'ACTIVE' ? 'Aktif' : filter === 'INACTIVE' ? 'Nonaktif' : 'Semua'}</button>)}</div><button className="pattern-refresh" onClick={() => void load()}><RefreshCw/> Refresh</button></header>
      {loading ? <div className="pattern-empty"><RefreshCw className="spin"/><strong>Memuat Pola authoritative…</strong></div> : <div className="pattern-table"><div className="pattern-table-head"><span>Urutan</span><span>Kode, revisi & nama</span><span>Status</span><span>Riwayat</span><span>Aksi</span></div>{visible.map((row) => <article key={row.id} className={!row.is_active ? 'inactive' : ''}><strong className="pattern-order">{row.sort_order}</strong><div><strong>{row.code} · {row.revision}</strong><span>{row.name}</span></div><em>{row.is_active ? <><Check/> AKTIF</> : 'NONAKTIF'}</em><div className="pattern-history"><History/><span><strong>{row.usage_count} pemakaian</strong><small>{localDate(row.updated_at)} · {row.updated_by || 'System'}</small></span></div><div className="pattern-actions"><button disabled={!canManage || !row.is_active} onClick={() => openEditor(row)}>Edit</button><button disabled={!canManage || !row.is_active} onClick={() => void deactivate(row)}>Nonaktifkan</button></div></article>)}{visible.length === 0 && <div className="pattern-empty"><Search/><strong>{total === 0 && !query ? 'Master Pola masih kosong—buat saat pola pertama benar-benar dipakai.' : 'Tidak ada Pola yang cocok.'}</strong></div>}<footer className="pattern-pagination"><span>{total} Pola · {offset + (visible.length ? 1 : 0)}–{Math.min(offset + visible.length, total)}</span><div><button disabled={!connected || offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Sebelumnya</button><button disabled={!connected || offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)}>Berikutnya</button></div></footer></div>}
    </section>

    {editing && <div className="pattern-editor-layer" role="presentation" onMouseDown={() => setEditing(null)}><section className="pattern-editor" role="dialog" aria-modal="true" aria-labelledby="pattern-editor-title" onMouseDown={(event) => event.stopPropagation()}><header><div><span>{editing === 'NEW' ? 'POLA BARU' : 'EDIT POLA'}</span><h2 id="pattern-editor-title">{editing === 'NEW' ? 'Buat Master Pola' : editing.name}</h2></div><button onClick={() => setEditing(null)}><X/></button></header><div><label>Kode stabil<input autoFocus value={code} disabled={editing !== 'NEW'} onChange={(event) => setCode(event.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, '').slice(0, 32))} placeholder="REG"/></label><label>Revisi stabil<input value={revision} disabled={editing !== 'NEW'} onChange={(event) => setRevision(event.target.value.toUpperCase().replace(/[^A-Z0-9._-]/g, '').slice(0, 16))} placeholder="R1"/></label><label>Nama Pola<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Regular"/></label><label>Urutan tampil<input type="number" min="0" max="999999" value={sortOrder} onChange={(event) => setSortOrder(event.target.value)}/></label><label className="pattern-reason">Alasan perubahan<textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Wajib untuk audit."/></label></div><aside><AlertTriangle/><span><strong>Kode + revisi adalah identitas stabil; urutan hanya presentation metadata.</strong><small>Buat revisi baru bila bentuk fisik Pola berubah. Edit master tidak menulis ulang snapshot Potongan lama.</small></span></aside><footer><button onClick={() => setEditing(null)}>Batal</button><button disabled={saving || !canManage} onClick={() => void save()}><Save/> {saving ? 'Menyimpan…' : 'Simpan Pola'}</button></footer></section></div>}
  </section>
}
