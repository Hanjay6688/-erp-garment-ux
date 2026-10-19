"""Four predeclared counterfixtures on mutable derived state/new master only.

Every trigger stays active. No journal/movement/HPP fact, permission, guard,
function or trigger is edited. Administrative fixture writes are loopback-only
inside the existing Native rollback runner; this is not ordinary CRUD proof.
"""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
PRODUCT=ROOT.parents[2]/'auditor'
sys.path.insert(0,str(PRODUCT/'scripts'))
import cp7_cp17_fix_cases as c
import cp7_procurement_cases as procurement
import cp7_recost_cases as recost
from detector_case import detector_rows,counts
def record(ident,fn):
    observed=dict(case_id=ident,source='CURRENT_PINNED_NATIVE_DETECTORS')
    def once():
        try:
            fn(observed)
            observed['status']='PASS'
            return observed
        finally:
            out=PRODUCT/'cp6-proof/t3'/(ident+'_OBSERVATIONS.json')
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(observed,indent=2,default=str)+'\n')
    return ident,once

FACTS=('journal_entries','journal_lines','material_stock_movements','fg_stock_movements','wip_stage_events','hpp_versions','hpp_version_components')
GUARDS=('guard_system_managed_table()','guard_material_cached_fields()','guard_material_accessory_category_history()','validate_material_accessory_category()')

def fingerprints(cur):
    c.b.api.admin(cur)
    facts={table:cur.execute("select count(*),md5(coalesce(string_agg(md5(to_jsonb(t)::text),'' order by id::text),'')) from erp."+table+' t').fetchone() for table in FACTS}
    guards={name:hashlib.sha256(cur.execute('select pg_get_functiondef(to_regprocedure(%s))',('erp.'+name,)).fetchone()[0].encode()).hexdigest() for name in GUARDS}
    return dict(immutable_facts=facts,guard_definitions=guards)

def schema(cur,table,columns):
    c.b.api.admin(cur)
    rows=cur.execute('select column_name,data_type,numeric_precision,numeric_scale,is_nullable from information_schema.columns where table_schema=\'erp\' and table_name=%s and column_name=any(%s) order by column_name',(table,list(columns))).fetchall()
    out={name:dict(type=typ,precision=precision,scale=scale,nullable=nullable) for name,typ,precision,scale,nullable in rows}
    assert set(out)==set(columns),('SOL_MUTABLE_SCHEMA_COLUMNS',table,out)
    return out

def baseline(cur,o):
    o['before']=detector_rows(cur)
    values=counts(o['before'])
    assert len(values)==167 and all(v==0 for v in values.values()),'SOL_MUTABLE_BASELINE_NOT_ZERO'
    o['protected_before']=fingerprints(cur)
    return values

def phase(cur,o,name,expected,before):
    rows=detector_rows(cur);during=counts(rows)
    o.setdefault('phases',[]).append(dict(name=name,rows=rows,expected_deltas=expected))
    assert set(during)==set(before) and len(during)==167,'SOL_MUTABLE_ALL_167_IDENTITIES'
    delta={key:during[key]-value for key,value in before.items() if during[key]!=value}
    o['phases'][-1]['observed_deltas']=delta
    assert delta==expected,('SOL_MUTABLE_EXACT_EXPECTED_UNITS',name,expected,delta)
    assert fingerprints(cur)==o['protected_before'],'SOL_MUTABLE_PROTECTED_FACT_OR_GUARD_CHANGED'

def restored(cur,o,before):
    o['after_rollback']=detector_rows(cur)
    after=counts(o['after_rollback'])
    assert set(after)==set(before) and len(after)==167 and after==before,'SOL_MUTABLE_ALL_167_RESTORED'
    assert fingerprints(cur)==o['protected_before']
    o.update(all_nine_functions_each_phase=True,all167rows_each_phase=True,immutable_facts_and_guard_definitions_unchanged=True,no_trigger_privilege_or_function_change=True)

