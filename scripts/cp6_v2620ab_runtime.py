"""Pinned AB runtime and read-only historical edges for CP6 audit evidence.

Rollback admission continues to require the exact installed target. Historical
overlays below verify an explicit AB predecessor edge; they never authorize a
rollback of an older generation while AB remains installed.
"""
import hashlib
import os
import subprocess
from pathlib import Path

import cp6_preuse_rollback_maintenance as maintenance

STAMP = '20260914190500'
NAME = 'erp_v2_6_20ab_cp6_operational_business_clock'
MIGRATION = Path('supabase/migrations/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.sql')
ROLLBACK = Path('supabase/rollbacks/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.rollback.sql')
MIGRATION_SHA256 = '7b31f000b3ca89f4bc776d93f3211f39dce5adbc73445291b9c0e0268f2d7fe3'
ROLLBACK_SHA256 = '5602fefc1b29935ccfb485635ec14e6fdea7468bd726ed440d6c5d93d12b1262'
AA_HEAD = '7d824f780fa06fc16385c347759a9b96d0138e9d'
AA_TREE = '0bfda3d552a3a3c37b4563d895a9eb387f64acb4'


def verified_successor(cur):
    cur.execute("""select exists(select 1 from erp.schema_migrations
      where version='v2.6.20ab'), to_regclass('erp.cp6_v2620ab_rollback_capsule') is not null,
      exists(select 1 from supabase_migrations.schema_migrations where name=%s)""", (NAME,))
    marker, capsule, platform = cur.fetchone()
    if not marker and not capsule and not platform:
        return {}
    if not marker or not capsule or not platform:
        raise AssertionError('AB_MARKER_CAPSULE_PLATFORM_MISMATCH')
    data = MIGRATION.read_bytes()
    if hashlib.sha256(data).hexdigest() != MIGRATION_SHA256:
        raise AssertionError('AB_FROZEN_MIGRATION_BYTES_MISMATCH')
    cur.execute("""select version,encode(extensions.digest(convert_to(
      array_to_string(statements,E'\\n'),'UTF8'),'sha256'),'hex')
      from supabase_migrations.schema_migrations where name=%s""", (NAME,))
    rows = cur.fetchall()
    if len(rows) != 1 or rows[0][0] != STAMP or rows[0][1] not in {
        MIGRATION_SHA256, hashlib.sha256(data[:-1]).hexdigest(),
    }:
        raise AssertionError('AB_SOURCE_PLATFORM_MISMATCH')
    observations = maintenance._capsule_snapshot(cur.connection, 'AB', maintenance.TARGETS['AB'])
    return {item['identity']: item for item in observations}


def verify_extra_objects(cur):
    # AA, Z and Y's own capsule identities are unchanged by AB. Their checks
    # retain exact predecessor owner/ACL pins and all inherited private facts.
    import cp6_v2620aa_runtime as predecessor
    if len(predecessor.verified_successor(cur)) != 2:
        raise AssertionError('AB_REQUIRES_VERIFIED_AA')
    return predecessor.verify_extra_objects(cur)


def historical_overlay(cur, generation, immediate_successor):
    """Qualify non-overlapping AB edges without changing capsule cardinality."""
    successor = verified_successor(cur)
    expected = {item['identity']: item for item in maintenance.TRUSTED_FUNCTIONS[generation]}
    direct = {}
    for identity, item in successor.items():
        if identity not in expected:
            continue
        if item['predecessor_sha256'] != expected[identity]['installed_sha256']:
            raise AssertionError('AB_HISTORICAL_PREDECESSOR_EDGE_MISMATCH:' + identity)
        direct[identity] = item
    combined = dict(immediate_successor)
    for identity, item in direct.items():
        if identity in combined:
            raise AssertionError('AB_HISTORICAL_EDGE_MUST_BE_EXPLICIT:' + identity)
        combined[identity] = item
    return combined, direct


def extend_historical_items(direct, items):
    for item in items:
        newer = direct.get(item['identity'])
        if newer is None:
            continue
        if item['installed_sha256'] != newer['predecessor_sha256']:
            raise AssertionError('AB_HISTORICAL_ITEM_EDGE_MISMATCH')
        item['pre_ab_installed_sha256'] = item['installed_sha256']
        item['installed_sha256'] = newer['installed_sha256']
        item['effective_successor_generation'] = 'AB'


def verify_audit_source():
    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    if git('rev-parse', AA_HEAD + '^{tree}') != AA_TREE or git('merge-base', AA_HEAD, 'HEAD') != AA_HEAD:
        raise AssertionError('AB_AUDIT_REQUIRES_FROZEN_AA_ANCESTRY')
    if git('diff', '--name-only', '--diff-filter=MDRTCUXB', AA_HEAD, 'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks'):
        raise AssertionError('AB_AUDIT_ADMITTED_AA_SQL_CHANGED')
    changed = set(git('diff', '--name-only', AA_HEAD, 'HEAD', '--', 'supabase/migrations', 'supabase/rollbacks').splitlines())
    admitted = {str(MIGRATION), str(ROLLBACK)}
    if changed != admitted:
        # Historical AB audits also execute from an AC source checkout before
        # AC is installed. Admit only AC's two hash-pinned SQL additions; this
        # does not change the runtime phase or authorize any older rollback.
        import cp6_v2620ac_runtime as ac_runtime
        ac_additions = {str(ac_runtime.MIGRATION), str(ac_runtime.ROLLBACK)}
        if changed != admitted | ac_additions:
            raise AssertionError('AB_AUDIT_ONLY_EXACT_AB_OR_AC_ADDITIONS_ALLOWED')
        ac_runtime.verify_source_files()
    if hashlib.sha256(MIGRATION.read_bytes()).hexdigest() != MIGRATION_SHA256 or hashlib.sha256(ROLLBACK.read_bytes()).hexdigest() != ROLLBACK_SHA256:
        raise AssertionError('AB_AUDIT_SUCCESSOR_SQL_BYTES_CHANGED')
    head = git('rev-parse', 'HEAD')
    if os.environ.get('GITHUB_SHA') != head:
        raise AssertionError('AB_AUDIT_EXACT_NATIVE_CHECKOUT_REQUIRED')
    phase = os.environ.get('CP6_AB_PHASE', 'AA_AUDIT')
    if phase not in ('AA_AUDIT', 'AB_REGRESSION'):
        raise AssertionError('AB_AUDIT_UNKNOWN_PHASE')
    return phase, head, git('rev-parse', 'HEAD^{tree}')


def verify_audit_runtime(cur):
    phase = os.environ.get('CP6_AB_PHASE', 'AA_AUDIT')
    import cp6_v2620aa_runtime as predecessor
    if len(predecessor.verified_successor(cur)) != 2:
        raise AssertionError('AB_AUDIT_AA_BASE_REQUIRED')
    expected = 0 if phase == 'AA_AUDIT' else 5 if phase == 'AB_REGRESSION' else None
    found = verified_successor(cur)
    if expected is None or len(found) != expected:
        raise AssertionError('AB_AUDIT_PHASE_RUNTIME_MISMATCH')
    return found
