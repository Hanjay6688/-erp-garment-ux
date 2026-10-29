export type NoteCreditCarryReview={contract_version:'cp7.note-credit-carry-review.v1';basis_sha256:string;transfer_amount:string;replacement_net:string;remaining_amount:string}
export type NoteCreditCarryBasis={contract_version:'cp7.note-credit-carry-basis.v1';sale_id:string;root_sale_id:string;row_version:string;review_token:string;basis_sha256:string;transfer_amount:string;minimum_replacement_net:string;original_net:string;policy:'AUTO_TRANSFER_TO_REPLACEMENT';issues:string[];consumers:{event_id:string;amount:string;cohort_id:string;journal_id:string;historical_target_id:string;economic_date:string;transaction_date:string}[]}
const fail=():never=>{throw Error('Pemakaian kredit pada nota belum cocok. Muat ulang nota dan periksa lagi.')}
const id=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(v)
const amount=(v:unknown):v is string=>typeof v==='string'&&/^(0|[1-9][0-9]{0,30})\.[0-9]{2}$/.test(v)
const signed=(v:unknown):v is string=>typeof v==='string'&&/^-?(0|[1-9][0-9]{0,30})\.[0-9]{2}$/.test(v)&&v!=='-0.00'
export const noteCreditCents=(v:string):bigint=>{if(!signed(v))return fail();const negative=v.startsWith('-'),[whole,fraction]=(negative?v.slice(1):v).split('.');const cents=BigInt(whole)*100n+BigInt(fraction);return negative?-cents:cents}
export const noteCreditAmount=(v:bigint)=>{if(v<0n)return fail();return `${v/100n}.${String(v%100n).padStart(2,'0')}`}
function closed(v:unknown,keys:string[]){if(!v||typeof v!=='object'||Array.isArray(v))return fail();const r=v as Record<string,unknown>;if(Object.keys(r).length!==keys.length||keys.some(k=>!Object.hasOwn(r,k)))return fail();return r}
const day=(v:unknown):v is string=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v
export function parseNoteCreditCarryBasis(v:unknown,source:{id:string;row_version:string;review_token?:string}):NoteCreditCarryBasis{
 const r=closed(v,['contract_version','sale_id','root_sale_id','row_version','review_token','basis_sha256','transfer_amount','minimum_replacement_net','original_net','policy','issues','consumers'])
 if(r.contract_version!=='cp7.note-credit-carry-basis.v1'||r.sale_id!==source.id||!id(r.root_sale_id)||r.row_version!==source.row_version||r.review_token!==source.review_token||typeof r.basis_sha256!=='string'||!/^[a-f0-9]{64}$/.test(r.basis_sha256)||r.policy!=='AUTO_TRANSFER_TO_REPLACEMENT'||![r.transfer_amount,r.minimum_replacement_net,r.original_net].every(amount)||!Array.isArray(r.issues)||!Array.isArray(r.consumers))return fail()
 const issues=r.issues as unknown[],consumers=r.consumers as unknown[],allowed=['NEXT_NOTE_REVISION_ADAPTER_REQUIRED','NATIVE_PAYMENT_REPLAY_ADAPTER_REQUIRED','RETURN_FAMILY_NOTE_ADAPTER_REQUIRED','ZERO_INCOMING_NOTE_ADAPTER_REQUIRED','ORIGINAL_NOTE_BOOK_PAIR_ADAPTER_REQUIRED','NOTE_HPP_CLASS_ADAPTER_REQUIRED']
 if(issues.some(x=>typeof x!=='string'||!allowed.includes(x))||new Set(issues).size!==issues.length||noteCreditCents(String(r.minimum_replacement_net))<noteCreditCents(String(r.transfer_amount)))return fail()
 const ids=new Set<string>();let total=0n
 for(const value of consumers){const e=closed(value,['event_id','amount','cohort_id','journal_id','historical_target_id','economic_date','transaction_date'])
  if(![e.event_id,e.cohort_id,e.journal_id,e.historical_target_id].every(id)||ids.has(String(e.event_id))||!signed(e.amount)||noteCreditCents(e.amount)===0n||!day(e.economic_date)||!day(e.transaction_date)||e.transaction_date<e.economic_date)return fail()
  total+=noteCreditCents(e.amount);ids.add(String(e.event_id))
 }
 if(!consumers.length||total!==noteCreditCents(String(r.transfer_amount)))return fail()
 return r as unknown as NoteCreditCarryBasis
}
export function noteCreditCarryReview(basis:NoteCreditCarryBasis,newNet:string):NoteCreditCarryReview|null{
 if(!amount(newNet))return null
 const net=noteCreditCents(newNet),transfer=noteCreditCents(basis.transfer_amount)
 if(basis.issues.length||net<noteCreditCents(basis.minimum_replacement_net)||net<transfer)return null
 return {contract_version:'cp7.note-credit-carry-review.v1',basis_sha256:basis.basis_sha256,transfer_amount:basis.transfer_amount,replacement_net:newNet,remaining_amount:noteCreditAmount(net-transfer)}
}
