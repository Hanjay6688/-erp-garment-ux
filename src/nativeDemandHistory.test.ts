// @vitest-environment jsdom
import{describe,expect,it}from'vitest'
import{parseNativeDemandHistory,yesterdayWib,readNativeDemandRequest,persistNativeDemandRequest,clearNativeDemandRequest,nativeDemandRequestKey}from'./nativeDemandHistory'
import{demandWire,demandRequest}from'../tests/fixtures/nativeDemandHistory'
describe('authoritative demand wire boundaries',()=>{
 it('keeps native physical, draft and available quantities separate; unknown stays unknown',()=>{const r=parseNativeDemandHistory(demandWire());expect(r.rows[0]).toMatchObject({physical:'100',reserved:'24',available:'76',gross:'0',trainingAvailable:false,unknownDays:1});expect(r.state).toBe('UNCHANGED')})
 it('retains a stale archive as explicitly stale',()=>{const w=demandWire();w.source_state='ARCHIVED_STALE';expect(parseNativeDemandHistory(w).state).toBe('ARCHIVED_STALE')})
 it.each(['hash','scope','run','duplicate','missing_history','quantity','native_quantity','unknown_training','days','returns','version','partial','capture_knowledge','forecast'])( 'refuses inconsistent %s',kind=>{
  const w=demandWire()
  switch(kind){case'hash':w.source_hash='b'.repeat(64);break;case'scope':w.scope='FILTERED';break;case'run':w.run_id='missing';break;case'duplicate':w.current_stock.push(structuredClone(w.current_stock[0]));break;case'missing_history':w.history.rows=[];break;case'quantity':w.current_stock[0].availability.available_fg_pcs='100';break;case'native_quantity':w.current_stock[0].native_available_pcs='77';break;case'unknown_training':w.history.rows[0].days[0].training_pcs='0' as never;break;case'days':w.history.rows[0].unknown_days=0;break;case'returns':w.history.rows[0].days[0].returned_pcs='1';break;case'version':w.versions.history='other';break;case'partial':w.capture_complete=false;break;case'capture_knowledge':w.training_known_at='2026-09-28T00:00:00.000000Z';break;case'forecast':w.current_stock[0].availability.inputs.residual_future_pcs='50';break}
  expect(()=>parseNativeDemandHistory(w)).toThrow()
 })
 it('preserves exact PCS above JavaScript safe integer',()=>{const w=demandWire();w.current_stock[0].availability.physical_fg_pcs='9007199254741017';w.current_stock[0].availability.available_fg_pcs='9007199254740993';w.current_stock[0].native_available_pcs='9007199254740993';expect(parseNativeDemandHistory(w).rows[0].available).toBe('9007199254740993')})
 it('uses WIB yesterday across midnight and caller timezone',()=>{expect(yesterdayWib(new Date('2026-09-30T17:01:00Z'))).toBe('2026-09-30');expect(yesterdayWib(new Date('2026-09-30T16:59:00Z'))).toBe('2026-09-29')})
})
describe('same native capture survives reply loss',()=>{
 const scope='test:native-demand',q={from_date:'2026-09-29',through_date:'2026-09-29',group_mode:'AS_SOLD' as const}
 it('retains exact query/UUID and refuses replacement or wrong clearing',()=>{localStorage.clear();persistNativeDemandRequest(scope,{id:demandRequest,q});expect(readNativeDemandRequest(scope).pending).toEqual({id:demandRequest,q});expect(()=>persistNativeDemandRequest(scope,{id:crypto.randomUUID(),q})).toThrow();expect(()=>clearNativeDemandRequest(scope,crypto.randomUUID())).toThrow();expect(readNativeDemandRequest(scope).pending?.id).toBe(demandRequest);clearNativeDemandRequest(scope,demandRequest);expect(readNativeDemandRequest(scope).pending).toBeNull()})
 it('fails closed on corrupt saved state and isolates actors',()=>{localStorage.clear();localStorage.setItem(nativeDemandRequestKey(scope),'broken');expect(readNativeDemandRequest(scope).error).not.toBe('');expect(()=>persistNativeDemandRequest(scope,{id:demandRequest,q})).toThrow();expect(readNativeDemandRequest(scope+'-other')).toEqual({pending:null,error:''})})
})
