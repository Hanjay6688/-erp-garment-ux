import { isConnectedRuntime } from './config/runtime'
import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Check, ChevronDown, Layers3, Plus, Search, X } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { hasPermission } from './auth/accessCatalog'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { parsePatternRows, type PatternRow } from './patternModel'
import './cutting-pattern-picker.css'
import { patterns as garmentPatterns } from './demo/planner/model'

export type CuttingPatternChoice = Pick<PatternRow, 'id' | 'code' | 'revision' | 'name'>

export function hasCanonicalPattern(value: CuttingPatternChoice | null): value is CuttingPatternChoice {
  return Boolean(value?.id)
}

const demoPatterns: PatternRow[] = [
  ...garmentPatterns.map((pattern,index)=>({...pattern, sort_order:index, is_active:true, row_version:1, updated_at:'',updated_by:null,usage_count:0})),
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

export default function CuttingPatternPicker({ value, onChange, suspended = false, onAuthorityLost, layout = 'standard' }: {
  value: CuttingPatternChoice | null
  onChange: (value: CuttingPatternChoice | null) => void
  suspended?: boolean
  onAuthorityLost?: () => void
  layout?: 'standard' | 'workbench'
}) {
  const workbench = layout === 'workbench'
  const { runtime, identity } = useAuth()
  const connected = isConnectedRuntime(runtime)
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
  const savingRef = useRef(false)
  const requestIdRef = useRef(globalThis.crypto.randomUUID())
  const searchRef = useRef<HTMLInputElement>(null)
  const changeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!client) return
    setRows([])
    if (suspended) return
    let cancelled = false
    const timer = globalThis.setTimeout(() => {
      setLoading(true)
      setError('')
      void (async () => {
        try {
          const { data, error: loadError } = await client.rpc('erp_list_patterns_v1', {
            p_status: 'ACTIVE', p_query: query.trim() || null, p_limit: 30, p_offset: 0,
          })
          if (cancelled) return
          if (loadError) {
            const failure = normalizeClientError(loadError)
            setError(failure.message)
            if (['FORBIDDEN', 'AUTH_REQUIRED'].includes(failure.code)) onAuthorityLost?.()
            return
          }
          setRows(parsePatternRows(data))
        } catch (loadFailure) {
          if (!cancelled) setError(loadFailure instanceof Error ? loadFailure.message : normalizeClientError(loadFailure).message)
        } finally {
          if (!cancelled) setLoading(false)
        }
      })()
    }, 180)
    return () => { cancelled = true; globalThis.clearTimeout(timer) }
  }, [client, query, suspended, onAuthorityLost])

  const visible = connected ? rows : rows.filter((row) =>
    `${row.code} ${row.revision} ${row.name}`.toLowerCase().includes(query.toLowerCase()))

  function choosePattern(choice: CuttingPatternChoice) {
    onChange(choice)
    if (workbench) {
      setQuery('')
      setQuickOpen(false)
      setError('')
      requestAnimationFrame(() => changeRef.current?.focus({ preventScroll: true }))
    }
  }

  function clearPattern() {
    onChange(null)
    if (workbench) requestAnimationFrame(() => searchRef.current?.focus())
  }

  const openQuick = () => {
    if (suspended || !canManage) return
    setCode('')
    setRevision('R1')
    setName('')
    setError('')
    requestIdRef.current = globalThis.crypto.randomUUID()
    setQuickOpen(true)
  }

  const quickCreate = async () => {
    if (suspended || !canManage || savingRef.current) return
    const normalizedCode = code.trim().toUpperCase()
    const normalizedRevision = revision.trim().toUpperCase()
    const normalizedName = name.trim()
    if (!normalizedCode || !normalizedRevision || !normalizedName) {
      setError('Kode, revisi, dan nama Pola wajib diisi.')
      return
    }
    savingRef.current = true
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
      choosePattern(choice)
      setQuickOpen(false)
      setQuery('')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : String(saveError))
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return <section className={`cutting-pattern-picker${workbench ? ' cutting-pattern-workbench' : ''}`} aria-hidden={suspended || undefined} style={suspended ? { display: 'none' } : undefined}>
    <header>
      {workbench && <i><Layers3 aria-hidden="true"/></i>}
      <div><span>POLA · WAJIB</span>
        {workbench ? <><strong>{value?.name ?? 'Pilih pola potongan'}</strong>{value && <small>{value.code} · {value.revision}</small>}</>
          : <><strong>{value ? `${value.code} · ${value.revision}` : 'Pilih atau buat Pola'}</strong><small>{value ? `${value.name} · pattern_id siap mengikat snapshot transaksi` : 'Master boleh kosong, tetapi Potongan baru wajib memiliki Pola.'}</small></>}
      </div>
      {value && <button ref={changeRef} type="button" aria-label="Ganti Pola" onClick={clearPattern}>
        {workbench ? <>Ganti Pola <ChevronDown aria-hidden="true"/></> : <X aria-hidden="true"/>}
      </button>}
    </header>
    {(!workbench || !value) && <>
      <label><Search aria-hidden="true"/><input ref={searchRef} aria-label="Cari pola potongan" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari kode, revisi, atau nama Pola…"/></label>
      <div className="cutting-pattern-results" role="listbox" aria-label="Pola aktif">
        {loading ? <span>Memuat Pola aktif…</span> : visible.map(row => {
          const codeRevision = `${row.code} · ${row.revision}`
          return <button type="button" role="option" aria-selected={value?.id === row.id} className={value?.id === row.id ? 'selected' : ''} key={row.id} onClick={() => choosePattern({ id: row.id, code: row.code, revision: row.revision, name: row.name })}>
            <span><strong>{workbench ? row.name : codeRevision}</strong><small>{workbench ? codeRevision : row.name}</small></span>
            {value?.id === row.id && <Check aria-hidden="true"/>}
          </button>
        })}
        {!loading && visible.length === 0 && <span>Belum ada Pola aktif yang cocok.</span>}
      </div>
      <button type="button" className="cutting-pattern-add" disabled={!canManage} title={canManage ? 'Tambah ke Master Pola dan pilih otomatis' : 'Butuh permission master.pattern.manage'} onClick={openQuick}><Plus aria-hidden="true"/> Tambah Pola Baru</button>
      {error && <div className="cutting-pattern-error" role="alert"><AlertTriangle aria-hidden="true"/>{error}</div>}
      {quickOpen && <div className="cutting-pattern-quick"><label>Kode<input autoFocus value={code} onChange={(event) => setCode(event.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, '').slice(0, 32))} placeholder="REG"/></label><label>Revisi<input value={revision} onChange={(event) => setRevision(event.target.value.toUpperCase().replace(/[^A-Z0-9._-]/g, '').slice(0, 16))} placeholder="R1"/></label><label>Nama<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Regular"/></label><div><button type="button" onClick={() => setQuickOpen(false)}>Batal</button><button type="button" disabled={saving} onClick={() => void quickCreate()}>{saving ? 'Menyimpan…' : 'Buat & pilih'}</button></div></div>}
    </>}
    <footer>{connected ? 'MASTER POLA UAT CONNECTED' : 'MASTER POLA SIMULATION'}{(!workbench || !canManage) && ' · akses Buat Potongan tidak otomatis memberi hak membuat Pola.'}</footer>
  </section>
}
