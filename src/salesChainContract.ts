import type {SalesRead} from './salesReadContract'

export type SalesChainSource={sale_id:string;number:string;status:string;row_version:string;review_token:string;payments:{id:string;number:string;physical_at:string;amount:string}[];returns:{id:string;number:string;physical_at:string;line_count:string}[];pending_children:{kind:'PAYMENT'|'RETURN';id:string;number:string}[]}
export type SalesChainWorkspace={contract_version:'cp7.sales-chain-workspace.v1';captured_at:string;source:SalesChainSource;chain_token:string;eligible:boolean}
export type SalesChainPayload={sale_id:string;review_token:string;chain_token:string;payment_ids:string[];return_ids:string[];change_reason:string}
type Step={action:'PAYMENT_REVERSE'|'RETURN_REVERSE'|'SALE_REVERSE';id:string;status:'REVERSED'}
const fail=():never=>{throw Error('Rantai penjualan berubah atau belum lengkap. Muat ulang invoice dan periksa semua dokumen terkait.')}
const id=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const token=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{32}$/.test(v)
const stamp=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v))
const text=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0
const count=(v:unknown):v is string=>typeof v==='string'&&/^(?:0|[1-9][0-9]*)$/.test(v)
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(Object.keys(r).length!==keys.length||keys.some(k=>!(k in r)))fail();return r}
function list(v:unknown,keys:string[],check:(r:Record<string,unknown>)=>boolean){if(!Array.isArray(v))return fail();const ids=new Set<string>();for(const value of v){const r=closed(value,keys),ident=r.id;if(!id(ident))return fail();if(ids.has(ident.toLowerCase())||!check(r))fail();ids.add(ident.toLowerCase())}return v}
export function parseSalesChainWorkspace(v:unknown,owning:NonNullable<SalesRead['detail']>):SalesChainWorkspace{
 const r=closed(v,['contract_version','captured_at','source','chain_token','eligible']),s=closed(r.source,['sale_id','number','status','row_version','review_token','payments','returns','pending_children'])
 if(r.contract_version!=='cp7.sales-chain-workspace.v1'||!stamp(r.captured_at)||!token(r.chain_token)||typeof r.eligible!=='boolean'||s.sale_id!==owning.id||s.number!==owning.number||s.status!==owning.status||s.row_version!==owning.row_version||s.review_token!==owning.review_token)fail()
 list(s.payments,['id','number','physical_at','amount'],p=>text(p.number)&&stamp(p.physical_at)&&typeof p.amount==='string'&&/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(p.amount)&&BigInt(p.amount.replace('.',''))>0n)
 list(s.returns,['id','number','physical_at','line_count'],p=>text(p.number)&&stamp(p.physical_at)&&count(p.line_count)&&p.line_count!=='0')
 const pending=list(s.pending_children,['kind','id','number'],p=>['PAYMENT','RETURN'].includes(String(p.kind))&&text(p.number))
 if(r.eligible!==(['POSTED','PARTIAL_PAID','PAID'].includes(String(s.status))&&pending.length===0))fail()
 return r as unknown as SalesChainWorkspace
}
export function salesChainPayload(w:SalesChainWorkspace,reason:string):SalesChainPayload{
 if(!w.eligible||reason.trim().length<5||reason.trim().length>1000)return fail()
 return {sale_id:w.source.sale_id,review_token:w.source.review_token,chain_token:w.chain_token,payment_ids:w.source.payments.map(p=>p.id),return_ids:w.source.returns.map(r=>r.id),change_reason:reason.trim()}
}
export function parseSalesChainOutcome(v:unknown,requestId:string,p:SalesChainPayload){
 const r=closed(v,['contract_version','kind','action','request_id','sale_id','status','row_version','steps'])
 if(r.contract_version!=='cp7.sales-chain-outcome.v1'||r.kind!=='COMMITTED_OUTCOME'||r.action!=='SALE_CHAIN_REVERSE'||r.request_id!==requestId||r.sale_id!==p.sale_id||r.status!=='REVERSED'||typeof r.row_version!=='string'||!/^[1-9][0-9]{0,18}$/.test(r.row_version))fail()
 const steps=r.steps;if(!Array.isArray(steps))return fail()
 const expected:Step[]=[...p.payment_ids.map(id=>({action:'PAYMENT_REVERSE' as const,id,status:'REVERSED' as const})),...p.return_ids.map(id=>({action:'RETURN_REVERSE' as const,id,status:'REVERSED' as const})),{action:'SALE_REVERSE',id:p.sale_id,status:'REVERSED'}]
 if(steps.length!==expected.length)fail()
 steps.forEach((v,i)=>{const s=closed(v,['action','id','status']);if(s.action!==expected[i].action||s.id!==expected[i].id||s.status!=='REVERSED')fail()})
 return r as unknown as {sale_id:string;row_version:string;steps:Step[]}
}
