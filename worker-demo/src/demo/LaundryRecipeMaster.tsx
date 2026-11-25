import { BrowsePane } from '../components/BrowsePane'
import { useState, type FormEvent } from 'react'
import { ArrowLeft, Droplets, Link2, Pencil, Plus, Search, WashingMachine } from 'lucide-react'
import { browseMatch } from '../browseMatch'
import { laundryProcesses } from './laundryModel'
import { readLaundryColourMaster, removeLaundryColourDefault, saveLaundryColourLink, saveLaundryColourType, type LaundryColourLink, type LaundryColourType } from './laundryRecipes'
import { ReasonDialog } from './planner/ReasonDialog'
import { usePlannerSession } from './planner/session'
import { laundryVendorNames } from './sewingModel'
import { allSkus } from './skuCatalog'
import { fixtureDate } from './accessoryPricing'
import { lastWarehouseDay } from './warehouseDay'
import './warehouseForms.css'
import './laundryRecipe.css'

const displayDate = (date: string) => new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(date + 'T00:00:00Z'))

export default function LaundryRecipeMaster() {
  const skus = allSkus(usePlannerSession(), true)
  const params = new URLSearchParams(location.search)
  const [master, setMaster] = useState(readLaundryColourMaster)
  const [vendor, setVendor] = useState(() => laundryVendorNames.find(name => name === params.get('vendor')) ?? 'Laundry Intan')
  const [query, setQuery] = useState('')
  const [typeDraft, setTypeDraft] = useState<LaundryColourType | null>(null)
  const [linkDraft, setLinkDraft] = useState<LaundryColourLink | null>(null)
  const [previousLink, setPreviousLink] = useState<LaundryColourLink | null>(null)
  const [removeFrom, setRemoveFrom] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const types = master.types.filter(type => type.vendor === vendor)
  const visible = types.filter(type => browseMatch(query, type.name, type.note, ...master.links.filter(link => link.typeId === type.id).map(link => link.sku)))
  const vendorLinks = master.links.filter(link => link.vendor === vendor)
  const backLink = params.get('kembali') === 'laundry' ? '/produksi/laundry/' : '/master/supplier-vendor/'

  function openType(type?: LaundryColourType) {
    setTypeDraft(type ?? { id: '', vendor, name: '', note: '' })
    setError(''); setNotice('')
  }

  function openLink(type: LaundryColourType, existing?: LaundryColourLink) {
    const sku = skus.find(item => item.key === params.get('sku'))
    const date = params.get('tanggal') || fixtureDate
    const exact = vendorLinks.find(link => link.sku === sku?.key && link.typeId === type.id && link.from === date)
    setPreviousLink(existing ?? exact ?? null)
    setLinkDraft(existing ?? exact ?? { vendor, sku: sku?.key ?? '', from: date, typeId: type.id, colour: '', service: '' })
    setError(''); setNotice('')
  }

  function saveType(event: FormEvent) {
    event.preventDefault()
    if (!typeDraft) return
    try {
      const result = saveLaundryColourType(typeDraft)
      setMaster(result.master)
      setNotice(`${result.type.name} tersimpan di ${vendor}.`)
      setQuery(''); setTypeDraft(null)
    } catch (failure) { setError((failure as Error).message) }
  }

  function saveLink(event: FormEvent) {
    event.preventDefault()
    if (!linkDraft) return
    try {
      if (!skus.some(sku => sku.key === linkDraft.sku)) throw Error('Pilih SKU aktif.')
      setMaster(saveLaundryColourLink(linkDraft, previousLink?.typeId))
      setNotice(`Default ${linkDraft.sku} di ${vendor} disimpan.`)
      setLinkDraft(null); setPreviousLink(null)
    } catch (failure) { setError((failure as Error).message) }
  }

  function removeLink(event: FormEvent) {
    event.preventDefault()
    if (!previousLink || !removeFrom) return
    try {
      setMaster(removeLaundryColourDefault(previousLink, removeFrom))
      setNotice(`Default ${previousLink.sku} dilepas dari ${displayDate(removeFrom)}.`)
      setRemoveFrom(null); setLinkDraft(null); setPreviousLink(null)
    } catch (failure) { setError((failure as Error).message) }
  }

  return <div className="laundry-colour-master">
    <header className="hero-copy compact md-hero">
      <div><div className="eyebrow">MASTER DATA · SUPPLIER &amp; VENDOR</div><h1>Jenis pewarnaan laundry</h1><p>Kelola katalog setiap laundry dan atur default untuk SKU yang sering dikirim.</p></div>
      <a className="soft-btn colour-back" href={backLink}><ArrowLeft size={16} aria-hidden="true"/>{params.get('kembali') === 'laundry' ? 'Kembali ke Laundry' : 'Supplier & Vendor'}</a>
    </header>
    <section className="md-metrics colour-metrics" aria-label={'Ringkasan ' + vendor}>
      <article className="good"><Droplets aria-hidden="true"/><span>JENIS DI {vendor.toUpperCase()}</span><strong>{types.length} jenis</strong></article>
      <article><Link2 aria-hidden="true"/><span>DEFAULT SKU TERSIMPAN</span><strong>{new Set(vendorLinks.filter(link => link.typeId).map(link => link.sku)).size} SKU</strong></article>
    </section>
    <section className="panel md-workspace colour-workspace">
      <BrowsePane aria-label="Pilih laundry">
        <header><div><span>VENDOR LAUNDRY</span><strong>{laundryVendorNames.length} laundry</strong></div><WashingMachine aria-hidden="true"/></header>
        <div className="md-browser-list colour-vendors" aria-label="Laundry untuk proses warna">
          {laundryVendorNames.map(name => <button type="button" key={name} className={vendor === name ? 'active' : ''} aria-pressed={vendor === name}
            onClick={() => { setVendor(name); setQuery(''); setNotice('') }}><i><WashingMachine aria-hidden="true"/></i>
            <div><strong>{name}</strong><small>{master.types.filter(type => type.vendor === name).length} jenis pewarnaan</small></div>
          </button>)}
        </div>
      </BrowsePane>
      <div className="colour-catalogue">
        <header className="md-detail-head colour-catalogue-head"><div><span>KATALOG VENDOR</span><h2>{vendor}</h2><p>Pilih jenis ini langsung dari surat kirim.</p></div>
          <button type="button" className="primary-btn" onClick={() => openType()}><Plus aria-hidden="true"/>Tambah jenis</button></header>
        <div className="colour-catalogue-body">
          <label className="colour-search"><Search size={17} aria-hidden="true"/><input type="search" aria-label="Cari jenis pewarnaan atau SKU" placeholder="Cari jenis pewarnaan atau SKU…" value={query} onChange={e => setQuery(e.target.value)}/></label>
          {notice && <p className="wh-feedback" role="status">{notice}</p>}
          {!visible.length && <div className="md-empty"><Droplets aria-hidden="true"/><strong>{query ? 'Tidak ada hasil pencarian' : 'Belum ada jenis pewarnaan'}</strong><small>{query ? 'Cari dengan nama jenis atau SKU.' : 'Tambah jenis untuk laundry ini.'}</small></div>}
          <div className="colour-type-list">
            {visible.map(type => {
              const links = vendorLinks.filter(link => link.typeId === type.id).sort((a, b) => a.sku.localeCompare(b.sku) || b.from.localeCompare(a.from))
              return <article key={type.id} className="colour-type-card" aria-label={'Jenis ' + type.name}>
                <header><i><Droplets size={18} aria-hidden="true"/></i><div><h3>{type.name}</h3>{type.note && <p>{type.note}</p>}</div>
                  <button type="button" className="soft-btn colour-edit" aria-label={'Edit jenis ' + type.name} onClick={() => openType(type)}><Pencil size={15} aria-hidden="true"/> Edit</button></header>
                <div className="colour-links">
                  <div><span className="colour-link-caption"><Link2 size={15} aria-hidden="true"/>{new Set(links.map(link => link.sku)).size} SKU tertaut</span>
                    <button type="button" className="soft-btn" aria-label={'Tautkan SKU ke ' + type.name} onClick={() => openLink(type)}><Plus size={15} aria-hidden="true"/> Tautkan SKU</button></div>
                  {links.length > 0 && <ul aria-label={'Default SKU untuk ' + type.name}>{links.map(link => <li key={link.sku + link.from}>
                    <span><strong>{link.sku}</strong><small>{displayDate(link.from)}{link.colour ? ' · ' + link.colour : ''}
                      {vendorLinks.some(item => item.sku === link.sku && item.from > link.from) ? ' · Riwayat' : ' · Default terakhir'}</small></span>
                    <button type="button" className="soft-btn" aria-label={'Edit default ' + link.sku + ' mulai ' + link.from} onClick={() => openLink(type, link)}>Edit</button>
                  </li>)}</ul>}
                </div>
              </article>
            })}
          </div>
        </div>
      </div>
    </section>
    {typeDraft && <ReasonDialog title={typeDraft.id ? 'Edit jenis pewarnaan' : 'Tambah jenis pewarnaan'} onClose={() => setTypeDraft(null)} closeLabel="Tutup">
      <form className="colour-master-editor" onSubmit={saveType}>
        <p className="colour-editor-vendor"><WashingMachine size={17} aria-hidden="true"/> {vendor}</p>
        <div className="wh-fields">
          <label>Nama jenis pewarnaan<input required maxLength={100} placeholder="Contoh Tinting Indigo" value={typeDraft.name} onChange={e => setTypeDraft({ ...typeDraft, name: e.target.value })}/></label>
          <label>Catatan proses (opsional)<input maxLength={240} value={typeDraft.note} onChange={e => setTypeDraft({ ...typeDraft, note: e.target.value })}/></label>
        </div>
        {error && <p className="wh-feedback" role="alert">{error}</p>}
        <button type="submit" className="primary-btn">Simpan jenis pewarnaan</button>
      </form>
    </ReasonDialog>}
    {linkDraft && removeFrom === null && <ReasonDialog title={previousLink ? 'Edit default SKU' : 'Tautkan SKU'} onClose={() => { setLinkDraft(null); setPreviousLink(null) }} closeLabel="Tutup">
      <form className="colour-master-editor" onSubmit={saveLink}>
        <p className="colour-editor-vendor"><WashingMachine size={17} aria-hidden="true"/> {vendor} · {types.find(type => type.id === linkDraft.typeId)?.name}</p>
        <div className="wh-fields">
          <label>SKU<select required disabled={Boolean(previousLink)} value={linkDraft.sku} onChange={e => setLinkDraft({ ...linkDraft, sku: e.target.value })}>
            <option value="">Pilih SKU</option>{skus.map(sku => <option key={sku.key} value={sku.key}>{sku.key} · {sku.colour}</option>)}
          </select></label>
          <label>Berlaku mulai<input required disabled={Boolean(previousLink)} type="date" max={lastWarehouseDay()} value={linkDraft.from} onChange={e => setLinkDraft({ ...linkDraft, from: e.target.value })}/></label>
          {previousLink && <label>Jenis pewarnaan<select value={linkDraft.typeId} onChange={e => setLinkDraft({ ...linkDraft, typeId: e.target.value })}>
            {types.map(type => <option key={type.id} value={type.id}>{type.name}</option>)}
          </select></label>}
          <label>Warna target (opsional)<input maxLength={120} placeholder={skus.find(sku => sku.key === linkDraft.sku)?.colour || 'Mengikuti Master SKU'} value={linkDraft.colour} onChange={e => setLinkDraft({ ...linkDraft, colour: e.target.value })}/></label>
          <label>Layanan untuk estimasi (opsional)<select value={linkDraft.service} onChange={e => setLinkDraft({ ...linkDraft, service: e.target.value })}>
            <option value="">Belum ditentukan</option>{laundryProcesses.map(service => <option key={service}>{service}</option>)}
          </select></label>
        </div>
        <p>Default berlaku untuk SKU ini di {vendor} mulai tanggal yang dipilih.</p>
        {error && <p className="wh-feedback" role="alert">{error}</p>}
        <div className="colour-editor-actions"><button type="submit" className="primary-btn">Simpan tautan SKU</button>
          {previousLink && previousLink.from < lastWarehouseDay() && !vendorLinks.some(item => item.sku === previousLink.sku && item.from > previousLink.from) &&
            <button type="button" className="soft-btn" onClick={() => { setRemoveFrom(lastWarehouseDay()); setError('') }}>Lepas default SKU</button>}
        </div>
      </form>
    </ReasonDialog>}
    {previousLink && removeFrom !== null && <ReasonDialog title="Lepas default SKU" onClose={() => { setRemoveFrom(null); setError('') }} closeLabel="Kembali">
      <form className="colour-master-editor" onSubmit={removeLink}>
        <p>{previousLink.sku} · {vendor}. Surat baru mulai tanggal ini dapat memilih jenis dari katalog.</p>
        <div className="wh-fields"><label>Lepas mulai<input required type="date" min={previousLink.from} max={lastWarehouseDay()} value={removeFrom} onChange={e => setRemoveFrom(e.target.value)}/></label></div>
        {error && <p className="wh-feedback" role="alert">{error}</p>}
        <button type="submit" className="primary-btn">Konfirmasi lepas default</button>
      </form>
    </ReasonDialog>}
  </div>
}
