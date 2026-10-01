import { skuObject } from './skuHpp'
export type SupplierCredit = { return_id: string; return_number: string; supplier_id: string; source_purchase_id: string; purchase_number: string;
 credit: string; original_purchase_credit: string; version: string; allocations: { purchase_id: string; amount: string }[];
 events: { id: string; purchase_id: string; amount: string; date: string; reason: string; reversal_of: string | null; journal_id: string }[] }
export type SupplierCreditWorkspace = { supplier_id: string | null; page: number; total: number; can_manage: boolean;
 suppliers: { id: string; code: string; name: string }[]; credits: SupplierCredit[];
 purchases: { id: string; number: string; date: string; final_ap: string; paid: string; remaining: string; credit_delta: string; payment_status: string }[] }
export function creditCents(value: string): bigint | null {
 const v=value.trim();if(!/^\d{1,18}(\.\d{1,2})?$/.test(v))return null
 const [whole,fraction='']=v.split('.');return BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0'))
}
export function creditAmount(cents: bigint) { const n=cents<0n?-cents:cents;return `${cents<0n?'-':''}${n/100n}.${(n%100n).toString().padStart(2,'0')}` }
export function signedSupplierSourceCents(v:string){const negative=v.startsWith('-'),c=creditCents(negative?v.slice(1):v);if(c===null)throw new Error('Nominal kredit supplier tidak lengkap.');return negative?-c:c}
export function parseSupplierCredit(value: unknown): SupplierCreditWorkspace {
 const w=skuObject(value), text=(v:unknown)=>{if(typeof v!=='string'||!v)throw new Error('Identitas kredit supplier tidak lengkap.');return v}
 const amount=(v:unknown,signed=false)=>{if(typeof v!=='string'||!(signed?/^-?\d+\.\d{2}$/:/^\d+\.\d{2}$/).test(v))throw new Error('Nominal kredit supplier tidak lengkap.');return v}
 if(!(w.supplier_id===null||typeof w.supplier_id==='string')||!Number.isSafeInteger(w.page)||Number(w.page)<1||!Number.isSafeInteger(w.total)||Number(w.total)<0||typeof w.can_manage!=='boolean')throw new Error('Halaman kredit supplier tidak lengkap.')
 for(const k of ['suppliers','purchases','credits'])if(!Array.isArray(w[k]))throw new Error('Daftar kredit supplier belum lengkap.')
 for(const raw of w.suppliers as unknown[]){const s=skuObject(raw);text(s.id);text(s.code);text(s.name)}
 for(const raw of w.purchases as unknown[]){const p=skuObject(raw);for(const k of ['id','number','date','payment_status'])text(p[k]);for(const k of ['final_ap','paid'])amount(p[k]);amount(p.remaining,true);amount(p.credit_delta,true)
   if(signedSupplierSourceCents(String(p.final_ap))!==signedSupplierSourceCents(String(p.paid))+signedSupplierSourceCents(String(p.remaining)))throw new Error('Saldo utang supplier tidak cocok.')}
 for(const raw of w.credits as unknown[]){const c=skuObject(raw);for(const k of ['return_id','return_number','supplier_id','source_purchase_id','purchase_number','version'])text(c[k]);amount(c.credit);amount(c.original_purchase_credit)
   if(!Array.isArray(c.allocations)||!Array.isArray(c.events))throw new Error('Jejak alokasi kredit tidak lengkap.')
   let moved=0n;const seen=new Set<string>()
   for(const rawAllocation of c.allocations){const a=skuObject(rawAllocation),id=text(a.purchase_id);amount(a.amount);const cents=creditCents(String(a.amount))!
    if(cents<=0n||id===c.source_purchase_id||seen.has(id))throw new Error('Alokasi kredit supplier tidak cocok.');seen.add(id);moved+=cents}
   if(creditCents(String(c.credit))!==creditCents(String(c.original_purchase_credit))!+moved)throw new Error('Kredit retur tidak cocok dengan alokasinya.')
   for(const rawEvent of c.events){const e=skuObject(rawEvent);for(const k of ['id','purchase_id','date','reason','journal_id'])text(e[k]);amount(e.amount,true);if(e.reversal_of!==null)text(e.reversal_of)}
 }
 return w as SupplierCreditWorkspace
}
