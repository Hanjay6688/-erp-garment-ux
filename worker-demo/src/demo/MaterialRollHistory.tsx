import { useId, useMemo, useState } from 'react'
import { ArrowDownLeft, ArrowUpRight, FileText, History, ListFilter, Search, SlidersHorizontal } from 'lucide-react'
import { browseMatch } from '../browseMatch'
import { rollLength, type WarehouseRoll } from './materialRollHistory'
import './materialRollHistory.css'

const dateFormat = new Intl.DateTimeFormat('id-ID', { timeZone: 'Asia/Jakarta', day: 'numeric', month: 'short', year: 'numeric' })
const timeFormat = new Intl.DateTimeFormat('id-ID', { timeZone: 'Asia/Jakarta', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
function instant(at: string) {
  return Date.parse(at.length === 10 ? at + 'T00:00:00+07:00' : at)
}
const filters = ['Semua', 'Masuk', 'Keluar'] as const
const pageSize = 12

export default function MaterialRollHistory({ material, rolls, initialRoll = '' }: { material: string; rolls: WarehouseRoll[]; initialRoll?: string }) {
  const heading = useId()
  const [direction, setDirection] = useState<typeof filters[number]>('Semua')
  const [query, setQuery] = useState(initialRoll)
  const [limit, setLimit] = useState(pageSize)
  const movements = useMemo(() => rolls.flatMap(roll => roll.events.map(event => ({ roll, event, time: instant(event.at) })))
    .reverse().sort((a, b) => (Number.isFinite(b.time) ? b.time : 0) - (Number.isFinite(a.time) ? a.time : 0)), [rolls])
  const matches = movements.filter(({ roll, event }) =>
    (direction === 'Semua' || (direction === 'Masuk' ? event.delta > 0 : event.delta < 0))
    && browseMatch(query, roll.id, roll.label, roll.supplier, event.title, event.ref, event.note, event.at,
      rollLength(Math.abs(event.delta), roll.unit), event.delta))

  return <section className="material-history" aria-labelledby={heading} id="riwayat-bahan">
    <header className="material-history-title"><i><History aria-hidden="true"/></i>
      <div><h3 id={heading}>Riwayat roll · {material}</h3><p>Masuk dan keluar dari semua roll bahan ini.</p></div>
    </header>
    <div className="material-history-tools">
      <div className="material-direction" role="group" aria-label="Arah mutasi">
        {filters.map(value => <button key={value} type="button" aria-pressed={value === direction}
          onClick={() => { setDirection(value); setLimit(pageSize) }}>{value}</button>)}
      </div>
      <label className="wh-search"><Search aria-hidden="true"/><input type="search" aria-label="Cari dalam riwayat bahan"
        placeholder="Cari roll, dokumen, atau panjang…" value={query} onChange={e => { setQuery(e.target.value); setLimit(pageSize) }}/></label>
    </div>
    {matches.length > 0 ? <>
      <div className="material-history-caption"><span>{Math.min(limit, matches.length)} dari {matches.length} mutasi</span><span>Terbaru dahulu</span></div>
      <ul className="material-history-list">
        {matches.slice(0, limit).map(({ roll, event, time }) => {
          const incoming = event.delta > 0, outgoing = event.delta < 0
          const Glyph = incoming ? ArrowDownLeft : outgoing ? ArrowUpRight : SlidersHorizontal
          const content = <>
            <div className={'movement-amount ' + (incoming ? 'incoming' : outgoing ? 'outgoing' : 'correction')}>
              <span><Glyph size={15} aria-hidden="true"/>{incoming ? 'Masuk' : outgoing ? 'Keluar' : 'Koreksi'}</span>
              <strong>{incoming ? '+' : outgoing ? '−' : ''}{rollLength(Math.abs(event.delta), roll.unit)}</strong>
            </div>
            <div className="material-history-identity"><strong>{event.title}</strong>
              <span><b>{roll.label}</b> · {event.ref}</span>{event.note && <small>{event.note}</small>}</div>
            <div className="material-history-source">{Number.isFinite(time)
              ? <time dateTime={event.at}>{dateFormat.format(time)}{event.at.length > 10 ? ' · ' + timeFormat.format(time) : ''}</time>
              : <small>Tanggal belum tercatat</small>}
              {event.source && <span className="movement-open"><FileText size={15} aria-hidden="true"/>{event.source.label}</span>}
            </div>
          </>
          return <li key={roll.id+'/'+event.id}>{event.source
            ? <a className="movement-row" href={event.source.href} aria-label={[event.source.label,event.ref,roll.label].join(' · ')}>{content}</a>
            : <div className="movement-row">{content}</div>}</li>
        })}
      </ul>
      {limit < matches.length && <button type="button" className="soft-btn material-history-more"
        onClick={() => setLimit(current => current + pageSize)}>Lihat {Math.min(pageSize, matches.length - limit)} mutasi berikutnya</button>}
    </> : <div className="material-history-empty"><ListFilter aria-hidden="true"/>
      <strong>{movements.length ? 'Tidak ada mutasi yang cocok.' : 'Belum ada mutasi roll untuk bahan ini.'}</strong>
      {movements.length > 0 && <button type="button" className="soft-btn" onClick={() => { setDirection('Semua'); setQuery(''); setLimit(pageSize) }}>Tampilkan semua mutasi</button>}
    </div>}
  </section>
}
