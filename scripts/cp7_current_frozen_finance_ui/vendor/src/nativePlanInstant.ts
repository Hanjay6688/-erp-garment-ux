import {fail} from './nativePlanDraft'

export function planInstantMicros(v:unknown):bigint{
 if(typeof v!=='string')return fail()
 const m=v.match(/^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?(Z|[+-]\d\d:\d\d)$/)
 if(!m)return fail()
 const local=Date.parse(m[1]+'Z'),utc=Date.parse(m[1]+m[3])
 // Reject calendar normalization (e.g. February 30 or 24:00), then compare
 // PostgreSQL's full microseconds. Date.parse alone discards the last three.
 if(!Number.isFinite(local)||!Number.isFinite(utc)||new Date(local).toISOString().slice(0,19)!==m[1])return fail()
 return BigInt(utc)*1000n+BigInt((m[2]??'').padEnd(6,'0'))
}
