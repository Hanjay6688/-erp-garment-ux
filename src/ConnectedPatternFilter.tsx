import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import BrowsePicker from './components/BrowsePicker'
import type { BrowseOption } from './components/BrowsePicker'
import { normalizeClientError } from './lib/clientError'
import { getUatSupabaseClient } from './lib/supabase'
import { parsePatternRows, type PatternRow } from './patternModel'
import './connected-pattern-filter.css'

type KnownPattern = Pick<PatternRow, 'id' | 'code' | 'revision' | 'name' | 'is_active'>

export default function ConnectedPatternFilter({ value, onChange, label = 'FILTER POLA', tone = 'light' }: {
  value: string
  onChange: (patternId: string) => void
  label?: string
  // The light Connected pages (pickup, WIP) vs the dark CP5 BS page.
  tone?: 'dark' | 'light'
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
      setError('')
      const fetchPatterns = async () => {
        try {
          const { data, error: loadError } = await client.rpc('erp_list_patterns_v1', {
            p_status: 'ALL', p_query: query.trim() || null, p_limit: 50, p_offset: 0,
          })
          if (cancelled) return
          if (loadError) {
            setError(normalizeClientError(loadError).message)
            return
          }
          const parsed = parsePatternRows(data)
          setRows(parsed)
          const match = parsed.find((row) => row.id === value)
          setSelected((current) => match ?? (current?.id === value ? current : null))
        } catch (loadFailure) {
          if (!cancelled) setError(normalizeClientError(loadFailure).message)
        } finally {
          if (!cancelled) setLoading(false)
        }
      }
      void fetchPatterns()
    }, 180)
    return () => { cancelled = true; globalThis.clearTimeout(timer) }
  }, [client, query, value])

  const options = selected && !rows.some((row) => row.id === selected.id) ? [selected, ...rows] : rows
  // Server-side search: what is typed in the popdown goes to erp_list_patterns_v1
  // (debounced above); "Semua Pola" stays reachable whatever the search.
  const pickerOptions: BrowseOption[] = [
    { id: '', label: 'Semua Pola', detail: 'Tanpa filter Pola', pinned: true },
    ...options.map((pattern) => ({
      id: pattern.id,
      label: `${pattern.code} · ${pattern.revision}`,
      detail: pattern.name,
      meta: pattern.is_active ? undefined : 'Nonaktif',
      keywords: `${pattern.code} ${pattern.revision} ${pattern.name}`,
    })),
  ]

  return <div className={`connected-pattern-filter ${tone === 'dark' ? 'tone-dark' : 'tone-light'}`}>
    <BrowsePicker
      label={label}
      tone={tone}
      size="compact"
      value={value}
      options={pickerOptions}
      // As before: locked only while the first list is still loading (a search
      // with no match keeps the popdown usable).
      disabled={loading && rows.length === 0 && query.trim() === ''}
      onChange={(next) => {
        if (next === value) return
        setSelected(options.find((row) => row.id === next) ?? null)
        onChange(next)
      }}
      onQueryChange={setQuery}
      filterOptions={false}
      status={loading ? 'Mengambil…' : `${rows.length} hasil`}
      placeholder="Semua Pola"
      searchPlaceholder="Cari kode, revisi, nama…"
      emptyText="Pola tidak ditemukan. Coba kode, revisi, atau nama lain."
    />
    {error ? <small role="alert"><AlertTriangle/>{error}</small> : <small>{loading ? 'Mengambil Master Pola…' : `${rows.length} hasil · server-side search`}</small>}
  </div>
}
