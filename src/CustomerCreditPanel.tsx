import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal} from './procurementContract'
import TransactionSourceLink from './TransactionSourceNavigation'
import type {useProductionMutation} from './useProductionMutation'
import {
  creditAmountInput,creditCents,creditNowInput,creditPhysicalInput,creditQuery,parseCreditPayload,parseCreditReview,parseCreditWorkspace,
  type CreditAction,type CreditCash,type CreditCohort,type CreditEvent,type CreditPageKind,type CreditPayload,
  type CreditRecovery,type CreditReview,type CreditSource,type CreditTarget,type CreditWorkspace,
} from './customerCreditContract'

type Fence=Pick<ReturnType<typeof useProductionMutation>,'currentReadTicket'|'isReadCurrent'>
type Props={source:CreditSource;locked:boolean;stale:boolean;pendingEnvelope:boolean;readFence:Fence;onClose:()=>void;onInvalid:(message:string)=>void;onIntent:(payload:CreditRecovery)=>void}
type Capture={scope:object;data:CreditWorkspace}
const kinds:CreditPageKind[]=['COHORTS','TARGETS','CASH','EVENTS']
const titles:Record<CreditPageKind,string>={COHORTS:'Saldo dari retur',TARGETS:'Invoice tujuan',CASH:'Rekening pengembalian',EVENTS:'Riwayat penggunaan kredit'}
const money=(value:string)=>`Rp${formatReceiptDecimal(value)}`

