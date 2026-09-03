import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Search } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import { parsePatternRows, type PatternRow } from './patternModel'
import './connected-pattern-filter.css'

type KnownPattern = Pick<PatternRow, 'id' | 'code' | 'revision' | 'name' | 'is_active'>

export default function ConnectedPatternFilter({ value, onChange, label = 'FILTER POLA' }: {
  value: string
  onChange: (patternId: string) => void
  label?: string
}) {
  const { runtime } = useAuth()
  if (runtime.mode !== 'UAT_AUTH_SIMULATION') throw new Error('ConnectedPatternFilter hanya untuk ERP Enteng UAT.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const [query, setQuery] = useState('')
  const [rows, setRows] = useState<PatternRow[]>([])
  const [selected, setSelected] = useState<KnownPattern | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const timer = globalThis.setTimeout(() => {
      setLoading(true)
      void client.rpc('erp_list_patterns_v1', {
        p_status: 'ALL', p_query: query.trim() || null, p_limit: 50, p_offset: 0,
      }).then(({ data, error: loadError }) => {
        if (cancelled) return
        if (loadError) setError(normalizeClientError(loadError).message)
        else {
          try {
            const parsed = parsePatternRows(data)
            setRows(parsed)
            const match = parsed.find((row) => row.id === value)
            if (match) setSelected(match)
            setError('')
          } catch (parseError) {
            setError(parseError instanceof Error ? parseError.message : String(parseError))
          }
        }
        setLoading(false)
      })
    }, 180)
    return () => { cancelled = true; globalThis.clearTimeout(timer) }
  }, [client, query, value])

  const options = selected && !rows.some((row) => row.id === selected.id) ? [selected, ...rows] : rows

  return <div className="connected-pattern-filter">
    <span>{label}</span>
    <label><Search/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari kode, revisi, nama…"/></label>
    <select aria-label={label} value={value} disabled={loading && rows.length === 0} onChange={(event) => {
      const next = event.target.value
      setSelected(rows.find((row) => row.id === next) ?? null)
      onChange(next)
    }}>
      <option value="">Semua Pola</option>
      {options.map((pattern) => <option value={pattern.id} key={pattern.id}>{pattern.is_active ? '' : '[Nonaktif] '}{pattern.code} · {pattern.revision} · {pattern.name}</option>)}
    </select>
    {error ? <small role="alert"><AlertTriangle/>{error}</small> : <small>{loading ? 'Mengambil Master Pola…' : `${rows.length} hasil · server-side search`}</small>}
  </div>
}
