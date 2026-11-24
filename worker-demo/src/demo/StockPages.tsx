import RecordTable from '../RecordTable'
import { Icon } from '../components/AppIcon'
import { productCatalog } from '../productCatalog'
import { MultiCheckFilter } from './controls'
import { dozenPieces } from './format'
import type { QtyTuple } from './productionModel'
import {
  chronologicalMovements,
  initialMovements,
  movementProductKey,
  productBrands,
  productKey,
  productSizes,
  stockGrades,
  stockLocations,
} from './stockModel'
import type { Movement } from './stockModel'
import { Fragment, useMemo, useState } from 'react'

export function StockCard() {
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [skuQuery, setSkuQuery] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [selectedBrands, setSelectedBrands] = useState([...productBrands])
  const [selectedSizes, setSelectedSizes] = useState([...productSizes])
  const [selectedLocations, setSelectedLocations] = useState([...stockLocations])
  const [selectedGrades, setSelectedGrades] = useState([...stockGrades])
  const visibleSkus = useMemo(() => productCatalog.filter((product) => {
    const matchesQuery = `${product.brand} ${product.code} ${product.range} ${product.name} ${product.color}`.toLowerCase().includes(skuQuery.toLowerCase())
    const matchesSize = product.sizes.some((size) => selectedSizes.includes(size))
    return matchesQuery && selectedBrands.includes(product.brand) && matchesSize && selectedLocations.includes(product.location) && selectedGrades.includes(product.grade)
  }), [skuQuery, selectedBrands, selectedSizes, selectedLocations, selectedGrades])
  const selected = productCatalog.find((product) => productKey(product) === selectedKey)
  const currentStock = selected?.stocks.reduce((sum,qty)=>sum+qty,0) ?? 0
  const productMovements = selected ? initialMovements.filter((movement)=>movementProductKey(movement)===productKey(selected)) : []
  const ledgerMovements = selected ? productMovements.map((movement)=>({ ...movement, balance: movement.balance })) : []

  if (!selected) return <><section className="hero-copy compact"><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1></section><div className="panel sku-browser"><div className="stock-browser-toolbar"><div className="sku-search-field"><Icon name="search" /><input autoFocus value={skuQuery} onChange={(e)=>setSkuQuery(e.target.value)} placeholder="Cari merek dulu, lalu SKU / model / warna..." /></div><div className="stock-filter-row"><MultiCheckFilter label="Merek" options={productBrands} selected={selectedBrands} onChange={setSelectedBrands}/><MultiCheckFilter label="Size" options={productSizes} selected={selectedSizes} onChange={setSelectedSizes}/><MultiCheckFilter label="Lokasi" options={stockLocations} selected={selectedLocations} onChange={setSelectedLocations}/><MultiCheckFilter label="Grade" options={stockGrades} selected={selectedGrades} onChange={setSelectedGrades}/></div></div><div className="sku-browser-list">{visibleSkus.map((sku)=>{ const total=sku.stocks.reduce((s,q)=>s+q,0); const sequence=productCatalog.findIndex((row)=>productKey(row)===productKey(sku))+1; return <button className="sku-browser-row" key={productKey(sku)} onClick={()=>{setSelectedKey(productKey(sku));setExpandedId(null)}}><span className="sku-sequence">{String(sequence).padStart(2,'0')}</span><div className="sku-browser-name"><span className="brand-chip strong">{sku.brand}</span><strong>{sku.code}</strong><small>{sku.name} · {sku.color}</small></div><span className="range-chip">{sku.range}</span><div className="sku-size-preview">{sku.sizes.map((size,index)=><span key={size}><small>{size}</small><strong>{sku.stocks[index]}</strong><em>{dozenPieces(sku.stocks[index])}</em></span>)}</div><div className="sku-stock-preview"><strong>{total} pcs</strong><small>{dozenPieces(total)}</small></div><Icon name="arrow" /></button>})}</div></div></>

  return <><section className="hero-copy compact"><button className="back-link" onClick={()=>{setSelectedKey(null);setExpandedId(null)}}><Icon name="back" /> Semua SKU</button><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Kartu stok FG</h1></section><div className="panel stock-summary"><div className="stock-summary-main"><div><div className="sku-title"><span className="brand-chip strong">{selected.brand}</span><h2>{selected.code}</h2><span>Range {selected.range}</span></div><p>{selected.name} · {selected.color} · {selected.location}</p></div><div className="stock-size-overview">{selected.sizes.map((size,index)=><div key={size}><span>SIZE {size}</span><strong>{selected.stocks[index]} pcs</strong><small>{dozenPieces(selected.stocks[index])}</small></div>)}</div></div><div className="stock-total-hero"><span>TOTAL STOK AKHIR</span><strong>{currentStock} pcs</strong><small>{dozenPieces(currentStock)}</small></div></div><div className="panel table-panel"><div className="table-toolbar"><div className="search-box compact-search"><Icon name="search" /> Cari ref / pelanggan...</div><button className="soft-btn"><Icon name="calendar" /> 30 hari</button><button className="soft-btn"><Icon name="filter" /> Filter</button></div><div className="responsive-table stock-ledger"><RecordTable><thead><tr><th>Waktu fisik</th><th>Transaksi</th><th className="number-head">Masuk</th><th className="number-head">Keluar</th><th className="number-head">Stok akhir</th><th aria-label="Rincian" /></tr></thead><tbody>{ledgerMovements.map((movement)=>{ const masuk=movement.delta.reduce((s,q)=>s+Math.max(0,q),0); const keluar=movement.delta.reduce((s,q)=>s+Math.abs(Math.min(0,q)),0); const stock=movement.balance.reduce((s,q)=>s+q,0); const open=expandedId===movement.id; return <Fragment key={movement.id}><tr className={open?'stock-row-open':''}><td><span className="ledger-date">{movement.date}</span></td><td><div className="ledger-transaction"><div><strong>{movement.ref}</strong><span className="type-pill">{movement.type}</span></div><small>{movement.note}</small></div></td><td className="ledger-number incoming">{masuk>0?`+${masuk}`:'—'}<small>{masuk>0?dozenPieces(masuk):''}</small></td><td className="ledger-number outgoing">{keluar>0?`−${keluar}`:'—'}<small>{keluar>0?dozenPieces(keluar):''}</small></td><td className="ledger-balance"><strong>{stock} pcs</strong><small>{dozenPieces(stock)}</small></td><td><button className="stock-expand" onClick={()=>setExpandedId(open?null:movement.id)}>{open?'−':'+'}</button></td></tr>{open&&<tr className="stock-detail-row"><td colSpan={6}><div className="stock-size-details"><div className="detail-caption"><span>RINCIAN SIZE</span><small>Komposisi transaksi dan saldo sesudah transaksi</small></div>{movement.delta.map((delta,index)=><div className="size-ledger-card" key={index}><span>SIZE {selected.sizes[index]}</span><div><small>{delta>=0?'Masuk':'Keluar'}</small><strong className={delta<0?'neg':delta>0?'pos':''}>{delta>0?'+':delta<0?'−':''}{Math.abs(delta)} pcs</strong></div><div><small>Stok akhir</small><strong>{movement.balance[index]} pcs</strong></div><em>{dozenPieces(movement.balance[index])}</em></div>)}</div></td></tr>}</Fragment>})}</tbody></RecordTable></div></div></>
}

