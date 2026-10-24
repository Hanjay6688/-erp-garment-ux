"""Source-bound recovery envelope for the composed corrected current install.

The unchanged qualified draft-return recovery still proves the full fresh
backup and changes only its single Native OID seal. This envelope additionally
binds the composed entrypoint and this adapter; it never projects metadata.
"""
from hashlib import sha256
from pathlib import Path
import cp7_current_return_installation as installation
import cp7_draft_return_recovery as recovery

CONTRACT='cp7.current-AB-draft-return.full-backup.v1'
catalog=recovery.catalog


def sources():
    return dict(contract=CONTRACT,current_installation=installation.sources(),
        qualified_recovery=recovery.sources(),adapter_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


def export_manifest(cur,state):
    """Hold the resulting SHARE locks until the caller finishes its full dump."""
    installation.verify(cur,state)
    backup,digest=recovery.export_manifest(cur,state['predecessor'],state['delta'])
    envelope=dict(contract=CONTRACT,sources=sources(),product_backup=backup,product_backup_sha256=digest)
    return envelope,catalog.digest(envelope)


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    if not isinstance(expected_sha256,str)or catalog.digest(backup)!=expected_sha256:
        raise ValueError('CURRENT_RETURN_RESTORE_TRUSTED_BACKUP_HASH_REQUIRED')
    if backup.get('contract')!=CONTRACT or backup.get('sources')!=sources():
        raise ValueError('CURRENT_RETURN_RESTORE_SOURCE_OR_CONTRACT_CHANGED')
    receipt=recovery.rebind_restored(cur,backup['product_backup'],backup['product_backup_sha256'],
        expected_database=expected_database)
    return dict(contract=CONTRACT,trusted_composed_backup_sha256=expected_sha256,
        composed_entrypoint_and_recovery_sources_verified=True,qualified_binding=receipt,
        production_go=False,independent_acceptance=False)
