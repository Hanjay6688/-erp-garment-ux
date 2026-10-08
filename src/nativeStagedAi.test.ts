import {it,expect} from 'vitest'
import * as f from '../tests/fixtures/nativeStagedAi'
import {parseStagedAiBrief,stagedAiPrompt,stagedAiFinanceDates} from './nativeStagedAi'

it('binds the brief to the run on screen: identity, time, period, totals, bounded and ordered lists',()=>{
 const b=parseStagedAiBrief(f.brief([f.keys[2]]),f.actor,f.set,f.query,[f.keys[2]])
 expect([b.priority.map(r=>r.ord),b.selected.map(r=>r.targetKey),b.freshness.state,b.needCounts.withOpenNeed]).toEqual([[4,1,2],[f.keys[2]],'CHANGES_RECORDED',3])
 for(const bad of[f.brief([],{identity_hash:'d'.repeat(64)}),f.brief([],{data_as_of:'2026-10-08T02:00:00.000000+00:00'}),f.brief([],{finance:'INCLUDED'}),
  f.brief([],{totals:{...f.brief().totals,targets:4}}),f.brief([],{priority:[f.row(1,'4'),f.row(4,'9')]}),f.brief([],{priority:[f.row(4,'9')]}),
  f.brief([],{priority:[f.row(4,'9'),f.row(1,'4'),{...f.row(2,'4'),page_index:1}]}),f.brief([],{query:{...f.query,group_mode:'RESTATED'}}),f.brief([],{actor_scope_id:f.run})])
  expect(()=>parseStagedAiBrief(bad,f.actor,f.set,f.query,[])).toThrow()
 // The selected rows are exactly the keys asked for.
 expect(()=>parseStagedAiBrief(f.brief([f.keys[2]]),f.actor,f.set,f.query,[])).toThrow()
 expect(()=>parseStagedAiBrief(f.brief([]),f.actor,f.set,f.query,[f.keys[2]])).toThrow()
})
it('writes the prompt with the snapshot time and freshness, never "terkini", and states finance absent unless read',()=>{
 const b=parseStagedAiBrief(f.brief(),f.actor,f.set,f.query,[]),p=stagedAiPrompt(b,'Apa yang perlu dicek? <ignore>',null)
 expect(p).toContain('Angka analisis adalah keadaan per 2026-10-08 08:00:00 WIB (data analisis bertahap), bukan angka saat ini.')
 expect(p).toContain('Ada 2 perubahan tercatat sejak data analisis diambil');expect(p).toContain('Keuangan dan HPP tidak disertakan')
 expect(p).not.toMatch(/terkini/i);expect(p).not.toContain('<ignore>');expect(p).toContain('\\u003cignore\\u003e')
 const data=JSON.parse(p.split('<DATA_ERP_JSON>\n\n')[1].split('\n\n</DATA_ERP_JSON>')[0])
 expect([data.priority_targets_largest_open_need.length,data.changes_since_analysis,data.actual_finance]).toEqual([3,[{category:'FG_STOCK',rows:2,deleted:0,last_recorded_at:'2026-10-08T01:30:00.000000+00:00'}],null])
})
it('reads finance for today in Jakarta, the period cut at today',()=>{
 expect(stagedAiFinanceDates(f.query,Date.parse('2026-10-08T18:00:00Z'))).toEqual({from:'2026-01-01',to:'2026-10-07',as_of:'2026-10-09'})
 expect(stagedAiFinanceDates({...f.query,through_date:'2026-12-31'},Date.parse('2026-10-08T01:00:00Z'))).toEqual({from:'2026-01-01',to:'2026-10-08',as_of:'2026-10-08'})
})