def cases(cur,today):
    def queue(o):
        o.update(oracle_origin='SOL_ACTIVE_STATUS_AND_AGE_PREDICATES_ONE_QUEUE_ROW',fixture_origin='EXISTING_P13_ADMINISTRATIVE_FAULT_CONSTRUCTOR_NO_PROCESSOR_EXECUTED')
        o['schema']=schema(cur,'cost_recalc_queue',('id','entity_type','entity_id','status','attempt_count','queued_at'))
        assert o['schema']['id']['type']=='bigint' and o['schema']['attempt_count']['type']=='integer' and o['schema']['queued_at']['type']=='timestamp with time zone'
        before=baseline(cur,o)
        cur.execute('savepoint sol_mutable_control')
        try:
            ident=recost.fault(cur,'PENDING',0)
            c.b.api.admin(cur)
            changed=cur.execute("update erp.cost_recalc_queue set queued_at=statement_timestamp()-interval '11 minutes' where id=%s returning id::text,entity_type,status,attempt_count,queued_at::text",(ident,)).fetchall()
            assert len(changed)==1
            o['source_queue']=changed
            phase(cur,o,'OLD_PENDING',{'run_integrity_checks:STALE_RECOST_QUEUE':1,'run_v268_financial_report_checks:V268_COST_RECALC_PENDING':1},before)
            c.b.api.admin(cur)
            assert cur.execute("update erp.cost_recalc_queue set status='FAILED',attempt_count=1 where id=%s returning status,attempt_count",(ident,)).fetchone()==('FAILED',1)
            phase(cur,o,'RETRYABLE_FAILED',{'run_integrity_checks:FAILED_RECOST_QUEUE':1,'run_v268_financial_report_checks:V268_COST_RECALC_PENDING':1},before)
            c.b.api.admin(cur)
            assert cur.execute("update erp.cost_recalc_queue set attempt_count=3 where id=%s returning status,attempt_count",(ident,)).fetchone()==('FAILED',3)
            phase(cur,o,'EXHAUSTED_FAILED',{'run_integrity_checks:FAILED_RECOST_QUEUE':1,'run_v268_financial_report_checks:V268_COST_RECALC_EXHAUSTED':1},before)
        finally:
            cur.execute('rollback to savepoint sol_mutable_control');c.b.api.admin(cur)
        assert cur.execute('select count(*) from erp.cost_recalc_queue where id=%s',(ident,)).fetchone()[0]==0
        restored(cur,o,before)
        o['queue_row_removed']=True
    def material(o):
        o.update(oracle_origin='SOL_ONE_OWN_MATERIAL_CACHE_VALUE_DIFFERS_BY_ONE',fixture_origin='ACCEPTED_PUBLIC_RECEIPT_QTY1_PRICE10_BEFORE_COUNTERFIXTURE')
        f=procurement.fixture(cur,today,qty='1',price='10',final=True)
        posted=procurement.post(cur,procurement.command(cur,'SAVE_DRAFT',f['payload']))
        c.b.api.admin(cur)
        o['schema']=schema(cur,'materials',('id','cached_stock_qty','moving_average_cost'))
        assert all(o['schema'][x]['type']=='numeric' and o['schema'][x]['precision']==18 and o['schema'][x]['scale']==6 for x in ('cached_stock_qty','moving_average_cost'))
        row=lambda:cur.execute('select to_jsonb(m) from erp.materials m where id=%s',(f['material'],)).fetchone()[0]
        original=row()
        assert Decimal(str(original['cached_stock_qty']))==1 and Decimal(str(original['moving_average_cost']))==10
        o.update(source_material=f['material'],source_purchase=posted['purchase_id'],original_cache=original,expected_inventory_value_before='10.00',expected_poisoned_cache_value='11.00')
        before=baseline(cur,o)
        cur.execute('savepoint sol_mutable_control')
        try:
            c.b.api.admin(cur)
            changed=cur.execute('update erp.materials set moving_average_cost=moving_average_cost+1 where id=%s returning cached_stock_qty::text,moving_average_cost::text',(f['material'],)).fetchall()
            assert len(changed)==1 and tuple(map(Decimal,changed[0]))==(Decimal(1),Decimal(11))
            o['changed_cache']=changed
            phase(cur,o,'MAC_10_TO_11',{'run_v255_material_cost_integrity_checks:MATERIAL_GL_VALUATION_MISMATCH':1},before)
        finally:
            cur.execute('rollback to savepoint sol_mutable_control');c.b.api.admin(cur)
        assert row()==original
        restored(cur,o,before);o['full_cache_row_restored']=True
    def po_qty(o):
        o.update(oracle_origin='SOL_ONE_PO_DERIVED_OUTPUT_CACHE_10_TO_11_WITH_FACTS_FIXED',fixture_origin='ACCEPTED_NATIVE_FINISH_FIXTURE10_GOOD')
        f=c.finish_fixture(cur,today,label='SOLR4-D01-POCACHE')
        c.b.api.admin(cur)
        o['schema']=schema(cur,'po_hpp_gl_state',('po_id','base_output_qty'))
        assert o['schema']['base_output_qty']['type']=='integer'
        row=lambda:cur.execute('select to_jsonb(s) from erp.po_hpp_gl_state s where po_id=%s',(f['po'],)).fetchone()[0]
        original=row();assert original['base_output_qty']==10
        o.update(source_po=f['po'],original_cache=original)
        before=baseline(cur,o)
        cur.execute('savepoint sol_mutable_control')
        try:
            c.b.api.admin(cur)
            changed=cur.execute('update erp.po_hpp_gl_state set base_output_qty=base_output_qty+1 where po_id=%s returning base_output_qty',(f['po'],)).fetchall()
            assert changed==[(11,)];o['changed_cache']=changed
            phase(cur,o,'PO_OUTPUT_CACHE_10_TO_11',{'run_v268_financial_report_checks:V2620C_PO_HPP_TARGET_STATE_MISMATCH':1},before)
        finally:
            cur.execute('rollback to savepoint sol_mutable_control');c.b.api.admin(cur)
        assert row()==original
        restored(cur,o,before);o['full_cache_row_restored']=True
    def accessory(o):
        o.update(oracle_origin='SOL_ONE_NEW_ACTIVE_ACCESSORY_NULL_CATEGORY_MATCHES_TWO_EXPLICIT_PREDICATES',fixture_origin='EXISTING_ISOLATED_MASTER_CLONE_NO_STOCK_OR_FINANCIAL_FACTS')
        c.b.api.admin(cur)
        ident=str(procurement.aa.prior.clone_material(cur,'SOLR4-DETECTOR-MASTER'))
        o['schema']=schema(cur,'materials',('id','material_type','accessory_category_id','is_active'))
        assert o['schema']['accessory_category_id']['type']=='uuid' and o['schema']['accessory_category_id']['nullable']=='YES'
        row=lambda:cur.execute('select to_jsonb(m) from erp.materials m where id=%s',(ident,)).fetchone()[0]
        original=row();assert original['material_type']!='ACCESSORY' and original['accessory_category_id'] is None and original['is_active'] is True
        assert cur.execute('select count(*) from erp.material_stock_movements where material_id=%s',(ident,)).fetchone()[0]==0
        o.update(source_material=ident,original_master=original,ordinary_master_CRUD_claim=False)
        before=baseline(cur,o)
        cur.execute('savepoint sol_mutable_control')
        try:
            c.b.api.admin(cur)
            changed=cur.execute("update erp.materials set material_type='ACCESSORY' where id=%s returning material_type,accessory_category_id,is_active",(ident,)).fetchall()
            assert changed==[('ACCESSORY',None,True)];o['changed_master']=changed
            phase(cur,o,'OWN_NEW_ACCESSORY_WITH_NULL_CATEGORY',{'run_v24_accessory_integrity_checks:ACCESSORY_WITHOUT_CATEGORY':1,'run_v266_gudang_accessory_fg_checks:v266_accessory_material_category_mismatch':1},before)
        finally:
            cur.execute('rollback to savepoint sol_mutable_control');c.b.api.admin(cur)
        assert row()==original
        restored(cur,o,before);o['full_master_row_restored']=True
    return [record('SOL_R4_D01_QUEUE_STATUS_AND_AGE_ONE_ROW',queue),record('SOL_R4_D01_MATERIAL_MAC_CACHE_ONE_KEY',material),record('SOL_R4_D01_PO_OUTPUT_CACHE_ONE_KEY',po_qty),record('SOL_R4_D01_NEW_ACCESSORY_NULL_CATEGORY',accessory)]
