import {it,expect,vi} from 'vitest'
import readerSQL from '../scripts/cp7_product_analog_reader_stage/reader.sql?raw'
import {parseAnalogCandidates,readProductAnalogCandidates} from './nativeProductAnalog'
import {analogContext,analogReply,analogId} from '../tests/fixtures/nativeProductAnalog'

it('keeps a genuine available zero as an advisory and sends exact named parameters from the SQL facade',async()=>{
 const c=analogContext(),raw=analogReply(c)
 const expected=readerSQL.match(/create function public\.erp_cp7_read_product_analog_candidates_v1\(([^)]+)\)/)![1].split(',').map(p=>p.trim().split(/\s+/)[0]).sort()
 const rpc=vi.fn(async(name:string,args:unknown)=>{expect(name).toBe('erp_cp7_read_product_analog_candidates_v1');expect(Object.keys(args as object).sort()).toEqual(expected);return{data:raw,error:null}})
 const result=await readProductAnalogCandidates({rpc},c)
 expect(result.rows[0].mean).toBe('0.000000000000');expect(result.rows[0].availableDays).toBe(1)
 expect(rpc).toHaveBeenCalledWith('erp_cp7_read_product_analog_candidates_v1',{p_request:c.requestId,p_target:c.targetKey,p_offset:0,p_limit:50,p_access:c.accessEpoch})
})
it.each(['actor','request','run','epoch','identity','hash','clock','query','target','size','selected','reviewed','applied','unknown','stockout','nullMean','duplicate','refs'])('refuses mismatched or unsafe %s evidence',field=>{
 const c=analogContext(),r=analogReply(c),x=r.result.candidates[0]
 if(field==='actor')r.actor_scope_id=analogId(999)
 if(field==='request')r.request_id=analogId(999)
 if(field==='run')r.run_id=analogId(999)
 if(field==='epoch')r.access_epoch='9'.repeat(64)
 if(field==='identity')r.identity_hash='9'.repeat(64)
 if(field==='hash')r.reference.source_hash='9'.repeat(64)
 if(field==='clock')r.result.source_captured_at=r.result.source_captured_at.replace('123456','123457')
 if(field==='query')r.result.query.group_mode='RESTATED'
 if(field==='target')r.result.target_key=analogId(999)+':'+x.size_id
 if(field==='size'){x.size_id=analogId(999);x.target_key=x.root_id+':'+x.size_id}
 if(field==='selected')x.selected=true
 if(field==='reviewed')r.result.reviewed=true
 if(field==='applied')r.forecast_applied=true
 if(field==='unknown'){x.available_days=0;x.unknown_days=1}
 if(field==='stockout'){x.available_days=0;x.stockout_days=1}
 if(field==='nullMean')Object.assign(x,{observed_available_daily_mean:null})
 if(field==='duplicate'){r.result.total=2;r.result.suggested=2;r.result.candidates.push({...x})}
 if(field==='refs')x.refs=[]
 expect(()=>parseAnalogCandidates(r,c,0)).toThrow('pembanding')
})
it('binds subsequent pages to the same captured history, whole totals, profile and producer',()=>{
 const c=analogContext(),one=parseAnalogCandidates(analogReply(c,51),c,0),next=analogReply(c,51,50)
 expect(parseAnalogCandidates(next,c,50,one).rows).toHaveLength(1)
 next.result.profile_revision='2';expect(()=>parseAnalogCandidates(next,c,50,one)).toThrow()
 next.result.profile_revision='1';next.producer_hash='9'.repeat(64);expect(()=>parseAnalogCandidates(next,c,50,one)).toThrow()
})
it('accepts explicit lack of profile or insufficient history without turning it into a zero forecast',()=>{
 const c=analogContext(),raw=analogReply(c,0);raw.result.state='PLANNING_CONFIG_REQUIRED';raw.result.suggested=0
 const result=parseAnalogCandidates(raw,c,0);expect(result.minimumDays).toBeNull();expect(result.rows).toEqual([])
 raw.result.state='INSUFFICIENT_REVIEWABLE_HISTORY';raw.result.minimum_available_days='2'
 expect(parseAnalogCandidates(raw,c,0).minimumDays).toBe('2')
})
it('does not promote the captured read to a freshness check',()=>{
 const c=analogContext(),raw=analogReply(c);raw.source_state='UNCHANGED'
 expect(()=>parseAnalogCandidates(raw,c,0)).toThrow()
})
