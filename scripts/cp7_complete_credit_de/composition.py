"""D1 then E on the complete S03/SKU/S05 parent, with exact raw source guards.

Preparation only. The caller must admit the actual accepted permanent-parent
qualification and own every package, Auth, backup and full restore gate.
This module supplies no connection, commit, runtime dispatch or default.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTRACT='cp7.current-complete-credit-de.v1'
USED_ERROR='COMPLETE_CREDIT_DE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'


def parts():
    from cp7_current_s03_sku_s05 import composition as complete
    from cp7_credit_correction_de import composition as d1
    from cp7_credit_correction_de import e_composition as e
    if d1.predecessor is not complete or e.predecessor is not d1:
        raise ValueError('COMPLETE_CREDIT_DE_NATURAL_PARENT_OBJECT_CHAIN_REQUIRED')
    return complete,d1,e


def parent():return parts()[0]
def runtime():return parent().runtime()


def source_manifest():
    value=json.loads((HERE/'SOURCE.json').read_bytes())
    if(value['contract']!=CONTRACT or value['actual_Native_cases']!=0
       or value['production_go']is not False or value['independent_acceptance']is not False):
        raise ValueError('COMPLETE_CREDIT_DE_PREPARATION_SOURCE_REQUIRED')
    for name,pin in value['files'].items():
        path=ROOT/name;raw=path.read_bytes()
        if path.is_symlink()or len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('COMPLETE_CREDIT_DE_SOURCE_CHANGED:'+name)
    return value


def sources():
    manifest=source_manifest()
    _,_,e=parts()
    return dict(contract=CONTRACT,predecessor=e.sources(),source=manifest,
        S03_SKU_S05_parent_retained=True,D_complete=False,E_complete=False,
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)


def parent_qualification():
    path=ROOT/'scripts/current-complete-de-integration-preparation/admission.py'
    spec=importlib.util.spec_from_file_location('complete_DE_closed_actual_parent',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.parent_receipt()


def qualified_parent_sources(receipt,state):
    raw=json.dumps(state['sources'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    actual=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    expected=receipt.get('qualified_complete_sources')
    if(type(expected)is not dict or set(expected)!={'bytes','sha256'}
       or type(expected.get('bytes'))is not int or type(expected.get('sha256'))is not str
       or expected!=actual):
        raise ValueError('COMPLETE_CREDIT_DE_ENTIRE_SOURCE_GRAPH_MUST_EQUAL_ACTUAL_PERMANENT6')
    return actual


def raw_authority(cur,signatures):
    rows=cur.execute("select s.signature,p.oid::text,pg_get_userbyid(p.proowner),p.proacl::text "
        "from unnest(%s::text[])s(signature)join pg_proc p on p.oid=to_regprocedure(s.signature) "
        'order by s.signature collate "C"',(sorted(signatures),)).fetchall()
    if len(rows)!=len(signatures):raise ValueError('COMPLETE_CREDIT_DE_ALL_RAW_FUNCTION_IDENTITIES_REQUIRED')
    return {row[0]:list(row[1:])for row in rows}


def binding(catalog,state):
    complete=state['complete_parent'];d1=state['D1'];e=state['E']
    return catalog.digest(dict(sources=state['sources'],before=state['before'],after=state['after'],
        qualified_complete_sources=state['qualified_complete_sources'],
        raw_existing_function_authority=state['raw_existing_function_authority'],
        complete_component_binding=complete['component_binding'],complete_sources=complete['sources'],
        complete_binding_recomputed=parent().binding(catalog,complete),
        D1_parent_binding=d1['parent_binding'],D1_catalog=d1['after'],D1_sources=d1['sources'],
        D1_preinstall=d1['preinstall_data_and_sequences'],D1_preuse=d1['preuse_data_and_sequences'],
        E_parent_binding=e['parent_binding'],E_catalog=e['after'],E_sources=e['sources'],
        E_preinstall=e['preinstall_data_and_sequences'],E_preuse=e['preuse_data_and_sequences'],
        preinstall=state['preinstall_data_and_sequences'],preuse=state['preuse_data_and_sequences']))


def verify(cur,state):
    actual_parent=qualified_parent_sources(parent_qualification(),state['complete_parent'])
    if state['qualified_complete_sources']!=actual_parent:
        raise ValueError('COMPLETE_CREDIT_DE_QUALIFIED_PARENT_SOURCE_PIN_CHANGED')
    complete,d1,e=parts();_,_,_,_,catalog=runtime();catalog._authority(cur)
    if state['sources']!=sources():raise ValueError('COMPLETE_CREDIT_DE_ACTUAL_SOURCE_CHANGED')
    if(state['D1']['predecessor']!=state['complete_parent']or state['E']['predecessor']!=state['D1']
       or state['before']!=state['complete_parent']['after']or state['after']!=state['E']['after']
       or state['preinstall_data_and_sequences']!=state['complete_parent']['preinstall_data_and_sequences']
       or state['preuse_data_and_sequences']!=state['E']['preuse_data_and_sequences']
       or complete.binding(catalog,state['complete_parent'])!=state['complete_parent']['component_binding']):
        raise ValueError('COMPLETE_CREDIT_DE_ACTUAL_STATE_CHAIN_CHANGED')
    if state['component_binding']!=binding(catalog,state):raise ValueError('COMPLETE_CREDIT_DE_BOUNDARY_BINDING_CHANGED')
    if raw_authority(cur,state['raw_existing_function_authority'])!=state['raw_existing_function_authority']:
        raise ValueError('COMPLETE_CREDIT_DE_EXISTING_OID_OWNER_OR_RAW_ACL_CHANGED')
    top=e.verify(cur,state['E'])
    return dict(status='COMPLETE_CREDIT_DE_EXACT_INSTALLED_ALL22',top=top,
        previous_parent_verifiers_never_called_on_projected_catalogues=True,
        S03_SKU_S05_parent_retained=True,D_complete=False,E_complete=False,
        global_eight_hook_runtime_opened=False,production_go=False,independent_acceptance=False)


def install_delta(cur,qualified_complete_parent):
    receipt=parent_qualification()  # Pending closes before ERP imports or any database statement.
    accepted_sources=qualified_parent_sources(receipt,qualified_complete_parent)
    pins=sources()
    complete,d1,e=parts();_,_,_,base,catalog=runtime()
    with base.atomic(cur):
        complete.verify(cur,qualified_complete_parent)
        expected=json.loads((HERE/'RECORDED_NATIVE_CAPTURES.json').read_bytes())['functions']
        before=catalog._catalog_rows(cur)
        for signature,row in expected.items():
            if json.dumps(before['functions'].get(signature),sort_keys=True,separators=(',',':'),allow_nan=False)!=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False):
                raise ValueError('COMPLETE_CREDIT_DE_EXACT_CURRENT_FULL19_BEFORE_DDL_REQUIRED:'+signature)
        authority=raw_authority(cur,expected)
        first=d1.install_delta(cur,qualified_complete_parent)
        d1.verify(cur,first)
        second=e.install_delta(cur,first)
        e.verify(cur,second)
        if raw_authority(cur,expected)!=authority:
            raise ValueError('COMPLETE_CREDIT_DE_INSTALL_CHANGED_EXISTING_OID_OWNER_OR_RAW_ACL')
        state=dict(sources=pins,complete_parent=qualified_complete_parent,D1=first,E=second,
            qualified_complete_sources=accepted_sources,
            raw_existing_function_authority=authority,
            before=qualified_complete_parent['after'],after=second['after'],
            preinstall_data_and_sequences=qualified_complete_parent['preinstall_data_and_sequences'],
            preuse_data_and_sequences=second['preuse_data_and_sequences'])
        state['component_binding']=binding(catalog,state);verify(cur,state);return state


def rollback_delta_preuse(cur,state):
    complete,d1,e=parts();_,_,_,base,catalog=runtime()
    with base.atomic(cur):
        base.predecessor.predecessor._locks(cur);verify(cur,state);catalog._lock_tables(cur)
        if catalog._data(cur)!=state['preuse_data_and_sequences']:raise ValueError(USED_ERROR)
        second=e.rollback_delta_preuse(cur,state['E'])
        first=d1.rollback_delta_preuse(cur,state['D1'])
        proof=complete.verify(cur,state['complete_parent'])
        if(catalog._catalog_rows(cur)!=state['before']
           or catalog._data(cur)!=state['complete_parent']['preuse_data_and_sequences']):
            raise ValueError('COMPLETE_CREDIT_DE_EXACT_PARENT_ROWS_CATALOG_SEQUENCES_NOT_RESTORED')
        return dict(status='COMPLETE_CREDIT_DE_PREUSE_DELTA_INVERSE',E=second,D1=first,parent=proof,
            used_guard_before_DDL=True)
