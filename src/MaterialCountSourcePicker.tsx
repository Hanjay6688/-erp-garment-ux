import { useEffect, useState } from 'react'
import type { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { parseMaterialLocations, type MaterialLocation, type MaterialPage } from './materialContract'
import { parseCountOptions, type CountIdentity, type CountOptions } from './materialCountContract'

type Props = {
  client: ReturnType<typeof getUatSupabaseClient>
  location?: { id: string; name: string }
  selected: readonly string[]
  disabled: boolean
  onSelect: (source: CountIdentity) => void
}

export default function MaterialCountSourcePicker({ client, location, selected, disabled, onSelect }: Props) {
  const [warehouseSearch, setWarehouseSearch] = useState('')
  const [warehouseQuery, setWarehouseQuery] = useState({ q: '', offset: 0 })
  const [warehouses, setWarehouses] = useState<MaterialPage<MaterialLocation> | null>(null)
  const [chosen, setChosen] = useState<{ id: string; name: string } | null>(null)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState({ q: '', offset: 0, revision: 0 })
  const [options, setOptions] = useState<CountOptions | null>(null)
  const [receivedRevision, setReceivedRevision] = useState(-1)
  const [warehouseError, setWarehouseError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const currentLocation = location ?? chosen
  const locationId = currentLocation?.id

  useEffect(() => {
    if (location) return
    let retired = false
    setWarehouses(null); setWarehouseError('')
    void (async () => {
      try {
        const r = await client.rpc('erp_cp7_get_material_locations_v1', { p_q: warehouseQuery.q, p_offset: warehouseQuery.offset, p_limit: 25 })
        if (retired) return
        if (r.error) throw r.error
        const page = parseMaterialLocations(r.data)
        if (page.offset !== warehouseQuery.offset || page.limit !== 25) throw Error('Daftar gudang tidak cocok dengan pencarian.')
        setWarehouses(page)
      } catch (e) { if (!retired) setWarehouseError(normalizeClientError(e).message) }
    })()
    return () => { retired = true }
  }, [client, warehouseQuery, location?.id])

  useEffect(() => {
    let retired = false
    setOptions(null); setError(''); setLoading(Boolean(locationId))
    if (locationId) void (async () => {
      const requested = { location_id: locationId, q: query.q, offset: query.offset, limit: 25 }
      try {
        const r = await client.rpc('erp_cp7_get_material_count_options_v1', { p_query: requested })
        if (retired) return
        if (r.error) throw r.error
        setOptions(parseCountOptions(r.data, requested)); setReceivedRevision(query.revision)
      } catch (e) { if (!retired) setError(normalizeClientError(e).message) }
      finally { if (!retired) setLoading(false) }
    })()
    return () => { retired = true }
  }, [client, locationId, query])

  // Bind selection during the render before an effect retires an old response.
  const visible = options && receivedRevision === query.revision && options.location_id === locationId && options.query === query.q && options.page.offset === query.offset ? options : null
  return <section className="panel cmat-count-sources" aria-label="Pilih bahan terdaftar">
    <h2>Barang belum muncul di saldo?</h2>
    <p>Pilih gudang dan bahan terdaftar, termasuk barang yang belum pernah bergerak di gudang ini. Saldo diperiksa saat pratinjau; jumlah fisik dan harga tetap diisi sesuai hasil pemeriksaan.</p>
    {location ? <p>Gudang pemeriksaan: <strong>{location.name}</strong></p> : <>
      <form className="cproc-search" onSubmit={e => { e.preventDefault(); setChosen(null); setWarehouseQuery({ q: warehouseSearch.trim(), offset: 0 }) }}>
        <label>Cari gudang pemeriksaan<input value={warehouseSearch} maxLength={120} onChange={e => setWarehouseSearch(e.target.value)} /></label>
        <button disabled={disabled}>Cari gudang pemeriksaan</button>
      </form>
      {warehouseError ? <p role="alert">{warehouseError}</p> : null}
      {warehouses?.rows.map(w => <button type="button" className="cproc-receipt" key={w.id} disabled={disabled} aria-pressed={w.id === chosen?.id} onClick={() => { setChosen(w); setQuery(q => ({ ...q, offset: 0, revision: q.revision + 1 })) }}><span><strong>{w.name}</strong><small>{w.code}</small></span></button>)}
      {warehouses ? <div className="cproc-pagination"><span>Total {warehouses.total} gudang</span><button disabled={disabled || !warehouses.offset} onClick={() => setWarehouseQuery(q => ({ ...q, offset: Math.max(0, warehouses.offset - 25) }))}>Gudang pemeriksaan sebelumnya</button><button disabled={disabled || warehouses.next_offset === null} onClick={() => setWarehouseQuery(q => ({ ...q, offset: warehouses.next_offset ?? 0 }))}>Gudang pemeriksaan berikutnya</button></div> : null}
    </>}
    {currentLocation ? <>
      <p>Barang yang dipilih akan dihitung di <strong>{currentLocation.name}</strong>.</p>
      <form className="cproc-search" onSubmit={e => { e.preventDefault(); setQuery(q => ({ q: search.trim(), offset: 0, revision: q.revision + 1 })) }}>
        <label>Cari bahan atau roll terdaftar<input value={search} maxLength={120} onChange={e => setSearch(e.target.value)} /></label><button disabled={disabled}>Cari barang terdaftar</button>
      </form>
      {loading ? <p role="status">Memuat bahan terdaftar…</p> : null}{error ? <p role="alert">{error}</p> : null}
      {!loading && visible?.page.rows.length === 0 ? <p>Bahan tidak ditemukan. Kain harus memiliki nomor roll terdaftar.</p> : null}
      {visible?.page.rows.map(r => {
        const picked = selected.includes(`${r.material_id}:${r.roll_id}`)
        return <article className="cmat-roll" key={`${r.material_id}:${r.roll_id}`}><div><strong>{r.roll_number ?? r.material_name}</strong><small>{r.material_sku} · {r.unit_code}</small><small>Saldo diperiksa saat pratinjau.</small></div><button disabled={disabled || loading || picked || selected.length >= 100} onClick={() => onSelect({ material_id: r.material_id, material_sku: r.material_sku, material_name: r.material_name, unit_code: r.unit_code, roll_id: r.roll_id, roll_number: r.roll_number, location_id: visible.location_id, location_name: visible.location_name })}>{picked ? 'Sudah dipilih' : `Tambahkan ${r.roll_number ?? r.material_name}`}</button></article>
      })}
      {visible ? <div className="cproc-pagination"><span>Total {visible.page.total} bahan / roll</span><button disabled={disabled || loading || !visible.page.offset} onClick={() => setQuery(q => ({ ...q, offset: Math.max(0, visible.page.offset - 25) }))}>Barang terdaftar sebelumnya</button><button disabled={disabled || loading || visible.page.next_offset === null} onClick={() => setQuery(q => ({ ...q, offset: visible.page.next_offset ?? 0 }))}>Barang terdaftar berikutnya</button></div> : null}
    </> : <p>Pilih gudang tempat barang dihitung.</p>}
  </section>
}
