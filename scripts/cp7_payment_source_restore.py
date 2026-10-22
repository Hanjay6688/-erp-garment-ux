"""Offline full-backup binding for the complete current payment/consumer owner.

The caller owns the administrative transaction and the full dump/restore.
No connection, commit, public RPC, hosted access or production admission.
Every catalog member, row and sequence must match the trusted backup before
the one strict local-OID census can be regenerated for the fresh database.
"""
from hashlib import sha256
from pathlib import Path

import cp7_payment_source_owning_install as product
import cp7_ow04_restore_bundle as catalog

VERSION='ow04.payment-source.offline-full-backup.v1'
PHASE='OW04_CONSUMER_BOUNDED'
consumer=product.predecessor.consumer


def sources():
    return dict(financial_product=product.sources(),
        administrative_restore_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def _capture(cur):
    return consumer.owning._source_trigger_capture(cur,consumer.triggers)


def export_manifest(cur,state):
    """Keep the SHARE-lock transaction open until the caller's full dump ends."""
    identity=catalog._authority(cur)
    catalog._lock_tables(cur)
    product.verify(cur,state)
    installed=state['predecessor']['consumer']
    manifest=consumer.consumer_trigger_manifest()
    if manifest!=installed['source_trigger_manifest']:
        raise ValueError('PAYMENT_RESTORE_DECLARED_CONSUMER_TRIGGER_SOURCE_CHANGED')
    capture=_capture(cur)
    consumer.triggers.verify_unchanged(capture,installed['source_trigger_after'],manifest,PHASE)
    result=dict(contract_version=VERSION,source_identity=identity,sources=sources(),
        phase=PHASE,excluded_schemas=catalog.EXCLUDED,
        catalog=catalog._catalog_rows(cur),data=catalog._data(cur))
    if len(result['catalog'])!=22:
        raise ValueError('PAYMENT_RESTORE_COMPLETE_CATALOG_GROUP_SET_CHANGED')
    return result,catalog.digest(result)


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    """Only an exact source-bound fresh restore may receive its local OID seal."""
    if not isinstance(expected_sha256,str)or catalog.digest(backup)!=expected_sha256:
        raise ValueError('PAYMENT_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    if(backup.get('contract_version')!=VERSION or backup.get('sources')!=sources()
       or backup.get('phase')!=PHASE or backup.get('excluded_schemas')!=catalog.EXCLUDED):
        raise ValueError('PAYMENT_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    identity=catalog._authority(cur)
    if identity['database']!=expected_database or identity['database_oid']==backup['source_identity']['database_oid']:
        raise ValueError('PAYMENT_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    catalog._lock_tables(cur)
    actual=catalog._catalog_rows(cur)
    wanted=catalog._portable(backup['catalog'])
    observed=catalog._portable(actual)
    if len(actual)!=22 or observed!=wanted:
        changes={kind:sorted(key for key in set(observed.get(kind,{}))|set(wanted.get(kind,{}))
            if observed.get(kind,{}).get(key)!=wanted.get(kind,{}).get(key))
            for kind in set(observed)|set(wanted)if observed.get(kind)!=wanted.get(kind)}
        raise ValueError('PAYMENT_RESTORE_CATALOG_CHANGED: '+catalog.canonical(changes))
    before=catalog._data(cur)
    if before!=backup['data']:
        raise ValueError('PAYMENT_RESTORE_BUSINESS_ROWS_OR_SEQUENCE_CHANGED')
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
        raise ValueError('PAYMENT_RESTORE_UNDECLARED_BINDING_CATALOG_DELTA: '+catalog.canonical(changed))
    if actual['functions'][catalog.GUARD][1:]!=after['functions'][catalog.GUARD][1:]:
        raise ValueError('PAYMENT_RESTORE_SEAL_PRIVILEGE_OR_METADATA_CHANGED')
    if catalog._data(cur)!=before:
        raise ValueError('PAYMENT_RESTORE_BINDING_CHANGED_BUSINESS_DATA')
    return dict(contract_version='ow04.payment-source.verified-restore-binding.v1',
        trusted_backup_sha256=expected_sha256,fresh_database_verified=True,
        all_rows_and_sequences_equal=True,all22_portable_catalog_groups_equal=True,
        changed_functions=[catalog.GUARD],local_raw_oid_census_enforced=True,
        runtime_capture_sha256_pg=expected,production_go=False)
