"""Exact retained recovery source and fail-closed admission controls, without DB."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import ast,json

ROOT=Path(__file__).resolve().parent
PRIOR_SHA='c733553fd8b5db09132efc5e5cc50097ef1e3b4ba466afa7ad00e692fe58c03c'

def expected():
    old=(ROOT/'cp7_current_versioned_performance_recovery.py').read_bytes()
    assert sha256(old).hexdigest()==PRIOR_SHA,'EXACT_QUALIFIED_RECOVERY_CHANGED'
    text=old.decode();changes=[
        ('import cp7_current_versioned_performance_installation as installation','import cp7_current_frozen_public_installation as installation'),
        ("CONTRACT='cp7.current-AB-finance-versioned-performance.offline-full-backup.v1'","CONTRACT='cp7.current-AB-public-frozen-finance.offline-full-backup.v1'"),
        ('target_installation=installation'+'.predecessor'*4,'target_installation=installation'+'.predecessor'*7),
        ('current=state'+"['predecessor']"*10,'current=state'+"['predecessor']"*13),
        ('selected=installation.predecessor.selected.delta','selected=installation'+'.predecessor'*4+'.selected.delta'),
        ('installation.performance.','installation'+'.predecessor'*3+'.performance.'),
        ('VERSIONED_PERFORMANCE_RESTORE_','FROZEN_PUBLIC_RESTORE_'),
        ('EXACT_CURRENT_VERSIONED_PERFORMANCE_FULL_RESTORE_BOUND','EXACT_CURRENT_FROZEN_PUBLIC_FULL_RESTORE_BOUND')]
    for before,after in changes:
        assert before in text,before;text=text.replace(before,after)
    return text

def source_guard(text=None):
    actual=(ROOT/'cp7_current_frozen_public_recovery.py').read_text()if text is None else text
    assert actual==expected(),'PUBLIC_FULL_RECOVERY_UNDECLARED_LOGIC_CHANGE'
    ast.parse(actual)
    return dict(retained_recovery_sha256=PRIOR_SHA,current_recovery_sha256=sha256(actual.encode()).hexdigest(),
        all_business_data_and_OID_census_guards_unchanged=True,extra_composer_levels=3,production_go=False)

def run():
    import cp7_current_frozen_public_recovery as current
    import cp7_current_versioned_performance_recovery as old
    source=source_guard()
    assert current.target_installation is old.target_installation
    assert current.consumer is old.consumer and current.catalog is old.catalog
    assert current.installation.predecessor.predecessor.predecessor is old.installation
    actual=(ROOT/'cp7_current_frozen_public_recovery.py').read_text();source_controls=[]
    for name,before,after in[
        ('old_state_depth',"current=state"+"['predecessor']"*13,"current=state"+"['predecessor']"*10),
        ('catalog_check_removed','len(actual)!=22 or catalog._portable(actual)!=catalog._portable(backup[\'catalog\'])','False'),
        ('business_rows_check_removed',"before!=backup['data']",'False'),
        ('multiple_seals_allowed',"changed!=[('functions',catalog.GUARD)]",'False'),
        ('fresh_database_check_removed',"identity['database_oid']==backup['source_identity']['database_oid']",'False')]:
        assert before in actual,name
        try:source_guard(actual.replace(before,after))
        except AssertionError:source_controls.append(name)
        else:raise AssertionError(('RECOVERY_WEAKENING_ACCEPTED',name))
    original_catalog=current.catalog;original_chain=current.previous.chain_modules
    identity=dict(database='RESTORED',database_oid=20)
    rows={str(i):{}for i in range(22)}
    def authority(cur):return identity
    fake=SimpleNamespace(digest=original_catalog.digest,EXCLUDED=original_catalog.EXCLUDED,
        _authority=authority,_lock_tables=lambda cur:None,_catalog_rows=lambda cur:rows,_portable=lambda x:x)
    current.catalog=fake;current.previous.chain_modules=lambda:None
    refusals=[]
    try:
        backup=dict(contract=current.CONTRACT,sources=current.sources(),phase=current.previous.PHASE,
            excluded_schemas=fake.EXCLUDED,source_identity=dict(database='SOURCE',database_oid=10),
            catalog=deepcopy(rows),data={})
        def refused(name,value,prefix,hash_value=None,db='RESTORED'):
            try:current.rebind_restored(None,value,hash_value or fake.digest(value),expected_database=db)
            except ValueError as error:
                assert str(error)==prefix,(name,str(error));refusals.append(name)
            else:raise AssertionError(('BAD_RESTORE_ACCEPTED',name))
        refused('wrong_trusted_hash',backup,'FROZEN_PUBLIC_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED','0'*64)
        for name,change in[
            ('wrong_contract',lambda b:b.update(contract='old')),
            ('missing_public_layer',lambda b:b['sources'].update(current_installation=current.installation.predecessor.sources())),
            ('wrong_phase',lambda b:b.update(phase='different')),
            ('unknown_excluded_schema',lambda b:b.update(excluded_schemas=['erp']))]:
            b=deepcopy(backup);change(b);refused(name,b,'FROZEN_PUBLIC_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
        refused('wrong_database',backup,'FROZEN_PUBLIC_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED',db='OTHER')
        b=deepcopy(backup);b['source_identity']['database_oid']=20
        refused('same_database_oid',b,'FROZEN_PUBLIC_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
        b=deepcopy(backup);del b['catalog']['0'];refused('missing_catalog_group',b,'FROZEN_PUBLIC_RESTORE_CATALOG_CHANGED')
        b=deepcopy(backup);b['catalog']['1']={'public_function':'changed'}
        refused('changed_catalog_definition',b,'FROZEN_PUBLIC_RESTORE_CATALOG_CHANGED')
    finally:current.catalog=original_catalog;current.previous.chain_modules=original_chain
    assert current.catalog is original_catalog and current.previous.chain_modules is original_chain
    receipt=dict(status='PASS_LOCAL_SOURCE_AND_EARLY_REFUSAL_ONLY',source=source,
        source_controls=source_controls,early_admission_refusals=refusals,all_instrumentation_restored=True,
        database_executed=False,DDL_executed=False,actual_restore_qualified=False,production_go=False)
    print(json.dumps(receipt,indent=2));return receipt

if __name__=='__main__':run()