/** Parent alone persists UUIDs, sends writes and reconciles the saved envelope. */
export default function CustomerCreditPanel(props:Props) {
  const {runtime,identity}=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi saldo kredit belum siap.')
  const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime])
  const ticket=props.readFence.currentReadTicket()
  const authority=JSON.stringify([runtime.projectRef,identity.profile.authUserId,identity.profile.id,identity.profile.rowVersion,
    identity.profile.roleRowVersion,identity.permissions,props.source.id,props.source.row_version,props.source.review_token,
    props.locked,props.stale,props.pendingEnvelope])
  const scope=useMemo(()=>({}),[authority,ticket])
  const live=useRef({scope,props,ticket});live.current={scope,props,ticket}
  const mounted=useRef(false),requests=useRef({COHORTS:0,TARGETS:0,CASH:0,EVENTS:0,QUOTE:0}),generation=useRef(0),emitted=useRef(false)
  const [captures,setCaptures]=useState<Partial<Record<CreditPageKind,Capture>>>({})
  const [loading,setLoading]=useState<Partial<Record<CreditPageKind| 'QUOTE',boolean>>>({})
  const [problem,setProblem]=useState<{scope:object;message:string}|null>(null)
  const [action,setAction]=useState<CreditAction|''>('')
  const [cohort,setCohort]=useState<CreditCohort|null>(null),[target,setTarget]=useState<CreditTarget|null>(null),[cash,setCash]=useState<CreditCash|null>(null),[original,setOriginal]=useState<CreditEvent|null>(null)
  const [amount,setAmount]=useState(''),[at,setAt]=useState(''),[reason,setReason]=useState(''),[reference,setReference]=useState('')
  const [search,setSearch]=useState({TARGETS:'',CASH:''})
  const [quote,setQuote]=useState<{scope:object;generation:number;payload:CreditPayload;review:CreditReview}|null>(null)
  const quoteRef=useRef(quote);quoteRef.current=quote
  const [confirmed,setConfirmed]=useState(false)
  const [sent,setSent]=useState(false)
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;for(const k of [...kinds,'QUOTE']as const)++requests.current[k]}},[])
  useEffect(()=>{
    ++generation.current;for(const k of [...kinds,'QUOTE']as const)++requests.current[k]
    setCaptures({});setLoading({});setProblem(null);setQuote(null);setConfirmed(false)
    setCohort(null);setTarget(null);setCash(null);setOriginal(null)
    if(!props.pendingEnvelope&&!props.locked&&!props.stale&&ticket!==null&&props.readFence.isReadCurrent(ticket)){emitted.current=false;setSent(false)}
  },[scope])
  const current=(wanted=scope)=>{
    const s=live.current
    return mounted.current&&s.scope===wanted&&!s.props.locked&&!s.props.stale&&!s.props.pendingEnvelope
      &&!emitted.current&&s.ticket!==null&&s.props.readFence.isReadCurrent(s.ticket)
  }
  const retire=()=>{++generation.current;++requests.current.QUOTE;quoteRef.current=null;setQuote(null);setConfirmed(false)}
  const edit=(update:()=>void)=>{if(!current())return;retire();update()}
  const invalidate=(wanted:object,error:unknown)=>{
    if(!mounted.current||live.current.scope!==wanted)return
    retire();setCaptures({});setLoading({})
    for(const k of kinds)++requests.current[k]
    const message=normalizeClientError(error).message
    setProblem({scope:wanted,message});live.current.props.onInvalid(message)
  }
  const visible=<K extends CreditPageKind>(kind:K):CreditWorkspace<K>|null=>{
    const value=captures[kind]
    return current()&&value?.scope===scope?value.data as CreditWorkspace<K>:null
  }
  const load=async(kind:CreditPageKind,offset=0)=>{
    if(!current()||loading[kind])return
    const wanted=scope,request=++requests.current[kind],previous=visible(kind)
    const query=creditQuery(kind,props.source,kind==='TARGETS'||kind==='CASH'?search[kind].trim():'',offset,offset===0?null:previous?.dataset_sha256??null)
    retire();setCaptures(old=>({...old,[kind]:undefined}));setLoading(old=>({...old,[kind]:true}));setProblem(null)
    try {
      const r=await client.rpc('erp_cp7_get_customer_credit_workspace_v1',{p_query:query})
      if(!current(wanted)||requests.current[kind]!==request)return
      if(r.error)throw r.error
      const data=parseCreditWorkspace(r.data,query,props.source,identity.profile.authUserId)
      setCaptures(old=>({...old,[kind]:{scope:wanted,data}}))
    }catch(error){if(current(wanted)&&requests.current[kind]===request)invalidate(wanted,error)}
    finally{if(mounted.current&&live.current.scope===wanted&&requests.current[kind]===request)setLoading(old=>({...old,[kind]:false}))}
  }
  const positive=action==='APPLY'||action==='REFUND',exact=creditAmountInput(amount),physical=creditPhysicalInput(at)
  const anyLoading=Object.values(loading).some(Boolean),disabled=!current()||anyLoading
  const sourceRows=visible('COHORTS'),eventRows=visible('EVENTS'),targetRows=visible('TARGETS'),cashRows=visible('CASH')
  const caps=sourceRows?.capabilities??eventRows?.capabilities??targetRows?.capabilities??cashRows?.capabilities
  const cohortCurrent=cohort&&sourceRows?.page.rows.some(r=>r.id===cohort.id)
  const targetCurrent=target&&targetRows?.page.rows.some(r=>r.id===target.id&&r.row_version===target.row_version)
  const cashCurrent=cash&&cashRows?.page.rows.some(r=>r.id===cash.id)
  const originalCurrent=original&&eventRows?.page.rows.some(r=>r.id===original.id&&r.restores_event_id===null&&r.undone_by===null&&creditCents(r.amount)>0n)
  const allowed=action==='APPLY'?caps?.apply:action==='REFUND'?caps?.refund:action==='UNDO'&&original?(original.kind==='APPLY'?caps?.undo_apply:caps?.undo_refund):false
  const inputReady=Boolean(allowed&&physical&&reason.trim().length>=5&&reason.trim().length<=1000&&reference.trim().length<=100
    &&(positive?cohortCurrent&&exact&&(action==='APPLY'?targetCurrent&&creditCents(exact)<=creditCents(target!.open_balance):cashCurrent):action==='UNDO'&&originalCurrent))
  const makePayload=():CreditPayload=>parseCreditPayload({action,cohort_id:positive?cohort!.id:null,
    target_sale_id:action==='APPLY'?target!.id:null,cash_account_id:action==='REFUND'?cash!.id:null,
    restores_event_id:action==='UNDO'?original!.id:null,amount:positive?exact:null,physical_at:physical!,reason:reason.trim(),reference:reference.trim()||null})as CreditPayload
  const review=async()=>{
    if(disabled||!inputReady)return
    const wanted=scope,payload=makePayload(),g=++generation.current,request=++requests.current.QUOTE
    quoteRef.current=null;setQuote(null);setConfirmed(false);setProblem(null);setLoading(old=>({...old,QUOTE:true}))
    try {
      const r=await client.rpc('erp_cp7_get_customer_credit_review_v1',{p_payload:payload})
      if(!current(wanted)||requests.current.QUOTE!==request||generation.current!==g)return
      if(r.error)throw r.error
      const checked=parseCreditReview(r.data,payload,{source:props.source,original:original??undefined,target:target??undefined})
      setQuote({scope:wanted,generation:g,payload,review:checked})
    }catch(error){if(current(wanted)&&requests.current.QUOTE===request)invalidate(wanted,error)}
    finally{if(mounted.current&&live.current.scope===wanted&&requests.current.QUOTE===request)setLoading(old=>({...old,QUOTE:false}))}
  }
  const checked=current()&&quote?.scope===scope&&quote.generation===generation.current?quote:null
  const save=()=>{
    const value=quoteRef.current
    if(disabled||!confirmed||!value||value.scope!==scope||value.generation!==generation.current||!inputReady)return
    emitted.current=true;setSent(true);retire()
    props.onIntent({document:{...value.payload,quote_sha256:value.review.quote_sha256},review:value.review})
  }
  const pager=(kind:CreditPageKind)=>{
    const data=visible(kind)
    return data?<div className="cproc-pagination"><span>Total {data.page.total}</span>
      <button type="button" disabled={disabled||data.page.offset===0} onClick={()=>void load(kind,Math.max(0,data.page.offset-25))}>{titles[kind]} sebelumnya</button>
      <button type="button" disabled={disabled||data.page.next_offset===null} onClick={()=>void load(kind,data.page.next_offset!)}>{titles[kind]} berikutnya</button>
    </div>:null
  }
  return <section className="panel" aria-label="Saldo kredit pelanggan">
    <div className="cproc-heading"><div><h2>{current()?`Saldo kredit ${props.source.number}`:'Saldo kredit pelanggan'}</h2>{current()?<p>{props.source.customer_name}</p>:null}</div><button type="button" disabled={props.locked} onClick={props.onClose}>Tutup saldo kredit</button></div>
    {props.stale?<p role="alert">Invoice atau akses berubah. Muat ulang invoice dan periksa kembali pilihan saldo. Nominal, waktu, dan catatan tetap tersimpan di formulir ini.</p>:null}
    {props.pendingEnvelope||sent?<p role="status">Hasil kiriman sedang diperiksa. Gunakan pemulihan transaksi di halaman ini untuk memeriksa kiriman yang sama.</p>:null}
    {problem?.scope===scope?<p role="alert">{problem.message}</p>:null}
    <p>Pilih saldo dari retur yang tercatat. Pemakaian pada invoice lain mengurangi tagihan pelanggan yang sama; pengembalian uang memakai rekening yang dipilih.</p>
    <button type="button" disabled={disabled} onClick={()=>void load('COHORTS')}>Periksa saldo dari retur</button>
    <button type="button" disabled={disabled} onClick={()=>void load('EVENTS')}>Periksa riwayat kredit</button>
    {anyLoading?<p role="status">Memeriksa saldo dan sumber transaksi…</p>:null}
    {sourceRows?<section aria-label="Pilihan saldo retur"><h3>Saldo dari retur</h3>{sourceRows.page.rows.map(row=><button type="button" className="cproc-receipt" key={row.id} data-credit-cohort-id={row.id} aria-pressed={cohort?.id===row.id} disabled={disabled} onClick={()=>edit(()=>{setCohort(row);setOriginal(null);if(action==='UNDO')setAction('')})}>
    <span><strong>{row.return_number} · {money(row.available_credit)}</strong><small>{row.credit_account.code} · {row.credit_account.name}</small></span>
    </button>)}{sourceRows.page.total==='0'?<p>Invoice ini belum memiliki saldo dari retur.</p>:null}{pager('COHORTS')}</section>:null}
    {eventRows?<section aria-label="Riwayat kredit pelanggan"><h3>Riwayat kredit</h3>{eventRows.page.rows.map(row=><article className="cproc-item" key={row.id} data-credit-event-id={row.id}>
      <strong>{row.restores_event_id?'Pembatalan':row.kind==='APPLY'?'Pemakaian saldo':'Pengembalian uang'} · {money(row.amount)}</strong>
      <p>Retur {row.return_number} · {formatCp6WibDateTime(row.physical_at)}</p><p>Tanggal transaksi {row.economic_date} · tanggal buku {row.book_date}</p>
      {row.target_sale_id?<TransactionSourceLink sourceType="SALE" sourceId={row.target_sale_id} label={`Buka invoice tujuan ${row.target_number}`} disabled={disabled}/>:null}
      {row.cash_name?<p>Rekening {row.cash_name}</p>:null}
      {row.undone_by?<p>Sudah dibatalkan melalui transaksi pembalik yang tercatat.</p>:null}
      {creditCents(row.amount)>0n&&!row.undone_by&&(row.kind==='APPLY'?eventRows.capabilities.undo_apply:eventRows.capabilities.undo_refund)?<button type="button" disabled={disabled} onClick={()=>edit(()=>{setAction('UNDO');setOriginal(row);setCohort(null);setTarget(null);setCash(null)})}>Periksa pembatalan {row.kind==='APPLY'?'pemakaian saldo':'pengembalian uang'} {row.return_number}</button>:null}
    </article>)}{eventRows.page.total==='0'?<p>Belum ada penggunaan atau pengembalian uang dari saldo ini.</p>:null}{pager('EVENTS')}</section>:null}
    <fieldset className="cproc-fieldset" disabled={disabled}>
      <label>Tindakan saldo kredit<select aria-label="Tindakan saldo kredit" value={action} onChange={e=>edit(()=>{setAction(e.target.value as CreditAction|'');setOriginal(null);setTarget(null);setCash(null)})}>
        <option value="">Pilih tindakan</option>{caps?.apply?<option value="APPLY">Pakai untuk invoice lain</option>:null}{caps?.refund?<option value="REFUND">Kembalikan uang</option>:null}{action==='UNDO'?<option value="UNDO">Batalkan transaksi yang dipilih dari riwayat</option>:null}
      </select></label>
      {positive?<><p>Saldo terpilih: {cohortCurrent?`${cohort!.return_number} · ${money(cohort!.available_credit)}`:'pilih saldo dari hasil pemeriksaan.'}</p>
        <label>Nominal saldo kredit<input aria-label="Nominal saldo kredit" inputMode="decimal" value={amount} maxLength={20} onChange={e=>edit(()=>setAmount(e.target.value))}/></label></>:null}
      {action==='UNDO'&&originalCurrent?<p>Pembatalan penuh {money(original!.amount)} untuk {original!.kind==='APPLY'?'pemakaian saldo':'pengembalian uang'} dari retur {original!.return_number}. Nilai dan rekening mengikuti transaksi asli.</p>:null}
      {action==='APPLY'||action==='REFUND'?<section aria-label={action==='APPLY'?'Pilihan invoice tujuan':'Pilihan rekening pengembalian'}>
        <label>{action==='APPLY'?'Cari nomor invoice tujuan':'Cari rekening pengembalian'}<input aria-label={action==='APPLY'?'Cari invoice tujuan kredit':'Cari rekening kredit'} maxLength={120} value={search[action==='APPLY'?'TARGETS':'CASH']} onChange={e=>edit(()=>{
          const kind=action==='APPLY'?'TARGETS':'CASH';++requests.current[kind];setSearch(old=>({...old,[kind]:e.target.value}));setCaptures(old=>({...old,[kind]:undefined}));setTarget(null);setCash(null)
        })}/></label>
        <button type="button" onClick={()=>void load(action==='APPLY'?'TARGETS':'CASH')}>{action==='APPLY'?'Cari invoice tujuan kredit':'Cari rekening kredit'}</button>
        {action==='APPLY'&&targetRows?<>{targetRows.page.rows.map(row=><button type="button" className="cproc-receipt" key={row.id} data-credit-target-id={row.id} aria-pressed={target?.id===row.id} disabled={disabled||creditCents(row.open_balance)<=0n} onClick={()=>edit(()=>setTarget(row))}>{row.number} · sisa {money(row.open_balance)}</button>)}{targetRows.page.total==='0'?<p>Tidak ada invoice pelanggan ini sesuai pencarian.</p>:null}{pager('TARGETS')}</>:null}
        {action==='REFUND'&&cashRows?<>{cashRows.page.rows.map(row=><button type="button" className="cproc-receipt" key={row.id} data-credit-cash-id={row.id} aria-pressed={cash?.id===row.id} disabled={disabled} onClick={()=>edit(()=>setCash(row))}>{row.code} · {row.name}</button>)}{cashRows.page.total==='0'?<p>Tidak ada rekening yang memenuhi syarat sesuai pencarian.</p>:null}{pager('CASH')}</>:null}
        <p>{action==='APPLY'?`Invoice terpilih: ${targetCurrent?target!.number:'belum dipilih'}`:`Rekening terpilih: ${cashCurrent?cash!.name:'belum dipilih'}`}</p>
      </section>:null}
      <label>Waktu transaksi saldo kredit · WIB<input aria-label="Waktu transaksi saldo kredit WIB" type="datetime-local" step="0.001" value={at} onChange={e=>edit(()=>setAt(e.target.value))}/></label>
      <button type="button" onClick={()=>edit(()=>setAt(creditNowInput()))}>Gunakan waktu sekarang untuk transaksi kredit</button>
      <label>Alasan tindakan saldo kredit<input aria-label="Alasan tindakan saldo kredit" value={reason} maxLength={1000} onChange={e=>edit(()=>setReason(e.target.value))}/></label>
      <label>Referensi saldo kredit<input aria-label="Referensi saldo kredit" value={reference} maxLength={100} onChange={e=>edit(()=>setReference(e.target.value))}/></label>
      <button type="button" disabled={disabled||!inputReady} onClick={()=>void review()}>Periksa transaksi kredit</button>
    </fieldset>
    {checked?<section className="cproc-review" aria-label="Pemeriksaan transaksi kredit"><h3>Periksa sebelum menyimpan</h3>
      <p>{checked.review.selection.action==='UNDO'?'Pembatalan':checked.review.selection.event_kind==='APPLY'?'Pemakaian saldo':'Pengembalian uang'} {money(checked.review.selection.amount)}</p>
      <p>{formatCp6WibDateTime(checked.review.physical_at)} · tanggal transaksi {checked.review.economic_date} · tanggal buku {checked.review.transaction_date}</p>
      <p>Saldo sesudah transaksi ini: <strong>{money(checked.review.available_credit_after)}</strong></p>
      {targetCurrent?<p>Invoice tujuan {target!.number}</p>:null}{cashCurrent?<p>Rekening {cash!.name}</p>:null}
      <label className="cproc-check"><input type="checkbox" aria-label="Transaksi kredit sudah diperiksa" checked={confirmed} disabled={disabled} onChange={e=>setConfirmed(e.target.checked)}/>Nominal, sumber saldo, tujuan, dan waktu transaksi sudah saya periksa.</label>
      <button type="button" className="primary-btn" disabled={disabled||!confirmed||!inputReady} onClick={save}>Simpan transaksi kredit</button>
    </section>:null}
  </section>
}
