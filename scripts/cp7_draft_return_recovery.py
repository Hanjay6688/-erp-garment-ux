"""Exact full backup binding for current A/B plus the isolated draft-return delta.

This new contract binds the exact current installation and one-function delta.
Every source, all22 catalog groups, every row and every sequence must match
before regenerating the one local Native-trigger OID census. No live restore,
connection or commit is performed by this module.
"""
from hashlib import sha256
from pathlib import Path

from cp7_ab_bounded_chain import composition as product
import cp7_current_installation as installation
import cp7_draft_return_isolation as delta
from cp7_ab_quote_chain import recovery as previous_recovery
from cp7_contractor_correction import composition as ow05
import cp7_ow04_restore_bundle as catalog

VERSION='ow15.draft-return-isolation.offline-full-backup.v1'
PHASE='OW04_CONSUMER_BOUNDED'
DEPTH=15
consumer=ow05.predecessor.predecessor.consumer


def sources():
    return dict(current_installation=installation.sources(),draft_return_delta=delta.sources(),
        administrative_restore_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def chain_modules():
    return previous_recovery.chain_modules()


def ow05_state(state):
    if state.get('sources')!=product.sources():
        raise ValueError('PRODUCTION_DRAFT_RESTORE_PRODUCT_SOURCE_CHANGED')
    return previous_recovery.ow05_state(state['predecessor'])


def _capture(cur):
    return consumer.owning._source_trigger_capture(cur,consumer.triggers)


def export_manifest(cur,state,patch_state):
    """Keep the SHARE-lock transaction open until the caller's full dump ends."""
    chain_modules()
    identity=catalog._authority(cur)
    catalog._lock_tables(cur)
    # This is a new declared composition. Never ask an old product verifier
    # to accept a projected/fake catalog after the delta has been installed.
    admission=state.get('current_installation_admission',{})
    receipt=admission.get('receipt',{})
    if(admission.get('sha256')!=installation.inventory.digest(receipt)
       or receipt.get('sources')!=installation.sources()
       or receipt.get('before')!=receipt.get('after')
       or patch_state['before']!=state['after']):
        raise ValueError('DRAFT_RESTORE_PREDECESSOR_BINDING_CHANGED')
    delta.verify(cur,patch_state)
    installed=ow05_state(state)['predecessor']['predecessor']['consumer']
    manifest=consumer.consumer_trigger_manifest()
    if manifest!=installed['source_trigger_manifest']:
        raise ValueError('DRAFT_RESTORE_DECLARED_CONSUMER_TRIGGER_SOURCE_CHANGED')
    capture=_capture(cur)
    consumer.triggers.verify_unchanged(capture,installed['source_trigger_after'],manifest,PHASE)
    result=dict(contract_version=VERSION,source_identity=identity,sources=sources(),
        phase=PHASE,excluded_schemas=catalog.EXCLUDED,
        catalog=catalog._catalog_rows(cur),data=catalog._data(cur))
    if len(result['catalog'])!=22:
        raise ValueError('DRAFT_RESTORE_COMPLETE_CATALOG_GROUP_SET_CHANGED')
    return result,catalog.digest(result)


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    """Only an exact source-bound fresh restore may receive its local OID seal."""
    chain_modules()
    if not isinstance(expected_sha256,str)or catalog.digest(backup)!=expected_sha256:
        raise ValueError('DRAFT_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    if(backup.get('contract_version')!=VERSION or backup.get('sources')!=sources()
       or backup.get('phase')!=PHASE or backup.get('excluded_schemas')!=catalog.EXCLUDED):
        raise ValueError('DRAFT_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    identity=catalog._authority(cur)
    if identity['database']!=expected_database or identity['database_oid']==backup['source_identity']['database_oid']:
        raise ValueError('DRAFT_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    catalog._lock_tables(cur)
    actual=catalog._catalog_rows(cur)
    wanted=catalog._portable(backup['catalog'])
    observed=catalog._portable(actual)
    if len(actual)!=22 or observed!=wanted:
        changes={kind:sorted(key for key in set(observed.get(kind,{}))|set(wanted.get(kind,{}))
            if observed.get(kind,{}).get(key)!=wanted.get(kind,{}).get(key))
            for kind in set(observed)|set(wanted)if observed.get(kind)!=wanted.get(kind)}
        raise ValueError('DRAFT_RESTORE_CATALOG_CHANGED: '+catalog.canonical(changes))
    body=cur.execute('select prosrc from pg_proc where oid=%s::regprocedure',(delta.SIGNATURE,)).fetchone()[0]
    if body!=delta.bodies()[1]:raise ValueError('DRAFT_RESTORE_DELTA_DEFINITION_CHANGED')
    before=catalog._data(cur)
    if before!=backup['data']:
        raise ValueError('DRAFT_RESTORE_BUSINESS_ROWS_OR_SEQUENCE_CHANGED')
    manifest=consumer.consumer_trigger_manifest()
    capture=_capture(cur)
    consumer.triggers.validate_source(capture,manifest,PHASE)
    expected=cur.execute('select cp7_credit.pg_jsonb_sha256(%s::jsonb)',
        (consumer.triggers.canonical(capture),)).fetchone()[0]
    rendered=consumer.triggers.render_runtime_guard(capture,manifest,PHASE,expected)
    cur.execute(rendered,prepare=False)
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    after=catalog._catalog_rows(cur)
    changed=sorted((kind,key)for kind in set(actual)|set(after)
        for key in set(actual.get(kind,{}))|set(after.get(kind,{}))
        if actual.get(kind,{}).get(key)!=after.get(kind,{}).get(key))
    if changed!=[('functions',catalog.GUARD)]:
        raise ValueError('DRAFT_RESTORE_UNDECLARED_BINDING_CATALOG_DELTA: '+catalog.canonical(changed))
    if actual['functions'][catalog.GUARD][1:]!=after['functions'][catalog.GUARD][1:]:
        raise ValueError('DRAFT_RESTORE_SEAL_PRIVILEGE_OR_METADATA_CHANGED')
    if catalog._data(cur)!=before:
        raise ValueError('DRAFT_RESTORE_BINDING_CHANGED_BUSINESS_DATA')
    return dict(contract_version='ow15.draft-return-isolation.verified-restore-binding.v1',
        trusted_backup_sha256=expected_sha256,fresh_database_verified=True,
        all_rows_and_sequences_equal=True,all22_portable_catalog_groups_equal=True,
        changed_functions=[catalog.GUARD],local_raw_oid_census_enforced=True,
        runtime_capture_sha256_pg=expected,chain_depth_to_ow05=DEPTH+2,production_go=False)
