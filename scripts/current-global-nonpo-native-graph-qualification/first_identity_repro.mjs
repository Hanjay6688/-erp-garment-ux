/** Frozen4e263 structural closure counterexample. No Native business execution. */
import assert from 'node:assert/strict';
import path from 'node:path';
import {setup,inspect,snapshot,uuid,here} from './model.mjs';
const db=await setup({sqlSources:{'scope.sql':path.join(here,'retained/4e263_scope.sql'),
 'capture.sql':path.join(here,'retained/4e263_capture.sql')}});
await db.exec(`insert into erp.bc_documents_v1 values('${uuid(901)}','POSTED');
 insert into erp.material_adjustments values('${uuid(902)}',0);
 insert into erp.be_conversion_cost_sources_v1 values('${uuid(901)}','${uuid(201)}','USAGE');
 insert into erp.journal_entries(id,status,source_type,source_id)values('${uuid(610)}','POSTED','LOCAL_STRUCTURAL_MIXED',null);
 insert into erp.journal_lines values('${uuid(710)}','${uuid(610)}','${uuid(501)}',0,1,null,null),
 ('${uuid(711)}','${uuid(610)}','${uuid(501)}',1,0,'${uuid(21)}',null);
 insert into erp.be_conversion_cost_events_v1 values('${uuid(903)}','${uuid(901)}','${uuid(902)}',1,1,'${uuid(610)}','2026-10-20');
 set local_model.inspecting='on'`);
const before=await snapshot(db),result=await inspect(db),after=await snapshot(db);
assert.deepEqual(before,after);
const leaked=result.outside_source.facts.journal_lines.filter(x=>x.journal_entry_id===uuid(610));
assert.equal(result.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');
assert.deepEqual(result.scope.relevant.product_ids,[uuid(21)]);
assert.deepEqual(result.scope.outside.product_ids,[uuid(22),uuid(23)]);
assert(leaked.some(x=>x.product_id===uuid(21)));
console.log(JSON.stringify({classification:'LOCAL_TYPED_SCHEMA_CLOSURE_SENSITIVITY_NOT_NATIVE_BUSINESS_OR_NATIVE_BUG',
 status:'CONFIRMED_INSPECTOR_IDENTITY_CUT_GAP',frozen_inspector:'4e263e3437efa156ac27bd95989e2880be8cb570',
 source_pins:db.localSourcePins,relevant:result.scope.relevant,outside:result.scope.outside,mixed_journal_lines:leaked,
 observed_status:result.status,qualified_for_runtime:result.qualified_for_runtime,
 direct_before:before,direct_after:after,actual_Native:0,actual_DB_server:0,production_go:false},null,2));
await db.close();
