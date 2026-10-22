"""P21 administrative entry point for the complete current OW04 owner.

The caller owns the transaction. No connection, commit, provider, schedule or
production admission happens on import or through installation.
"""
from hashlib import sha256
from pathlib import Path

import cp7_payment_source_owning_install as owner
import cp7_payment_source_restore as recovery

ROOT=Path(__file__).resolve().parents[1]


def sources():
    return dict(financial_product=owner.sources(),administrative_restore=recovery.sources(),
        adapter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        default_P21_entrypoint_sha256=sha256((ROOT/'scripts/cp7_p21_full_rehearsal_probe.py').read_bytes()).hexdigest())


def install(cur):return owner.install(cur)


def verify(cur,state):return owner.verify(cur,state)


def rollback_preuse(cur,state):return owner.rollback_preuse(cur,state)


def export_manifest(cur,state):return recovery.export_manifest(cur,state)


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    return recovery.rebind_restored(cur,backup,expected_sha256,expected_database=expected_database)
