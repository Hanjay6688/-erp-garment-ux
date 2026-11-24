import type {RecordPageOrder} from './RecordTools'
/** OW-09 (owner D17-16): the list shape a CP7 reader applies to every matching row before it cuts the page. */
export type RecordList<S extends string=string>={q:string;status:S|null;order:RecordPageOrder}
export const wholeRecordList={q:'',status:null,order:'SOURCE'} as const
/** True only when the server echo carries exactly the requested keys and values (strict, fail closed by the caller). */
export function sameRecordList(value:unknown,expected:Readonly<Record<string,string|null>>):boolean{
 if(!value||typeof value!=='object'||Array.isArray(value))return false
 const r=value as Record<string,unknown>,keys=Object.keys(expected)
 return Object.keys(r).length===keys.length&&keys.every(k=>Object.hasOwn(r,k)&&r[k]===expected[k])
}
/** A changed search, filter or order starts again at the first page; an unchanged list keeps the page it is on. */
export const sameListShape=(a:Readonly<Record<string,unknown>>,b:Readonly<Record<string,unknown>>)=>JSON.stringify(Object.entries(a).sort())===JSON.stringify(Object.entries(b).sort())