type MovementBookRowData = Movement & { before: QtyTuple; after: QtyTuple }

function MovementBookMetric({
  label,
  value,
  conversion,
  className,
  valueClass = '',
}: {
  label: string
  value: string
  conversion: string
  className: string
  valueClass?: string
}) {
  return <span className={className}>
    <small>{label}</small>
    <strong className={valueClass}>{value}</strong>
    <em>{conversion}</em>
  </span>
}

export function MovementBookRow({
  movement,
  index,
  rowCount,
  expanded,
  dragged,
  onToggle,
  onDragStart,
  onDrop,
  onDragEnd,
  onMove,
}: {
  movement: MovementBookRowData
  index: number
  rowCount: number
  expanded: boolean
  dragged: boolean
  onToggle: () => void
  onDragStart: () => void
  onDrop: () => void
  onDragEnd: () => void
  onMove: (direction: -1 | 1) => void
}) {
  const product = productCatalog.find((item) => productKey(item) === movementProductKey(movement))
  const sizes = product?.sizes ?? ['28', '29', '30']
  const movementTotal = movement.delta.reduce((sum, quantity) => sum + quantity, 0)
  const beforeTotal = movement.before.reduce((sum, quantity) => sum + quantity, 0)
  const afterTotal = movement.after.reduce((sum, quantity) => sum + quantity, 0)
  const changeClass = movementTotal < 0 ? 'neg' : movementTotal > 0 ? 'pos' : ''

  return <div
    className={`mutation-row mutation-collapsible ${expanded ? 'is-expanded' : ''} ${dragged ? 'is-dragging' : ''}`}
    draggable
    onDragStart={() => { onDragStart(); if (expanded) onToggle() }}
    onDragOver={(event) => event.preventDefault()}
    onDrop={onDrop}
    onDragEnd={onDragEnd}
  >
    <div className="drag-grip" title="Ubah urutan buku"><Icon name="drag" /></div>
    <div className="order-no">{String(index + 1).padStart(2, '0')}</div>
    <div className="compact-identity">
      <strong>{movement.brand}</strong>
      <b>{movement.sku}</b>
      <small>{product ? `${product.name} · ${product.color}` : 'Deskripsi barang'}</small>
    </div>
    <div className="compact-transaction">
      <span className="type-pill">{movement.type}</span>
      <strong>{movement.ref}</strong>
      <small>{movement.date}</small>
    </div>
    <div className="compact-book-summary">
      <MovementBookMetric label="Saldo awal" value={`${beforeTotal} pcs`} conversion={dozenPieces(beforeTotal)} className="summary-opening" />
      <MovementBookMetric label="Mutasi" value={`${movementTotal > 0 ? '+' : ''}${movementTotal} pcs`} conversion={dozenPieces(Math.abs(movementTotal))} className="summary-change" valueClass={changeClass} />
      <MovementBookMetric label="Saldo akhir" value={`${afterTotal} pcs`} conversion={dozenPieces(afterTotal)} className="summary-closing" />
    </div>
    <button
      type="button"
      className="compact-detail-toggle"
      aria-expanded={expanded}
      aria-label={expanded ? 'Tutup rincian mutasi' : 'Lihat rincian mutasi'}
      title={expanded ? 'Tutup rincian' : 'Lihat rincian'}
      onClick={onToggle}
    >{expanded ? '▴' : '▾'}</button>
    <div className="reorder">
      <button aria-label="Naikkan urutan" onClick={() => onMove(-1)} disabled={index === 0}><Icon name="up" /></button>
      <button aria-label="Turunkan urutan" onClick={() => onMove(1)} disabled={index === rowCount - 1}><Icon name="down" /></button>
    </div>
    {expanded && <div className="compact-details-grid">
      {movement.delta.map((delta, sizeIndex) => <span className="size-book-flow" key={sizes[sizeIndex]}>
        <small className="size-book-title">SIZE {sizes[sizeIndex]}</small>
        <div className="book-step opening"><label>Saldo awal</label><strong>{movement.before[sizeIndex]} pcs</strong><small>{dozenPieces(movement.before[sizeIndex])}</small></div>
        <div className="book-step change"><label>Mutasi</label><strong className={delta < 0 ? 'neg' : delta > 0 ? 'pos' : ''}>{delta > 0 ? '+' : ''}{delta} pcs</strong><small>{dozenPieces(Math.abs(delta))}</small></div>
        <div className="book-step closing"><label>Saldo akhir</label><strong>{movement.after[sizeIndex]} pcs</strong><small>{dozenPieces(movement.after[sizeIndex])}</small></div>
      </span>)}
      <div className="compact-total-card">
        <span className="total-book-title">TOTAL {movement.brand} · {movement.sku}</span>
        <div className="total-book-step"><label>Saldo awal</label><strong>{beforeTotal} pcs</strong><small>{dozenPieces(beforeTotal)}</small></div>
        <div className="total-book-step change"><label>Mutasi</label><strong className={changeClass}>{movementTotal > 0 ? '+' : ''}{movementTotal} pcs</strong><small>{dozenPieces(Math.abs(movementTotal))}</small></div>
        <div className="total-book-step closing"><label>Saldo akhir</label><strong>{afterTotal} pcs</strong><small>{dozenPieces(afterTotal)}</small></div>
      </div>
    </div>}
  </div>
}

