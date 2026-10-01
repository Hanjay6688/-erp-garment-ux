import {it,expect} from 'vitest'
import fixture from '../tests/fixtures/nativeAnalysisStandin.json'
import {nativeReceivableFixture} from '../tests/fixtures/nativeReceivableConditions'
import {parseNativeReceivableConditions} from './nativeReceivableConditions'
import type {NativeDemandQuery} from './nativeDemandHistory'
const parse=(v:unknown,ar=true)=>parseNativeReceivableConditions(v,fixture.query as NativeDemandQuery,fixture.analysis.scope.actor_scope_id,{ownerReports:false,preflight:false},ar)
it('keeps the exact accepted Native balance and source while preserving original analysis',()=>{
 const v=nativeReceivableFixture(),p=parse(v);expect(p.rows[0].document.financial?.open_balance).toBe('300.00');expect(p.rows[0].document.row_version).toBe('9007199254740993');expect(p.rows[0].condition.business_resolved).toBe(false);expect(p.analysis.analysis).toEqual(fixture.analysis)
 v.source.pages[0].page.rows[0].financial!.open_balance='10.00';expect(p.rows[0].document.financial?.open_balance).toBe('300.00')
})
it('does not turn missing Native due dates or invoice credits into healthy or zero balances',()=>{
 const v=nativeReceivableFixture(),row=v.source.pages[0].page.rows[0],c=v.source.conditions[0];row.due_date=null;c.state='MISSING_DUE_DATE';expect(parse(v).rows[0].condition.state).toBe('MISSING_DUE_DATE')
 row.financial!.paid_total='510.00';row.financial!.open_balance='-10.00';c.state='CREDIT_REVIEW';expect(parse(v).rows[0].condition.business_resolved).toBe(false)
 c.business_resolved=true;expect(()=>parse(v)).toThrow()
})
it('accepts zero debt only when the actual Native document balance is zero',()=>{
 const v=nativeReceivableFixture();v.source.pages[0].page.rows[0].status='PAID';v.source.pages[0].page.rows[0].financial!.paid_total='500.00';v.source.pages[0].page.rows[0].financial!.open_balance='0.00';Object.assign(v.source.conditions[0],{state:'ZERO_BALANCE',business_resolved:true});expect(parse(v).rows[0].condition.business_resolved).toBe(true)
 v.source.pages[0].page.rows[0].financial!.paid_total='200.00';v.source.pages[0].page.rows[0].financial!.open_balance='300.00';expect(()=>parse(v)).toThrow()
})
it('refuses foreign/current-denied source, page gaps, duplicate documents and mismatched Native revisions',()=>{
 expect(()=>parse(nativeReceivableFixture(),false)).toThrow()
 const actor=nativeReceivableFixture();actor.actor_scope_id='00000000-0000-4000-8000-000000000001';expect(()=>parse(actor)).toThrow()
 const revision=nativeReceivableFixture();revision.source.conditions[0].source_revision='2';expect(()=>parse(revision)).toThrow()
 const gap=nativeReceivableFixture();gap.source.pages[0].page.offset=25;expect(()=>parse(gap)).toThrow()
 const duplicate=nativeReceivableFixture();duplicate.source.total='2';duplicate.source.pages[0].page.total='2';duplicate.source.pages[0].page.rows.push(duplicate.source.pages[0].page.rows[0]);duplicate.source.conditions.push(duplicate.source.conditions[0]);expect(()=>parse(duplicate)).toThrow()
 const incomplete=nativeReceivableFixture();incomplete.source.page_complete=false;expect(()=>parse(incomplete)).toThrow()
})
it('checks Native dates in WIB and rejects invented rollover or shifted due/as-of clocks',()=>{
 const v=nativeReceivableFixture();v.source.read_at='2026-09-30T18:00:00Z';v.source.pages[0].read_at=v.source.read_at;expect(parse(v).asOf).toBe('2026-10-01')
 v.source.as_of='2026-09-30';expect(()=>parse(v)).toThrow()
 v.source.as_of='2026-10-01';v.source.pages[0].page.rows[0].due_date='2026-02-30';expect(()=>parse(v)).toThrow()
 v.source.read_at='2026-09-30T24:00:00Z';expect(()=>parse(v)).toThrow()
})
