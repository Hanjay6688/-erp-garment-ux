import { useId, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ArrowRight, Check, FilePenLine, FilePlus2, Files, FolderOpen, Plus, ReceiptText, Search, WalletCards } from 'lucide-react'
import { BrowsePane } from '../components/BrowsePane'
import { amountText } from './accessoryPricing'
import { supplierDateLabel } from './supplierInvoices'
import './payableInvoiceDesk.css'

export type DeskDraft = { id: string; number: string; day: string; count: number; amount: number }
export type DeskList = { drafts: DeskDraft[]; onEdit: (id: string) => void; onDetail: (id: string) => void; onNew: () => void }
type Step = 'sources' | 'invoice' | 'drafts'

// An operator can move between counterparties or reopen a saved invoice without losing work in another slot.
export function useInvoiceWork<T>(scope: string[], saved: unknown, initial: () => T) {
  const key = 'erp.demo.ap-work.v1:' + JSON.stringify(scope)
  const basis = JSON.stringify(saved ?? null)
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem(key) ?? 'null')
      if (stored?.basis === basis) return stored.value as T
    } catch { /* An unreadable browser draft can be started again. */ }
    return initial()
  })
  const change = (next: T) => {
    sessionStorage.setItem(key, JSON.stringify({ basis, value: next }))
    setValue(next)
  }
  return { value, change, clear: () => sessionStorage.removeItem(key) }
}

type DeskProps = DeskList & {
  party: string; editing?: string; sourceCount: number; chosen: number; sourceName: string; total: number;
  sources: ReactNode; sourceAction?: ReactNode; meta: ReactNode; lines: ReactNode; error: string;
  actions: ReactNode; review?: ReactNode; onReview: (event: FormEvent) => void;
  query: string; onSearch: (value: string) => void
}
export function PayableInvoiceDesk(props: DeskProps) {
  const [step, setStep] = useState<Step>(props.editing ? 'invoice' : 'sources')
  const title = useId()
  const nav = useRef<HTMLElement>(null)
  function chooseStep(next: Step) {
    setStep(next)
    if (nav.current?.offsetHeight) nav.current.scrollIntoView({ block: 'start' })
  }
  return <section className="ap-desk" aria-label={'Penyusun invoice ' + props.party} data-step={step}>
    <nav className="ap-desk-mobile" aria-label="Langkah susun invoice" ref={nav}>
      <button aria-pressed={step==='sources'} onClick={()=>chooseStep('sources')}><ReceiptText/> Kontrabon <b>{props.sourceCount}</b></button>
      <button aria-pressed={step==='invoice'} onClick={()=>chooseStep('invoice')}><FilePenLine/> Invoice ini <b>{props.chosen}</b></button>
      <button aria-pressed={step==='drafts'} onClick={()=>chooseStep('drafts')}><Files/> Draf <b>{props.drafts.length}</b></button>
    </nav>
    <div className="ap-desk-grid">
      <BrowsePane className="panel ap-source-pane" aria-label="Kontrabon belum masuk invoice">
        <header className="ap-desk-heading"><i><ReceiptText/></i><div><h2>Kontrabon tersedia</h2><p>{props.party}</p></div><span className="ap-count">{props.sourceCount} tersedia</span></header>
        <div className="ap-source-body"><label className="supplier-draft-search"><Search aria-hidden="true"/>
          <input type="search" value={props.query} onChange={event=>props.onSearch(event.target.value)} aria-label="Cari kontrabon tersedia" placeholder="Cari kontrabon, barang, atau jumlah…"/></label>
          <div className="ap-source-list">{props.sources}</div>{props.sourceAction}
          <button className="primary-btn ap-mobile-next" type="button" onClick={()=>chooseStep('invoice')}>Lihat invoice ini ({props.chosen}) <ArrowRight size={16}/></button></div>
      </BrowsePane>
      <div className="ap-desk-right">
        <form className="panel ap-builder" aria-labelledby={title} onSubmit={props.onReview}>
          <header className="ap-desk-heading"><i><FilePenLine/></i><div><h2 id={title}>{props.editing ? 'Edit draf invoice' : 'Susun invoice'}</h2><p>{props.party}</p></div>
            {props.editing && <button type="button" className="soft-btn" onClick={props.onNew}><Plus size={15}/> Invoice baru</button>}</header>
          <div className="ap-builder-body"><div className="demo-operation-fields ap-builder-meta">{props.meta}</div>
            <div className="ap-chosen-heading"><h3>Kontrabon di invoice ini</h3><small>{props.chosen} dipilih</small></div>
            <div className="ap-selected-list">{props.lines}</div>
            <button className="soft-btn ap-mobile-next" type="button" onClick={()=>chooseStep('sources')}><Plus size={15}/> Pilih kontrabon</button>
            {props.error && <p role="alert">{props.error}</p>}</div>
          <footer className="ap-builder-footer">
            <div className="ap-current-total"><span><WalletCards aria-hidden="true"/> Total invoice</span><strong>{amountText(props.total)}</strong></div>
            {props.review && <div className="ap-review" role="status"><Check size={16}/>{props.review}</div>}
            <div className="invoice-composer-actions">{props.actions}</div>
          </footer>
        </form>
        <section className="panel ap-drafts" aria-label="Semua draf invoice">
          <header className="ap-desk-heading"><i><Files/></i><div><h2>Semua draf invoice</h2><p>{props.party}</p></div><span className="ap-count">{props.drafts.length} draf</span></header>
          {props.drafts.length ? <ul>{[...props.drafts].sort((a,b)=>b.day.localeCompare(a.day)||a.number.localeCompare(b.number,'id',{numeric:true})).map(item=><li key={item.id}>
            <div><strong>{amountText(item.amount)}</strong><span>{item.number}</span><small>{supplierDateLabel(item.day)} · {item.count} {props.sourceName}</small></div>
            <div className="ap-draft-actions">
              <button type="button" className="soft-btn" aria-label={'Detail '+item.number} onClick={()=>props.onDetail(item.id)}><FolderOpen size={15}/> Detail</button>
              <button type="button" className="soft-btn invoice-add" aria-label={'Lanjutkan '+item.number} onClick={()=>{props.onEdit(item.id);chooseStep('invoice')}}><FilePenLine size={15}/> Lanjutkan</button>
            </div></li>)}</ul> : <p className="invoice-list-empty">Belum ada draf invoice untuk {props.party}.</p>}
          <button type="button" className="soft-btn ap-mobile-next" onClick={()=>{props.onNew();chooseStep('sources')}}><FilePlus2 size={16}/> Susun invoice baru</button>
        </section>
      </div>
    </div>
  </section>
}