export function Movements({ bookName, bookBrands, setBookBrands, movements, setMovements }: {
  bookName: string; bookBrands: string[]; setBookBrands: (brands: string[]) => void; movements: Movement[]; setMovements: (m: Movement[]) => void
}) {
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [expandedMovementId, setExpandedMovementId] = useState<string | null>(null)
  const [movementQuery, setMovementQuery] = useState('')
  const customerOptions = ['Nusantara Fashion','Sumber Denim','Maju Jaya','Tanpa toko']
  const movementTypes = Array.from(new Set(initialMovements.map((movement)=>movement.type)))
  const [selectedCustomers,setSelectedCustomers] = useState([...customerOptions])
  const [selectedTypes,setSelectedTypes] = useState([...movementTypes])

  const moveVisible = (id:string,dir:-1|1,visibleIds:string[]) => { const visibleIndex=visibleIds.indexOf(id); const targetId=visibleIds[visibleIndex+dir]; if(!targetId)return; const next=[...movements]; const from=next.findIndex((m)=>m.id===id); const to=next.findIndex((m)=>m.id===targetId); [next[from],next[to]]=[next[to],next[from]]; setMovements(next) }
  const dropOn = (targetId:string) => { if(!draggedId||draggedId===targetId)return; const from=movements.findIndex((m)=>m.id===draggedId); const to=movements.findIndex((m)=>m.id===targetId); if(from<0||to<0)return; const next=[...movements]; const [picked]=next.splice(from,1); next.splice(to,0,picked); setMovements(next); setDraggedId(null) }

  const finalByProduct = new Map<string, QtyTuple>()
  initialMovements.forEach((movement)=>{ const key=movementProductKey(movement); if(!finalByProduct.has(key)) finalByProduct.set(key,[...movement.balance] as QtyTuple) })
  const totalDeltaByProduct = new Map<string, QtyTuple>()
  movements.forEach((movement)=>{ const key=movementProductKey(movement); const current=totalDeltaByProduct.get(key)??movement.delta.map(() => 0); totalDeltaByProduct.set(key,current.map((qty,index)=>qty+movement.delta[index]) as QtyTuple) })
  const runningByProduct = new Map<string, QtyTuple>()
  finalByProduct.forEach((final,key)=>{ const delta=totalDeltaByProduct.get(key)??final.map(() => 0); runningByProduct.set(key,final.map((qty,index)=>qty-delta[index]) as QtyTuple) })
  const bookRows = movements.map((movement)=>{ const key=movementProductKey(movement); const before=[...(runningByProduct.get(key)??movement.delta.map(() => 0))] as QtyTuple; const after=before.map((qty,index)=>qty+movement.delta[index]) as QtyTuple; runningByProduct.set(key,after); return {...movement,before,after} })
  const visibleRows = bookRows.filter((movement)=>{ const customer=movement.customer??'Tanpa toko'; const product=productCatalog.find((item)=>productKey(item)===movementProductKey(movement)); const matchesQuery=`${movement.brand} ${movement.sku} ${product?.name??''} ${product?.color??''} ${movement.ref} ${movement.note} ${customer}`.toLowerCase().includes(movementQuery.toLowerCase()); return bookBrands.includes(movement.brand)&&matchesQuery&&selectedCustomers.includes(customer)&&selectedTypes.includes(movement.type) })
  const visibleIds=visibleRows.map((movement)=>movement.id)

  return <>
    <section className="hero-copy compact brand-book-hero"><div><div className="eyebrow">GUDANG · BUKU MUTASI FG</div><h1>Buku {bookName}</h1><p>Halaman ini mengikuti buku fisik. Merek yang masuk ke buku bisa diatur tanpa mengubah fakta transaksi.</p></div><div className="book-brand-control"><span>MEREK DALAM BUKU</span><MultiCheckFilter label="Atur merek" options={productBrands} selected={bookBrands} onChange={setBookBrands}/></div></section>
    <div className="panel mutation-panel"><div className="table-toolbar mutation-toolbar"><div className="catalog-search compact-search"><Icon name="search" /><input value={movementQuery} onChange={(e)=>setMovementQuery(e.target.value)} placeholder="Cari merek, SKU, deskripsi, ref, toko..." /></div><MultiCheckFilter label="Toko" options={customerOptions} selected={selectedCustomers} onChange={setSelectedCustomers}/><MultiCheckFilter label="Jenis" options={movementTypes} selected={selectedTypes} onChange={setSelectedTypes}/><button className="soft-btn" onClick={()=>setMovements(chronologicalMovements)}><Icon name="reset" /> Reset urutan</button></div>
      <div className="mutation-list">
        {visibleRows.map((movement, index) => <MovementBookRow
          key={movement.id}
          movement={movement}
          index={index}
          rowCount={visibleRows.length}
          expanded={expandedMovementId === movement.id}
          dragged={draggedId === movement.id}
          onToggle={() => setExpandedMovementId((current) => current === movement.id ? null : movement.id)}
          onDragStart={() => setDraggedId(movement.id)}
          onDrop={() => dropOn(movement.id)}
          onDragEnd={() => setDraggedId(null)}
          onMove={(direction) => moveVisible(movement.id, direction, visibleIds)}
        />)}
        {visibleRows.length === 0 && <div className="catalog-empty"><Icon name="filter" /><strong>Tidak ada mutasi di buku {bookName}</strong><small>Cek merek yang dipilih atau ubah filter.</small></div>}
      </div>
    </div>
  </>
}
