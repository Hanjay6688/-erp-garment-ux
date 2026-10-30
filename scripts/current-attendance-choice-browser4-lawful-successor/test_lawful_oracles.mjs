// Explicit local raw-data doubles. No Native, Auth, browser, HTTP or DB execution.
import assert from 'node:assert/strict'
import {test} from 'node:test'
import {immutableFacts,physicalFacts,historyFacts,FG_FIELDS} from './evidence.mjs'
import {immutableFacts as frozenFalsePredicate} from '../current-attendance-choice-browser4-qualification/evidence.mjs'

function data(){
 const qc={id:'1',product_id:'product-double',lot_id:'lot-double',location_id:'location-double',quality_grade:'GOOD',movement_type:'QC_GOOD',qty_signed:10,unit_hpp_snapshot:'10.000000',customer_id:null,source_type:'QC',source_id:'qc-double',physical_at:'2026-10-01T00:00:00Z',system_created_at:'2026-10-01T00:00:01Z',created_by:'actor-double',reversal_of_id:null,notes:'EXPLICIT_LOCAL_ORACLE_DOUBLE',book_order:1}
 const sale={...qc,id:'2',movement_type:'SALE',qty_signed:-4,customer_id:'customer-double',source_type:'SALES',source_id:'sale-double',book_order:2}
 const hpp={id:'old-hpp',lot_id:'lot-double',hpp_per_pcs:'10.000000',total_cost:'100.00',qty_basis_pcs:10,is_current:true}
 const facts={FG:[qc,sale],current_HPP:[hpp],HPP_history:[hpp],HPP_components:[{id:'old-component',hpp_version_id:'old-hpp',total_cost:'100.00'}],journal_headers:[{id:'posted-journal',status:'POSTED',source_type:'ATTENDANCE_HPP_POOL',source_id:'pool-double',reversal_of_id:null}],journal_lines:[{id:'old-line',debit:'100.00',credit:'0.00',description:'EXPLICIT_DOUBLE'}]}
 const before={original_accrual:{id:'original-double'},decisions:[],requests:[],physical_rows:facts.FG,finished_native:{double:facts},dated_WIP:[]}
 const after=structuredClone(before);after.physical_rows[0].unit_hpp_snapshot='20.003000';after.finished_native.double.FG=after.physical_rows
 after.finished_native.double.HPP_history[0].is_current=false
 const current={...hpp,id:'new-hpp',hpp_per_pcs:'20.003',total_cost:'200.03'}
 after.finished_native.double.current_HPP=[current];after.finished_native.double.HPP_history.push(current)
 after.finished_native.double.HPP_components.push({id:'intermediate-component',hpp_version_id:'new-hpp',total_cost:'200.03'})
 return{before,after}
}

test('raw old false full-FG predicate retained, exact receiving cache succeeds only against current Native HPP (local doubles)',()=>{
 const{before,after}=data();assert.throws(()=>frozenFalsePredicate(before,after),/POSTED_PHYSICAL_ROWS_CHANGED/)
 assert.notDeepEqual(after.physical_rows,before.physical_rows);assert.equal(FG_FIELDS.length,17)
 immutableFacts(before,after);assert.equal(physicalFacts(before,after).all16_non_cost_fields_exact,true)
})

test('all16 physical fields and whole SALE rows remain strict; unknown fields or non-Native cache refuse',()=>{
 const changes=[x=>x.physical_rows[0].qty_signed=11,x=>x.physical_rows[0].notes='changed',x=>x.physical_rows[0].unit_hpp_snapshot='20.004',x=>x.physical_rows[1].unit_hpp_snapshot='20.003',x=>x.physical_rows[1].notes='changed',x=>x.physical_rows[0].unknown=true,x=>x.physical_rows.pop()]
 for(const change of changes){const{before,after}=data();change(after);after.finished_native.double.FG=after.physical_rows;assert.throws(()=>physicalFacts(before,after))}
})

test('cancel retains posted and linked inverse rows and HPP versions; erased or rewritten history refuses',()=>{
 const{before,after}=data();const current=after.finished_native.double
 current.journal_headers[0].status='REVERSED';current.journal_headers.push({id:'new-inverse',status:'POSTED',source_type:'JOURNAL_REVERSAL',source_id:'posted-journal',reversal_of_id:'posted-journal'})
 historyFacts(before,after)
 for(const change of[x=>x.journal_headers.pop(),x=>x.journal_lines[0].debit='99.99',x=>x.HPP_history.shift(),x=>x.journal_headers[0].source_id='changed']){const bad=structuredClone(after);change(bad.finished_native.double);assert.throws(()=>historyFacts(before,bad))}
})

test('pre-cancel snapshot rejects symmetric posted/inverse mutation and deleted intermediate HPP history',()=>{
 const{after:active}=data(),posted=active.finished_native.double
 posted.journal_headers.push({id:'allocation-post',status:'POSTED',source_type:'ATTENDANCE_HPP_POOL',source_id:'own-pool-double',reversal_of_id:null})
 posted.journal_lines.push({id:'allocation-line',journal_entry_id:'allocation-post',debit:'100.03',credit:'0.00',description:'EXPLICIT_PRE_CANCEL_DOUBLE'})
 const cancelled=structuredClone(active),next=cancelled.finished_native.double
 next.journal_headers.find(r=>r.id==='allocation-post').status='REVERSED'
 next.journal_headers.push({id:'allocation-inverse',status:'POSTED',source_type:'JOURNAL_REVERSAL',source_id:'allocation-post',reversal_of_id:'allocation-post'})
 next.journal_lines.push({id:'inverse-line',journal_entry_id:'allocation-inverse',debit:'0.00',credit:'100.03',description:'Reversal: EXPLICIT_PRE_CANCEL_DOUBLE'})
 next.HPP_history.find(r=>r.id==='new-hpp').is_current=false
 const restored={...next.HPP_history.find(r=>r.id==='old-hpp'),id:'cancel-current-hpp',is_current:true}
 next.HPP_history.push(restored);next.current_HPP=[restored];cancelled.physical_rows[0].unit_hpp_snapshot=restored.hpp_per_pcs;next.FG=cancelled.physical_rows
 historyFacts(active,cancelled)
 const symmetric=structuredClone(cancelled),lines=symmetric.finished_native.double.journal_lines
 lines.find(r=>r.id==='allocation-line').debit='99.99';lines.find(r=>r.id==='inverse-line').credit='99.99'
 assert.throws(()=>historyFacts(active,symmetric),/POSTED_JOURNAL_LINE_HISTORY_CHANGED/)
 const erased=structuredClone(cancelled);erased.finished_native.double.HPP_history=erased.finished_native.double.HPP_history.filter(r=>r.id!=='new-hpp')
 assert.throws(()=>historyFacts(active,erased),/HPP_HISTORY_REMOVED/)
 const component=structuredClone(cancelled);component.finished_native.double.HPP_components=component.finished_native.double.HPP_components.filter(r=>r.id!=='intermediate-component')
 assert.throws(()=>historyFacts(active,component),/HPP_COMPONENT_HISTORY_CHANGED/)
})
