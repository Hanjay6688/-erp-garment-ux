import {financeDate} from './financeReportContract'
export type JournalDates={from:string;to:string;q:string}
export type JournalHeader={id:string;number:string;source_type:string;source_id:string|null;status:'POSTED'|'REVERSED';reversal_of_id:string|null;description:string;economic_date:string;transaction_date:string;posting_at:string;period_shifted:boolean;line_count:string;debit:string;credit:string;balanced:boolean}
export type JournalLine={id:string;account_id:string;account_code:string;account_name:string;description:string|null;debit:string;credit:string;customer_id:string|null;vendor_id:string|null;contractor_id:string|null;po_id:string|null;product_id:string|null}
export type JournalRead={contract_version:'cp7.journal-read.v1';captured_at:string;knowledge_basis:'CURRENT_RECORDED_KNOWLEDGE';historical_knowledge:'NOT_RECONSTRUCTED';basis:JournalDates&{scope:'POSTED_AND_REVERSED_JOURNALS_BY_ACCOUNTING_DATE'};totals:{journal_count:string;line_count:string;debit:string;credit:string;unbalanced_journal_count:string};page:{rows:JournalHeader[];total:string;offset:number;limit:25;next_offset:number|null};detail:(JournalHeader&{lines:JournalLine[]})|null}
const fail=():never=>{throw Error('Sumber jurnal belum lengkap atau pilihannya berubah. Muat ulang jurnal.')}
const text=(v:unknown):v is string=>typeof v==='string'
const uuid=(v:unknown):v is string=>text(v)&&/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(v)
const whole=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,20})$/.test(v)
const decimal=(v:unknown):v is string=>text(v)&&/^(0|[1-9][0-9]{0,40})(\.[0-9]{1,2})?$/.test(v)
const cents=(v:unknown)=>{if(!decimal(v))return fail();const [a,b='']=v.split('.');return BigInt(a)*100n+BigInt(b.padEnd(2,'0'))}
const timestamp=(v:unknown)=>text(v)&&/^\d{4}-\d{2}-\d{2}T/.test(v)&&Number.isFinite(Date.parse(v))
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const x=v as Record<string,unknown>;if(keys.some(k=>!(k in x))||Object.keys(x).some(k=>!keys.includes(k)))fail();return x}
const headerKeys=['id','number','source_type','source_id','status','reversal_of_id','description','economic_date','transaction_date','posting_at','period_shifted','line_count','debit','credit','balanced']
function header(v:unknown,dates:JournalDates,detail=false){
 const h=closed(v,[...headerKeys,...(detail?['lines']:[])])
 if(!uuid(h.id)||![h.number,h.source_type,h.description].every(text)||h.source_id!==null&&!uuid(h.source_id)||h.reversal_of_id!==null&&!uuid(h.reversal_of_id)||!['POSTED','REVERSED'].includes(String(h.status))||!financeDate(h.economic_date)||!financeDate(h.transaction_date)||String(h.transaction_date)<dates.from||String(h.transaction_date)>dates.to||!timestamp(h.posting_at)||h.period_shifted!==(h.economic_date!==h.transaction_date)||!whole(h.line_count)||!decimal(h.debit)||!decimal(h.credit)||h.balanced!==(BigInt(String(h.line_count))>0n&&cents(h.debit)===cents(h.credit)))fail()
 return h
}
export function parseJournalRead(value:unknown,dates:JournalDates,offset=0,selected:string|null=null):JournalRead{
 if(![dates.from,dates.to].every(financeDate)||dates.from>dates.to)return fail()
 const r=closed(value,['contract_version','captured_at','knowledge_basis','historical_knowledge','basis','totals','page','detail'])
 if(r.contract_version!=='cp7.journal-read.v1'||!timestamp(r.captured_at)||r.knowledge_basis!=='CURRENT_RECORDED_KNOWLEDGE'||r.historical_knowledge!=='NOT_RECONSTRUCTED')fail()
 const basis=closed(r.basis,['from','to','q','scope']);if(basis.from!==dates.from||basis.to!==dates.to||basis.q!==dates.q||basis.scope!=='POSTED_AND_REVERSED_JOURNALS_BY_ACCOUNTING_DATE')fail()
 const totals=closed(r.totals,['journal_count','line_count','debit','credit','unbalanced_journal_count'])
 if(![totals.journal_count,totals.line_count,totals.unbalanced_journal_count].every(whole)||!decimal(totals.debit)||!decimal(totals.credit)||BigInt(String(totals.unbalanced_journal_count))>BigInt(String(totals.journal_count))||totals.unbalanced_journal_count==='0'&&cents(totals.debit)!==cents(totals.credit))fail()
 const p=closed(r.page,['rows','total','offset','limit','next_offset']);if(!Array.isArray(p.rows)||!whole(p.total)||p.total!==totals.journal_count||p.offset!==offset||p.limit!==25||p.rows.length>25)return fail()
 const end=BigInt(offset+p.rows.length),total=BigInt(p.total);if(p.rows.length&&end>total||end<total&&(!p.rows.length||p.next_offset!==Number(end))||end>=total&&p.next_offset!==null)fail()
 const ids=new Set();let debits=0n,credits=0n,lines=0n,bad=0n
 for(const row of p.rows){const h=header(row,dates);if(ids.has(h.id))fail();ids.add(h.id);debits+=cents(h.debit);credits+=cents(h.credit);lines+=BigInt(String(h.line_count));if(!h.balanced)++bad}
 if(debits>cents(totals.debit)||credits>cents(totals.credit)||lines>BigInt(String(totals.line_count))||bad>BigInt(String(totals.unbalanced_journal_count)))fail()
 if(offset===0&&end===total&&(debits!==cents(totals.debit)||credits!==cents(totals.credit)||lines!==BigInt(String(totals.line_count))||bad!==BigInt(String(totals.unbalanced_journal_count))))fail()
 if(selected===null){if(r.detail!==null)fail()}else{
  const h=header(r.detail,dates,true);if(h.id!==selected||!Array.isArray(h.lines)||h.lines.length>250||BigInt(h.lines.length)!==BigInt(String(h.line_count)))return fail()
  const seen=new Set();let d=0n,c=0n
  for(const row of h.lines){const l=closed(row,['id','account_id','account_code','account_name','description','debit','credit','customer_id','vendor_id','contractor_id','po_id','product_id']);if(!uuid(l.id)||seen.has(l.id)||!uuid(l.account_id)||![l.account_code,l.account_name].every(text)||l.description!==null&&!text(l.description)||['customer_id','vendor_id','contractor_id','po_id','product_id'].some(k=>l[k]!==null&&!uuid(l[k]))||!decimal(l.debit)||!decimal(l.credit)||!((cents(l.debit)>0n&&cents(l.credit)===0n)||(cents(l.credit)>0n&&cents(l.debit)===0n)))fail();seen.add(l.id);d+=cents(l.debit);c+=cents(l.credit)}
  if(d!==cents(h.debit)||c!==cents(h.credit))fail()
  const listed=p.rows.find(v=>(v as JournalHeader).id===selected) as JournalHeader|undefined;if(listed&&headerKeys.some(k=>h[k]!==listed[k as keyof JournalHeader]))fail()
 }
 return r as unknown as JournalRead
}
