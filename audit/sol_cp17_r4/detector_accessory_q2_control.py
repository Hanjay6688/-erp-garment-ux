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
    def accessory(o):
        o.update(oracle_origin='SOL_ONE_NEW_ACTIVE_ACCESSORY_NULL_CATEGORY_MATCHES_TWO_EXPLICIT_PREDICATES',fixture_origin='EXISTING_ISOLATED_MASTER_CLONE_NO_STOCK_OR_FINANCIAL_FACTS')
        c.b.api.admin(cur)
        ident=str(procurement.aa.prior.clone_material(cur,'SR4DC'))
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

    return [record('SOL_R4_D01_NEW_ACCESSORY_NULL_CATEGORY',accessory)]
