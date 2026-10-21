// @vitest-environment jsdom
import {act} from 'react'
import {createRoot, type Root} from 'react-dom/client'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import SalesReturnSettlementSection, {type SettlementSectionProps} from './SalesReturnSettlementSection'
import {blankChoice, commitIntent, parseSettlementQuote, type AccountOptionsQuery, type DraftChoice, type QuoteInput, type Source} from './salesReturnSettlementContract'

const id = (n: number) => `11111111-1111-4111-8111-${String(n).padStart(12, '0')}`
const hash = (n: number) => String(n).repeat(64)
const source: Source = {sale_id:id(1), sale_number:'INV-OW04', customer_id:id(2), customer_name:'Toko Sumber Rahasia', row_version:'9007199254740993', review_token:'a'.repeat(32)}
const draft = {return_number:'RET-OW04', physical_at:'2026-10-19T03:00:00.000Z', notes:null, change_reason:'Barang kembali telah diperiksa',
  items:[{allocation_id:id(3), location_id:id(6), qty_pcs:'1', quality_grade:'GRADE_A' as const, refund_amount:'200.00', notes:null}]}
const choice = (mode: DraftChoice['mode'] = 'CREDIT'): DraftChoice => ({mode, credit_account_id:id(4), cash_account_id:mode === 'REFUND' ? id(5) : null, refund_physical_at:mode === 'REFUND' ? '2026-10-19T17:01:00.000Z' : null, reference:null})
const input = (c = blankChoice()): QuoteInput => ({sale_id:source.sale_id, expected_version:source.row_version, review_token:source.review_token, return_payload:structuredClone(draft), settlement:structuredClone(c)})
const account = (kind:'CREDIT'|'CASH') => ({id:id(kind === 'CREDIT' ? 4 : 5), code:kind === 'CREDIT' ? '2109' : '1102', name:kind === 'CREDIT' ? 'Saldo kredit terpilih' : 'Bank pengembalian', facts_sha256:hash(5)})
function quoteFor(q: QuoteInput): any {
  const c = q.settlement, issues:string[] = []
  if (!c.mode) issues.push('CHOOSE_MODE')
  if (!c.credit_account_id) issues.push('CHOOSE_CREDIT_ACCOUNT')
  if (c.mode === 'REFUND' && !c.cash_account_id) issues.push('CHOOSE_REFUND_ACCOUNT')
  if (c.mode === 'REFUND' && !c.refund_physical_at) issues.push('ENTER_REFUND_TIME')
  const ready = !issues.length
  return {contract_version:'cp7.sales-return-settlement-quote.v1', kind:'QUOTE', read_only:true, business_DML:false, captured_at:'2026-10-20T01:00:00.000Z', input_echo:structuredClone(q), source:{...source},
    binding:{immutable_source_sha256:hash(1), current_state_sha256:hash(2), draft_sha256:hash(3), choice_sha256:hash(4), projection_sha256:hash(5), authority_sha256:hash(6), period_sha256:hash(7), dependency_sha256:hash(8), quote_sha256:ready ? hash(9) : null},
    has_recognition_effect:true, current_credit_amount:'200.00', components:[{component_key:hash(1), economic_date:'2026-10-19', book_date:'2026-10-19', signed_amount:'200.00', support_sha256:hash(2)}],
    return_projection:{economic_date:'2026-10-19', prior_causal:{contract_version:'ow04.prior-causal-book-proof.v1', scope:'PRIOR_CAUSAL_SALE_RETURN', state:'DATED', causal_book_floor:'2026-10-18', proof_sha256:hash(6)}, journal_effect:'JOURNAL_EXPECTED', planned_book_date:'2026-10-19', return_amount:'200.00', hpp_amount:'10.00', receivable_account_id:id(7)},
    totals:{before:{gross_total:'1000.00', return_total:'0.00', net_total:'1000.00', payments_received:'1000.00', credit_applied:'0.00', credit_recognized:'0.00', effective_paid:'1000.00', receivable_remaining:'0.00'},
      after:{gross_total:'1000.00', return_total:'200.00', net_total:'800.00', payments_received:'1000.00', credit_applied:'0.00', credit_recognized:'200.00', effective_paid:'800.00', receivable_remaining:'0.00'}},
    credit_account:c.credit_account_id ? {...account('CREDIT'), id:c.credit_account_id} : null,
    cash_account:c.cash_account_id ? {...account('CASH'), id:c.cash_account_id} : null,
    refund_projection:c.mode === 'REFUND' ? {amount:'200.00', physical_at:c.refund_physical_at, economic_date:c.refund_physical_at ? '2026-10-20' : null, book_date:c.refund_physical_at ? '2026-10-20' : null, safe_capacity:c.refund_physical_at ? '200.00' : null, capacity_sha256:c.refund_physical_at ? hash(7) : null} : null,
    capabilities:{record_return:true, recognize_credit:true, refund_cash:true}, readiness:{state:ready ? 'READY' : 'CHOICE_REQUIRED', issues}}
}
function zeroQuote(q: QuoteInput, journal: boolean): any {
  const w = quoteFor(q), z = {gross_total:'0.00', return_total:'0.00', net_total:'0.00', payments_received:'0.00', credit_applied:'0.00', credit_recognized:'0.00', effective_paid:'0.00', receivable_remaining:'0.00'}
  w.binding.quote_sha256 = hash(9); w.has_recognition_effect = false; w.current_credit_amount = '0.00'; w.components = []
  w.return_projection = {...w.return_projection, prior_causal:{...w.return_projection.prior_causal, state:'PROVEN_ABSENT', causal_book_floor:null}, journal_effect:journal ? 'JOURNAL_EXPECTED' : 'NO_JOURNAL', planned_book_date:journal ? '2026-10-19' : null, return_amount:'0.00', hpp_amount:journal ? '10.00' : '0.00', receivable_account_id:null}
  w.totals = {before:{...z}, after:{...z}}; w.readiness = {state:'READY', issues:[]}; return w
}
function historicalZero(q: QuoteInput): any {
  const w = quoteFor(q)
  w.current_credit_amount = '0.00'; w.components = [{component_key:hash(1), economic_date:'2026-10-19', book_date:'2026-10-19', signed_amount:'200.00', support_sha256:hash(3)}, {component_key:hash(2), economic_date:'2026-10-20', book_date:'2026-10-20', signed_amount:'-200.00', support_sha256:hash(4)}]
  w.totals.before = {...w.totals.before, payments_received:'0.00', effective_paid:'0.00', receivable_remaining:'1000.00'}
  w.totals.after = {...w.totals.after, payments_received:'0.00', credit_recognized:'0.00', effective_paid:'0.00', receivable_remaining:'800.00'}
  return w
}
function optionsFor(q: AccountOptionsQuery, count = 1): any {
  const all = Array.from({length:count}, (_, i) => count === 1 ? account(q.account_kind) : {id:id(100 + i), code:`21${String(i).padStart(2,'0')}`, name:`Akun halaman ${i + 1}`, facts_sha256:hash(5)})
  const rows = all.slice(q.offset, q.offset + 25), end = q.offset + rows.length
  return {contract_version:'cp7.sales-return-settlement-options.v1', kind:'ACCOUNT_OPTIONS', read_only:true, business_DML:false, captured_at:'2026-10-20T01:00:00.000Z', source:{...source}, account_kind:q.account_kind, q:q.q, rows, total:String(count), offset:q.offset, limit:25, next_offset:end < count ? end : null}
}
function deferred<T>() { let resolve!:(v:T)=>void, reject!:(e:unknown)=>void; const promise = new Promise<T>((a,b) => {resolve=a; reject=b}); return {promise, resolve, reject} }
type Ticket = {sequence:number}
let container:HTMLDivElement, root:Root, props:SettlementSectionProps<Ticket>, currentTicket:Ticket
const getQuote = vi.fn<(q:QuoteInput)=>Promise<unknown>>(), getAccountOptions = vi.fn<(q:AccountOptionsQuery)=>Promise<unknown>>()
const onIntent = vi.fn(), onInvalid = vi.fn(), onChoiceChange = vi.fn()
beforeEach(() => {
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true})
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
  getQuote.mockReset().mockImplementation(async q => quoteFor(q)); getAccountOptions.mockReset().mockImplementation(async q => optionsFor(q))
  onIntent.mockReset(); onInvalid.mockReset(); onChoiceChange.mockReset(); currentTicket = {sequence:1}
  props = {source:{...source}, input:input(), choice:blankChoice(), generation:1, parentReadTicket:currentTicket, isReadCurrent:t=>t === currentTicket, authorityScope:'actor-1/session-1/access-1', locked:false, stale:false, pendingEnvelope:false,
    getQuote, getAccountOptions, onInvalid, onIntent, onChoiceChange}
  onChoiceChange.mockImplementation((c:DraftChoice) => { props = {...props, choice:c, input:props.input ? {...props.input, settlement:structuredClone(c)} : null, generation:props.generation + 1}; root.render(<SalesReturnSettlementSection {...props}/> ) })
})
afterEach(async () => {await act(async () => root.unmount()); container.remove()})
const flush = async () => act(async () => {await new Promise(resolve => setTimeout(resolve,0))})
async function render(patch:Partial<typeof props> = {}) {props = {...props,...patch}; await act(async () => root.render(<SalesReturnSettlementSection {...props}/>)); await flush()}
const field = <T extends HTMLElement = HTMLInputElement>(label:string) => container.querySelector<T>(`[aria-label="${label}"]`)!
const button = (label:string) => [...container.querySelectorAll('button')].find(b => b.textContent === label)!
async function click(e:HTMLElement) {expect(e).toBeTruthy(); await act(async () => e.click()); await flush()}
const modeSelect = () => container.querySelector<HTMLSelectElement>('select[aria-label="Penyelesaian nilai retur"]')!
async function select(mode:string) {await act(async () => {const e = modeSelect(); e.value=mode; e.dispatchEvent(new Event('change',{bubbles:true}))}); await flush()}
async function fill(label:string, value:string) {await act(async () => {const e = field<HTMLInputElement>(label); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')!.set!.call(e,value); e.dispatchEvent(new Event('input',{bubbles:true}))}); await flush()}
async function quoted(c = choice()) {await render({choice:c, input:input(c)}); await click(button('Periksa penyelesaian retur'))}
const summary = () => field('Hasil pemeriksaan penyelesaian retur')
const review = () => field<HTMLInputElement>('Retur pelanggan sudah diperiksa')
const save = () => button('Catat retur dan penyelesaian')

describe('OW04 uninstalled controlled React settlement section, real jsdom events', () => {
  it('DOM01 begins with explicit blanks and no account fetch or invented amount', async () => {
    await render(); expect(modeSelect().value).toBe(''); expect(getAccountOptions).not.toHaveBeenCalled(); expect(getQuote).not.toHaveBeenCalled(); expect(summary()).toBeNull(); expect(save().disabled).toBe(true)
    await select('REFUND'); expect(field<HTMLInputElement>('Waktu pengembalian uang WIB').value).toBe(''); expect(field('Nominal pengembalian uang').textContent).toBe('Belum diperiksa')
    expect(props.choice).toEqual({...blankChoice(),mode:'REFUND'}); expect(getAccountOptions).not.toHaveBeenCalled(); expect(container.textContent).not.toContain('Rp0')
  })
  it('DOM02 cannot quote an incomplete draft or inconsistent controlled source/choice', async () => {
    await render({input:null}); expect(button('Periksa penyelesaian retur').disabled).toBe(true); await click(button('Periksa penyelesaian retur')); expect(getQuote).not.toHaveBeenCalled(); expect(container.textContent).toContain('Lengkapi barang')
    await render({input:input(choice()),choice:blankChoice()}); expect(button('Periksa penyelesaian retur').disabled).toBe(true)
    await render({input:input(), source:{...source,row_version:'9007199254740994'}}); expect(button('Periksa penyelesaian retur').disabled).toBe(true); expect(getQuote).not.toHaveBeenCalled()
  })
  it('DOM03 searches and pages actual credit choices without selecting the first account', async () => {
    getAccountOptions.mockImplementation(async q => optionsFor(q,26)); await render(); await select('CREDIT'); await fill('Cari akun saldo kredit pelanggan','saldo')
    await click(button('Cari akun saldo kredit pelanggan')); expect(getAccountOptions.mock.calls[0][0]).toEqual({kind:'ACCOUNT_OPTIONS',sale_id:source.sale_id,expected_version:source.row_version,review_token:source.review_token,account_kind:'CREDIT',q:'saldo',offset:0,limit:25})
    expect(container.querySelectorAll('[data-account-id]')).toHaveLength(25); expect(props.choice.credit_account_id).toBeNull(); expect(onChoiceChange).toHaveBeenCalledTimes(1); expect(container.textContent).not.toContain(id(100))
    await click(button('Akun saldo kredit pelanggan berikutnya')); expect(getAccountOptions.mock.calls[1][0].offset).toBe(25); expect(container.querySelectorAll('[data-account-id]')).toHaveLength(1)
    await click(button('2125 · Akun halaman 26')); expect(props.choice.credit_account_id).toBe(id(125)); expect(getQuote).not.toHaveBeenCalled(); expect(review().checked).toBe(false)
  })
  it('DOM04 retires facts and review before a deferred controlled-parent choice update', async () => {
    await quoted(); await click(review()); expect(save().disabled).toBe(false); onChoiceChange.mockImplementation(()=>{})
    await select('REFUND'); expect(onChoiceChange).toHaveBeenLastCalledWith({...choice(),mode:'REFUND',cash_account_id:null,refund_physical_at:null,reference:null})
    expect(summary()).toBeNull(); expect(review().checked).toBe(false); expect(save().disabled).toBe(true); expect(container.textContent).not.toContain(source.customer_name)
  })
  it.each(['CREDIT','CASH'] as const)('COUNTER_SAME_ACCOUNT_CHANGED_FACTS %s retires old eligibility even when the selected UUID is unchanged', async kind => {
    const c=kind==='CASH' ? choice('REFUND') : choice(), selected=kind==='CASH' ? c.cash_account_id : c.credit_account_id
    await quoted(c); await click(review()); expect(save().disabled).toBe(false)
    getAccountOptions.mockImplementation(async q=>{const w=optionsFor(q);w.rows[0].facts_sha256=hash(6);w.rows[0].name='Akun diperiksa ulang';return w})
    await click(button(kind==='CREDIT' ? 'Cari akun saldo kredit pelanggan' : 'Cari rekening pengembalian uang'))
    await click(button(`${kind==='CREDIT' ? '2109' : '1102'} · Akun diperiksa ulang`))
    expect(props.choice[kind==='CREDIT' ? 'credit_account_id' : 'cash_account_id']).toBe(selected)
    expect(summary()).toBeNull(); expect(review().checked).toBe(false); expect(save().disabled).toBe(true)
    await click(save()); expect(onIntent).not.toHaveBeenCalled()
    getQuote.mockImplementation(async q=>{const w=quoteFor(q);w[kind==='CREDIT' ? 'credit_account' : 'cash_account'].facts_sha256=hash(6);w.binding.quote_sha256=hash(8);return w})
    await click(button('Periksa penyelesaian retur')); expect(summary()).not.toBeNull(); expect(review().checked).toBe(false); expect(save().disabled).toBe(true)
    await click(review()); await click(save()); expect(onIntent).toHaveBeenCalledOnce(); expect(onIntent.mock.calls[0][0].document.quote_sha256).toBe(hash(8))
  })
  it('DOM05 requires final review and emits only the exact frozen CREDIT payload once', async () => {
    await quoted(); expect(save().disabled).toBe(true); await click(save()); expect(onIntent).not.toHaveBeenCalled(); await click(review()); expect(save().disabled).toBe(false)
    const q = parseSettlementQuote(quoteFor(props.input!),props.input!); expect(q.kind).toBe('QUOTE'); if(q.kind !== 'QUOTE') throw Error('fixture')
    const expected = commitIntent(q).payload
    await act(async () => {save().click(); save().click()}); await flush(); expect(onIntent).toHaveBeenCalledOnce(); expect(onIntent).toHaveBeenLastCalledWith(expected)
    expect(Object.keys(onIntent.mock.calls[0][0]).sort()).toEqual(['document','expected_version']); expect(onIntent.mock.calls[0][0].document.settlement).toEqual({mode:'CREDIT',credit_account_id:id(4)})
    for(const key of ['components','current_credit_amount','prior_causal','planned_book_date','request_id','projection_sha256']) expect(Object.hasOwn(onIntent.mock.calls[0][0].document,key)).toBe(false)
    expect(save().disabled).toBe(true); expect(summary()).toBeNull()
  })
  it('DOM06 selects real cash and independent explicit WIB time without an editable refund amount or book date', async () => {
    await render(); await select('REFUND'); expect(field<HTMLInputElement>('Waktu pengembalian uang WIB').value).toBe('')
    await click(button('Cari akun saldo kredit pelanggan')); await click(button('2109 · Saldo kredit terpilih')); await click(button('Cari rekening pengembalian uang')); await click(button('1102 · Bank pengembalian'))
    expect(props.choice.refund_physical_at).toBeNull(); await fill('Waktu pengembalian uang WIB','2026-10-20T00:01'); expect(props.choice.refund_physical_at).toBe('2026-10-19T17:01:00.000Z')
    await fill('Referensi pengembalian uang','BANK-RET-1'); await click(button('Periksa penyelesaian retur')); expect(field('Nominal pengembalian uang').textContent).toBe('Rp200'); expect(container.querySelector('input[inputmode="decimal"]')).toBeNull()
    expect(container.querySelectorAll('input[type="datetime-local"]')).toHaveLength(1); await click(review()); await click(save())
    expect(onIntent.mock.calls[0][0].document.settlement).toEqual({mode:'REFUND',credit_account_id:id(4),cash_account_id:id(5),refund_physical_at:'2026-10-19T17:01:00.000Z',reference:'BANK-RET-1'})
  })
  it('DOM05b names the exact chosen accounts and separate return/refund dates in the final review label', async () => {
    await quoted(choice('REFUND')); const label=review().parentElement!.textContent!
    expect(label).toContain('2109 · Saldo kredit terpilih'); expect(label).toContain('1102 · Bank pengembalian')
    expect(label).toContain('Tanggal retur 2026-10-19'); expect(label).toContain('buku retur 2026-10-19')
    expect(label).toContain('Tanggal pengembalian uang 2026-10-20'); expect(label).toContain('buku pengembalian 2026-10-20')
  })
  it.each([false,true])('DOM07/08 accepts prior ABSENT with projected journal=%s without invented floor or settlement', async journal => {
    const q=input(); q.return_payload.items[0].refund_amount='0.00'; getQuote.mockImplementation(async query=>zeroQuote(query,journal)); await render({input:q}); await click(button('Periksa penyelesaian retur'))
    expect(summary()).not.toBeNull(); expect(container.textContent).not.toContain('Batas tanggal buku sumber'); expect(container.querySelector('[aria-label="Akun saldo kredit pelanggan"]')).toBeNull()
    expect(container.querySelector('[data-return-book-date]')?.textContent ?? null).toBe(journal ? '2026-10-19' : null)
    if(!journal) expect(container.textContent).toContain('Retur fisik tanpa jurnal baru')
    await click(review()); await click(save()); expect(onIntent.mock.calls[0][0].document.settlement).toBeNull(); expect(onIntent.mock.calls[0][0].document.items[0].refund_amount).toBe('0.00')
  })
  it('DOM08b retains DATED prior proof for a current-HPP0 no-journal return', async () => {
    const q=input(); q.return_payload.items[0].refund_amount='0.00'; getQuote.mockImplementation(async query=>{const w=zeroQuote(query,false); w.return_projection.prior_causal={...w.return_projection.prior_causal,state:'DATED',causal_book_floor:'2026-10-20'}; return w})
    await render({input:q}); await click(button('Periksa penyelesaian retur')); expect(container.textContent).toContain('Batas tanggal buku sumber: 2026-10-20'); expect(container.querySelector('[data-return-book-date]')).toBeNull(); await click(review()); expect(save().disabled).toBe(false)
  })
  it('DOM09 keeps K0 historical recognition explicit and never treats negative adjustment as cash refund', async () => {
    getQuote.mockImplementation(async q=>historicalZero(q)); await quoted(); expect(container.textContent).toContain('Ada pengakuan kredit pada tanggal sebelumnya; hak kredit saat ini Rp0')
    expect(container.querySelectorAll('[data-signed-amount]')).toHaveLength(2); expect(container.textContent).toContain('Penyesuaian pengakuan kredit'); await click(review()); await click(save()); expect(onIntent.mock.calls[0][0].document.settlement).toEqual({mode:'CREDIT',credit_account_id:id(4)})
  })
  it('DOM10 displays unbounded exact signed values and P/U/I/E/AR separately', async () => {
    getQuote.mockImplementation(async q=>{const w=historicalZero(q); w.components=[{component_key:hash(1),economic_date:'2026-10-18',book_date:'2026-10-18',signed_amount:'999999999999999999.99',support_sha256:hash(4)},{component_key:hash(2),economic_date:'2026-10-19',book_date:'2026-10-19',signed_amount:'999999999999999999.99',support_sha256:hash(4)},{component_key:hash(3),economic_date:'2026-10-20',book_date:'2026-10-20',signed_amount:'-1999999999999999999.98',support_sha256:hash(4)}];return w})
    await quoted(); expect(container.querySelector('[data-signed-amount="-1999999999999999999.98"]')?.textContent).toBe('Rp-1.999.999.999.999.999.999,98')
    for(const label of ['Pembayaran diterima (P)','Saldo kredit dipakai (U)','Pengakuan kredit bersih (I)','Pelunasan efektif (E)','Piutang tersisa (AR)']) expect(container.textContent).toContain(label)
    expect(container.querySelectorAll('[data-total]')).toHaveLength(8); expect(container.querySelector('[data-total="payments_received"]')?.textContent).toBe('Pembayaran diterima (P)Rp0Rp0'); expect(container.textContent).toContain('2026-10-18')
  })
  it('DOM11 shows UNAVAILABLE as unknown, with no numeric0 or fallback intent', async () => {
    getQuote.mockImplementation(async q=>({contract_version:'cp7.sales-return-settlement-quote.v1',kind:'UNAVAILABLE',read_only:true,business_DML:false,captured_at:'2026-10-20T01:00:00.000Z',input_echo:q,source:{...source},reason:'SOURCE_INCOMPLETE'})); await render(); await click(button('Periksa penyelesaian retur'))
    expect(container.textContent).toContain('Nilai penyelesaian belum diketahui'); expect(summary()).toBeNull(); expect(container.textContent).not.toContain('Rp0'); expect(save().disabled).toBe(true); await click(save()); expect(onIntent).not.toHaveBeenCalled()
  })
  it.each(['PERIOD_CHANGED','DEPENDENCY_BLOCKED','REFUND_PERMISSION_REQUIRED','REFUND_ZERO_CURRENT_AMOUNT'] as const)('DOM12 refuses blocked %s without intent', async issue => {
    const c=issue.startsWith('REFUND') ? choice('REFUND') : choice(); getQuote.mockImplementation(async q=>{const w=issue==='REFUND_ZERO_CURRENT_AMOUNT' ? historicalZero(q) : quoteFor(q); w.binding.quote_sha256=null; w.readiness={state:'BLOCKED',issues:[issue]}; if(issue==='REFUND_PERMISSION_REQUIRED') w.capabilities.refund_cash=false; if(issue==='REFUND_ZERO_CURRENT_AMOUNT') w.refund_projection={...w.refund_projection,amount:'0.00',safe_capacity:'0.00'};return w})
    await quoted(c); expect(summary()).not.toBeNull(); expect(review().disabled).toBe(true); expect(save().disabled).toBe(true); await click(save()); expect(onIntent).not.toHaveBeenCalled()
  })
  it.each([401,403])('DOM13 retires financial and account facts on current HTTP%s without leaking raw error', async status => {
    await quoted(); await click(review()); const old=deferred<unknown>(); getAccountOptions.mockImplementation(()=>old.promise); await click(button('Cari akun saldo kredit pelanggan'))
    getQuote.mockRejectedValue({status,message:'PRIVATE SQL secret customer data'}); await click(button('Periksa penyelesaian retur')); expect(onInvalid).toHaveBeenCalledOnce(); expect(summary()).toBeNull(); expect(container.textContent).not.toContain(source.customer_name); expect(container.textContent).not.toContain('Saldo kredit terpilih'); expect(container.textContent).not.toContain('PRIVATE SQL')
    await act(async()=>old.resolve(optionsFor({kind:'ACCOUNT_OPTIONS',sale_id:source.sale_id,expected_version:source.row_version,review_token:source.review_token,account_kind:'CREDIT',q:'',offset:0,limit:25}))); await flush(); expect(container.querySelector('[data-account-id]')).toBeNull(); expect(save().disabled).toBe(true)
  })
  it('DOM13b retires an already reviewed quote when the current account read returns42501', async () => {
    await quoted(); await click(review()); getAccountOptions.mockRejectedValue({code:'42501',message:'PRIVATE forbidden bank'}); await click(button('Cari akun saldo kredit pelanggan')); expect(onInvalid).toHaveBeenCalledOnce(); expect(summary()).toBeNull(); expect(review().checked).toBe(false); expect(container.textContent).not.toContain('PRIVATE forbidden bank')
  })
  it('DOM14 discards old A→B→A replies and preserves the newer quoted result', async () => {
    const old=deferred<unknown>(), next=deferred<unknown>(); getQuote.mockImplementationOnce(()=>old.promise).mockImplementationOnce(()=>next.promise); const c=choice(), a=input(c)
    await render({choice:c,input:a}); await click(button('Periksa penyelesaian retur')); const b=structuredClone(a);b.return_payload.notes='Perubahan B'; await render({input:b,generation:2}); await render({input:structuredClone(a),generation:3}); await click(button('Periksa penyelesaian retur'))
    await act(async()=>old.resolve({...quoteFor(a),source:{...source,customer_name:'LATE PRIVATE A'}})); await flush(); expect(summary()).toBeNull(); expect(container.textContent).not.toContain('LATE PRIVATE A')
    await act(async()=>next.resolve(quoteFor(a))); await flush(); expect(summary()).not.toBeNull(); expect(review().checked).toBe(false); expect(container.textContent).not.toContain('LATE PRIVATE A')
  })
  it('DOM15 discards late account pages after a source ticket changes', async () => {
    const d=deferred<unknown>(); getAccountOptions.mockImplementation(()=>d.promise); await render({choice:choice(),input:input(choice())}); await click(button('Cari akun saldo kredit pelanggan')); const query=getAccountOptions.mock.calls[0][0]
    currentTicket={sequence:2}; await render({parentReadTicket:currentTicket}); await act(async()=>d.resolve(optionsFor(query))); await flush(); expect(container.querySelector('[data-account-id]')).toBeNull(); expect(onInvalid).not.toHaveBeenCalled(); expect(onChoiceChange).not.toHaveBeenCalled()
  })
  it('DOM15b checks the latest actual parent ticket at submit even without a rerender', async () => {
    await quoted(); await click(review()); expect(save().disabled).toBe(false); currentTicket={sequence:99}; await click(save()); expect(onIntent).not.toHaveBeenCalled(); expect(onInvalid).toHaveBeenCalledOnce(); expect(summary()).toBeNull(); expect(save().disabled).toBe(true)
  })
  it('DOM16 synchronously hides financial/source/account facts on authority transition and rejects its late page', async () => {
    await quoted(); await click(review()); const d=deferred<unknown>(); getAccountOptions.mockImplementation(()=>d.promise); await click(button('Cari akun saldo kredit pelanggan')); const query=getAccountOptions.mock.calls[0][0]
    await render({authorityScope:'actor-1/session-1/access-2'}); expect(summary()).toBeNull(); expect(container.textContent).not.toContain(source.customer_name); expect(container.textContent).not.toContain('Saldo kredit terpilih'); expect(review().checked).toBe(false)
    await act(async()=>d.resolve(optionsFor(query))); await flush(); expect(container.querySelector('[data-account-id]')).toBeNull(); expect(onIntent).not.toHaveBeenCalled()
  })
  it.each(['locked','stale','pendingEnvelope'] as const)('DOM17 retires and locks on %s, without restoring old review on unlock', async flag => {
    await quoted(); await click(review()); await render({[flag]:true}); expect(summary()).toBeNull(); expect(save().disabled).toBe(true); expect(button('Periksa penyelesaian retur').disabled).toBe(true)
    await select('REFUND'); expect(onChoiceChange).not.toHaveBeenCalled(); await render({[flag]:false}); expect(summary()).toBeNull(); expect(review().checked).toBe(false); expect(save().disabled).toBe(true)
  })
  it('DOM17b keeps the locally handed-off uncertain intent locked across later prop edits', async () => {
    await quoted(); await click(review()); await click(save()); expect(onIntent).toHaveBeenCalledOnce(); await render({pendingEnvelope:true}); await render({pendingEnvelope:false,generation:2,input:input(choice())}); await click(save()); await click(button('Periksa penyelesaian retur'))
    expect(onIntent).toHaveBeenCalledOnce(); expect(getQuote).toHaveBeenCalledTimes(1); expect(container.textContent).toContain('Selesaikan pemulihan permintaan'); expect(save().disabled).toBe(true)
  })
  it('DOM18 rejects a malformed current response without rendering private raw reply or falling back', async () => {
    getQuote.mockImplementation(async q=>({...quoteFor(q),private_debug:'SECRET journal rows'})); await render(); await click(button('Periksa penyelesaian retur')); expect(onInvalid).toHaveBeenCalledOnce(); expect(summary()).toBeNull(); expect(container.textContent).not.toContain('SECRET journal rows'); expect(save().disabled).toBe(true)
  })
})
