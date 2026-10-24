"""Full source-bound recovery for corrected ERP plus immutable analog choices.

All22 catalog groups, all rows and all sequences must match the trusted full
backup before the sole existing Native OID seal is regenerated. No connection,
commit, current database restore, projected catalog or business-row rewrite.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_analog_installation as installation
import cp7_draft_return_recovery as previous

CONTRACT='cp7.current-AB-return-analog.offline-full-backup.v1'
catalog=installation.catalog
consumer=previous.consumer


def sources():
    return dict(contract=CONTRACT,current_installation=installation.sources(),
        qualified_trigger_recovery_sources=previous.sources(),
        recovery_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def export_manifest(cur,state):
    """Keep these SHARE locks held until the caller finishes the complete dump."""
    previous.chain_modules()
    identity=catalog._authority(cur)
    catalog._lock_tables(cur)
    installation.verify(cur,state)
    current=state['predecessor']['predecessor']
    installed=previous.ow05_state(current)['predecessor']['predecessor']['consumer']
    manifest=consumer.consumer_trigger_manifest()
    if manifest!=installed['source_trigger_manifest']:
        raise ValueError('ANALOG_RESTORE_DECLARED_NATIVE_TRIGGER_SOURCE_CHANGED')
    capture=previous._capture(cur)
    consumer.triggers.verify_unchanged(capture,installed['source_trigger_after'],manifest,previous.PHASE)
    backup=dict(contract=CONTRACT,sources=sources(),source_identity=identity,
        phase=previous.PHASE,excluded_schemas=catalog.EXCLUDED,
        catalog=catalog._catalog_rows(cur),data=catalog._data(cur))
    if len(backup['catalog'])!=22:raise ValueError('ANALOG_RESTORE_FULL22_REQUIRED')
    return backup,catalog.digest(backup)


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    previous.chain_modules()
    if not isinstance(expected_sha256,str)or catalog.digest(backup)!=expected_sha256:
        raise ValueError('ANALOG_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    if(backup.get('contract')!=CONTRACT or backup.get('sources')!=sources()
       or backup.get('phase')!=previous.PHASE or backup.get('excluded_schemas')!=catalog.EXCLUDED):
        raise ValueError('ANALOG_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    identity=catalog._authority(cur)
    if identity['database']!=expected_database or identity['database_oid']==backup['source_identity']['database_oid']:
        raise ValueError('ANALOG_RESTORE_FRESH_EXPECTED_DATABASE_REQUIRED')
    catalog._lock_tables(cur)
    actual=catalog._catalog_rows(cur)
    if len(actual)!=22 or catalog._portable(actual)!=catalog._portable(backup['catalog']):
        raise ValueError('ANALOG_RESTORE_CATALOG_CHANGED')
    body=cur.execute('select prosrc from pg_proc where oid=%s::regprocedure',
        (installation.predecessor.delta.SIGNATURE,)).fetchone()[0]
    if body!=installation.predecessor.delta.bodies()[1]:
        raise ValueError('ANALOG_RESTORE_RETURN_DELTA_CHANGED')
    before=catalog._data(cur)
    if before!=backup['data']:raise ValueError('ANALOG_RESTORE_ROWS_OR_SEQUENCES_CHANGED')
    manifest=consumer.consumer_trigger_manifest()
    capture=previous._capture(cur)
    consumer.triggers.validate_source(capture,manifest,previous.PHASE)
    expected=cur.execute('select cp7_credit.pg_jsonb_sha256(%s::jsonb)',
        (consumer.triggers.canonical(capture),)).fetchone()[0]
    cur.execute(consumer.triggers.render_runtime_guard(capture,manifest,previous.PHASE,expected),prepare=False)
    cur.execute('select cp7_credit.assert_source_native_trigger_census_v1()')
    after=catalog._catalog_rows(cur)
    changed=sorted((group,key)for group in set(actual)|set(after)
        for key in set(actual.get(group,{}))|set(after.get(group,{}))
        if actual.get(group,{}).get(key)!=after.get(group,{}).get(key))
    if changed!=[('functions',catalog.GUARD)]:
        raise ValueError('ANALOG_RESTORE_UNDECLARED_CATALOG_DELTA: '+catalog.canonical(changed))
    if actual['functions'][catalog.GUARD][1:]!=after['functions'][catalog.GUARD][1:]:
        raise ValueError('ANALOG_RESTORE_SEAL_AUTHORITY_CHANGED')
    if catalog._data(cur)!=before:raise ValueError('ANALOG_RESTORE_CHANGED_BUSINESS_DATA')
    return dict(contract=CONTRACT,status='EXACT_CURRENT_ANALOG_FULL_RESTORE_BOUND',
        trusted_backup_sha256=expected_sha256,fresh_database_verified=True,
        all_rows_and_sequences_equal=True,all22_portable_catalog_groups_equal=True,
        analog_choices_and_receipts_preserved=True,changed_functions=[catalog.GUARD],
        local_raw_oid_census_enforced=True,runtime_capture_sha256_pg=expected,
        production_go=False,independent_acceptance=False)
