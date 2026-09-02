import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Check, Plus, Search, X } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { parsePatternRows, type PatternRow } from './patternModel'
import './cutting-pattern-picker.css'

export type CuttingPatternChoice = Pick<PatternRow, 'id' | 'code' | 'revision' | 'name'>

export function hasCanonicalPattern(value: CuttingPatternChoice | null): value is CuttingPatternChoice {
  return Boolean(value?.id)
}

const demoPatterns: PatternRow[] = [
  { id: 'demo-pattern-reg-r1', code: 'REG', revision: 'R1', name: 'Regular', sort_order: 10, is_active: true, row_version: 1, updated_at: '', updated_by: null, usage_count: 0 },
  { id: 'demo-pattern-jumbo-r2', code: 'JUMBO', revision: 'R2', name: 'Jumbo', sort_order: 20, is_active: true, row_version: 1, updated_at: '', updated_by: null, usage_count: 0 },
]

export function createdPatternChoice(value: unknown): CuttingPatternChoice {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Respons quick-create Pola tidak valid.')
  const row = value as Record<string, unknown>
  if (typeof row.pattern_id !== 'string' || typeof row.code !== 'string' || typeof row.revision !== 'string' || typeof row.name !== 'string') {
    throw new Error('Identitas quick-create Pola tidak lengkap.')
  }
  return { id: row.pattern_id, code: row.code, revision: row.revision, name: row.name }
}

export function mergeCreatedPattern(rows: readonly PatternRow[], choice: CuttingPatternChoice): PatternRow[] {
  if (rows.some((row) => row.id === choice.id)) return [...rows]
  return [...rows, {
    ...choice, sort_order: 100, is_active: true, row_version: 1,
    updated_at: '', updated_by: null, usage_count: 0,
  }]
}

export default function CuttingPatternPicker({ value, onChange }: {
  value: CuttingPatternChoice | null
  onChange: (value: CuttingPatternChoice | null) => void
}) {
  const { runtime, identity } = useAuth()
  const connected = runtime.mode === 'UAT_AUTH_SIMULATION'
  const client = useMemo(() => connected ? getUatSupabaseClient(runtime) : null, [connected, runtime])
  const canManage = identity.status === 'DEMO'
    || (identity.status === 'AUTHORIZED' && hasPermission(identity, 'master.pattern.manage'))
  const [rows, setRows] = useState<PatternRow[]>(connected ? [] : demoPatterns)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(connected)
  const [error, setError] = useState('')
  const [quickOpen, setQuickOpen] = useState(false)
  const [code, setCode] = useState('')
  const [revision, setRevision] = useState('R1')
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const requestIdRef = useRef(globalThis.crypto.randomUUID())

  useEffect(() => {
    if (!client) return
    let cancelled = false
    const timer = globalThis.setTimeout(() => {
      setLoading(true)
      void client.rpc('erp_list_patterns_v1', {
        p_status: 'ACTIVE', p_query: query.trim() || null, p_limit: 30, p_offset: 0,
      }).then(({ data, error: loadError }) => {
        if (cancelled) return
        if (loadError) setError(normalizeClientError(loadError).message)
        else {
          try { setRows(parsePatternRows(data)) } catch (parseError) { setError(String(parseError)) }
        }
        setLoading(false)
      })
    }, 180)
    return () => { cancelled = true; globalThis.clearTimeout(timer) }
  }, [client, query])

  const visible = connected ? rows : rows.filter((row) =>
    `${row.code} ${row.revision} ${row.name}`.toLowerCase().includes(query.toLowerCase()))

  const openQuick = () => {
    if (!canManage) return
    setCode('')
    setRevision('R1')
    setName('')
    setError('')
    requestIdRef.current = globalThis.crypto.randomUUID()
    setQuickOpen(true)
  }

  const quickCreate = async () => {
    if (!canManage || saving) return
    const normalizedCode = code.trim().toUpperCase()
    const normalizedRevision = revision.trim().toUpperCase()
    const normalizedName = name.trim()
    if (!normalizedCode || !normalizedRevision || !normalizedName) {
      setError('Kode, revisi, dan nama Pola wajib diisi.')
      return
    }
    setSaving(true)
    try {
      let choice: CuttingPatternChoice
      if (!client) {
        choice = { id: `demo-${normalizedCode}-${normalizedRevision}`, code: normalizedCode, revision: normalizedRevision, name: normalizedName }
      } else {
        const { data, error: saveError } = await client.rpc('erp_save_pattern_v1', {
          p_payload: {
            code: normalizedCode, revision: normalizedRevision, name: normalizedName,
            sort_order: 100, change_reason: 'Quick-create dari draft Buat Potongan',
          },
          p_client_request_id: requestIdRef.current,
          p_expected_version: null,
        })
        if (saveError) throw normalizeClientError(saveError)
        choice = createdPatternChoice(data)
      }
      setRows((current) => mergeCreatedPattern(current, choice))
      onChange(choice)
      setQuickOpen(false)
      setQuery('')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : String(saveError))
    } finally {
      setSaving(false)
    }
  }

  return <section className="cutting-pattern-picker">
    <header><div><span>POLA · WAJIB</span><strong>{value ? `${value.code} · ${value.revision}` : 'Pilih atau buat Pola'}</strong><small>{value ? `${value.name} · pattern_id siap mengikat snapshot transaksi` : 'Master boleh kosong, tetapi Potongan baru wajib memiliki Pola.'}</small></div>{value && <button type="button" aria-label="Ganti Pola" title="Kosongkan pilihan sementara untuk mengganti Pola" onClick={() => onChange(null)}><X/></button>}</header>
    <label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari kode, revisi, atau nama Pola…"/></label>
    <div className="cutting-pattern-results" role="listbox" aria-label="Pola aktif">
      {loading ? <span>Memuat Pola aktif…</span> : visible.map((row) => <button type="button" role="option" aria-selected={value?.id === row.id} className={value?.id === row.id ? 'selected' : ''} key={row.id} onClick={() => onChange({ id: row.id, code: row.code, revision: row.revision, name: row.name })}><span><strong>{row.code} · {row.revision}</strong><small>{row.name}</small></span>{value?.id === row.id && <Check/>}</button>)}
      {!loading && visible.length === 0 && <span>Belum ada Pola aktif yang cocok.</span>}
    </div>
    <button type="button" className="cutting-pattern-add" disabled={!canManage} title={canManage ? 'Tambah ke Master Pola dan pilih otomatis' : 'Butuh permission master.pattern.manage'} onClick={openQuick}><Plus/> Tambah Pola Baru</button>
    {error && <div className="cutting-pattern-error" role="alert"><AlertTriangle/>{error}</div>}
    {quickOpen && <div className="cutting-pattern-quick"><label>Kode<input autoFocus value={code} onChange={(event) => setCode(event.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, '').slice(0, 32))} placeholder="REG"/></label><label>Revisi<input value={revision} onChange={(event) => setRevision(event.target.value.toUpperCase().replace(/[^A-Z0-9._-]/g, '').slice(0, 16))} placeholder="R1"/></label><label>Nama<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Regular"/></label><div><button type="button" onClick={() => setQuickOpen(false)}>Batal</button><button type="button" disabled={saving} onClick={() => void quickCreate()}>{saving ? 'Menyimpan…' : 'Buat & pilih'}</button></div></div>}
    <footer>{connected ? 'MASTER POLA UAT CONNECTED' : 'MASTER POLA SIMULATION'} · akses Buat Potongan tidak otomatis memberi hak membuat Pola.</footer>
  </section>
}
