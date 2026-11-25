import { useState, type FormEvent } from 'react'
import { ArrowLeft, Pencil } from 'lucide-react'
import { browseMatch } from '../browseMatch'
import { laundryProcesses } from './laundryModel'
import { emptyInstructions, readLaundryRecipes, saveLaundryRecipe, type LaundryRecipe } from './laundryRecipes'
import { usePlannerSession } from './planner/session'
import { laundryVendorNames } from './sewingModel'
import { allSkus } from './skuCatalog'
import { fixtureDate } from './accessoryPricing'
import { lastWarehouseDay } from './warehouseDay'
import './warehouseForms.css'
import './pocketFabric.css'
import './laundryRecipe.css'

export default function LaundryRecipeMaster() {
  const skus = allSkus(usePlannerSession())
  const params = new URLSearchParams(location.search)
  const [rows, setRows] = useState(readLaundryRecipes)
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState<LaundryRecipe>(() => ({
    ...emptyInstructions,
    vendor: params.get('vendor') ?? '',
    sku: params.get('sku') ?? '',
    from: params.get('tanggal') ?? fixtureDate,
  }))
  const [notice, setNotice] = useState<{ text: string; error?: boolean }>()
  const visible = rows.filter(r => browseMatch(query, r.vendor, r.sku, r.colourProcess, r.colour, r.service))
  const set = (change: Partial<LaundryRecipe>) => { setDraft(current => ({ ...current, ...change })); setNotice(undefined) }

  function save(event: FormEvent) {
    event.preventDefault()
    try {
      if (!skus.some(sku => sku.key === draft.sku)) throw Error('Pilih SKU aktif.')
      setRows(saveLaundryRecipe(draft))
      setNotice({ text: 'Instruksi ' + draft.sku + ' untuk ' + draft.vendor + ' disimpan.' })
    } catch (error) { setNotice({ text: (error as Error).message, error: true }) }
  }

  return <section className="panel laundry-recipe-master" aria-labelledby="laundry-recipe-title">
    <header><div><h2 id="laundry-recipe-title">Master proses warna Laundry</h2><p>Atur instruksi untuk tiap pasangan laundry dan SKU.</p></div>
      {params.get('bagian') === 'laundry' && <a className="soft-btn" href="/produksi/laundry/"><ArrowLeft size={15}/>Kembali ke Laundry</a>}
    </header>
    <form onSubmit={save}>
      <div className="wh-fields">
        <label>Laundry untuk proses warna<select required value={draft.vendor} onChange={e => set({ vendor: e.target.value })}>
          <option value="">Pilih laundry</option>{laundryVendorNames.map(name => <option key={name}>{name}</option>)}
        </select></label>
        <label>SKU untuk proses warna<select required value={draft.sku} onChange={e => set({ sku: e.target.value })}>
          <option value="">Pilih SKU</option>{skus.map(sku => <option key={sku.key} value={sku.key}>{sku.key} · {sku.colour}</option>)}
        </select></label>
        <label>Berlaku mulai<input type="date" required max={lastWarehouseDay()} value={draft.from} onChange={e => set({ from: e.target.value })}/></label>
        <label>Proses warna master<input maxLength={120} placeholder="Contoh Celup ulang" value={draft.colourProcess} onChange={e => set({ colourProcess: e.target.value })}/></label>
        <label>Warna target master<input maxLength={120} placeholder="Contoh Biru muda" value={draft.colour} onChange={e => set({ colour: e.target.value })}/></label>
        <label>Layanan untuk estimasi<select value={draft.service} onChange={e => set({ service: e.target.value })}>
          <option value="">Belum ditentukan</option>{laundryProcesses.map(service => <option key={service}>{service}</option>)}
        </select></label>
      </div>
      <button className="primary-btn" type="submit">Simpan proses warna</button>
      {notice && <p role={notice.error ? 'alert' : 'status'}>{notice.text}</p>}
    </form>
    <section className="laundry-recipe-register" aria-label="Proses warna tersimpan">
      <label className="pocket-search">Cari pengaturan<input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Laundry atau SKU"/></label>
      {!visible.length && <p>Pengaturan belum ditemukan.</p>}
      {visible.map(row => <article key={[row.vendor,row.sku,row.from].join('|')}>
        <div><strong>{row.vendor} · {row.sku}</strong><small>{row.from} · {[row.colourProcess,row.colour,row.service].filter(Boolean).join(' · ')}</small></div>
        <button type="button" className="soft-btn" aria-label={'Edit proses ' + row.vendor + ' ' + row.sku + ' ' + row.from} onClick={() => set(row)}><Pencil size={15}/>Edit</button>
      </article>)}
    </section>
  </section>
}
