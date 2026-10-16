"""Pre-U table inventory for the frozen X admission step after the AC writer artifact expired.

The frozen step "Apply v2.6.20x fail-closed internal role before every final-runtime proof" (frozen workflow at
1bdca376) reads cp6-proof/CP6_V2620U_FAILED150_PREDICATES.json and uses only the [schema, name] of its
baseline tables: the live erp table set after X must equal that pre-U set plus the U, V and W rollback capsules,
with 208 baseline tables (207 erp, 1 supabase_migrations). Until 15 Oct 2026 the file came from the AC writer
artifact 10392910720 (run 34956212157 of 15 Sep), pinned by SHA-256 in cp6_ac_audit_bootstrap.reuse_bootstrap_input.
That artifact was kept 30 days and expired (HTTP 410 in runs 38721795013, 38721797914, 38721801271, 38721804060,
38721806508; logs kept); its producing workflow at 1bdca376 itself needs the expired artifact 10320611163, so it
cannot be rebuilt byte for byte.

When the archive is present the original, fully pinned path is used unchanged. When it is absent, the same frozen
function that produced the original file (scripts/cp6_v2620u_install_diagnostic.snapshot at the frozen checkout) is
run on this rebuild immediately before the frozen U apply step, and the file is written in the shape the X step
reads. The X step itself is not changed and still decides. Extra checks here, before U: the 208/207/1 counts and,
once pinned, the SHA-256 of the sorted [schema, name] list, so a later rebuild with another table set is refused
here instead of being compared with itself.
"""
from pathlib import Path
import hashlib, importlib.util, json, os

U_STEP = 'Apply v2.6.20u canonical material, reversal and owner-report business dates before every final-runtime proof'
NAME = 'CP6_V2620U_FAILED150_PREDICATES.json'
ARTIFACT_ID = 10392910720
PENDING = 'ARCHIVE_EXPIRED_PRE_U_CAPTURE_PENDING'
# SHA-256 of json.dumps(sorted([schema, name] for every baseline table)) captured before U on the frozen chain.
# First captures after the expiry, identical in three runs on 677a7b05 (CP7 CP17 Fixes 38724905951, CP7 Native Atomic Misc
# Correction 38724911818, CP7 Native Posted Cutting Reopen 38724908863), each followed by the unchanged X step passing.
NAMES_SHA256 = 'eb7f121d3b5fe5a6fc3c920fb88ddbcd64242580f0689f0459a1cb29cc169069'


def archive_available():
    path = os.environ.get('CP6_AC_WRITER_ARTIFACT')
    return bool(path) and Path(path).is_file() and Path(path).stat().st_size > 0


def bootstrap_input(ac, proof):
    """The original pinned reuse when the archive exists; otherwise a pending marker resolved before U."""
    if archive_available():
        return ac.reuse_bootstrap_input(proof)
    assert not (proof / NAME).exists(), 'PRE_U_INVENTORY_ALREADY_PRESENT'
    return {'status': PENDING, 'artifact_id': ARTIFACT_ID, 'artifact_state': 'EXPIRED_2026_10_15',
            'path': NAME, 'capture_before_step': U_STEP, 'historical_test_reexecuted': False, 'production_go': False}


def names_digest(tables):
    return hashlib.sha256(json.dumps(sorted([schema, name] for schema, name, *_ in tables)).encode()).hexdigest()


def capture_before(step_name, proof, reused):
    """Run the frozen snapshot on the live chain right before the frozen U apply step, once."""
    if step_name != U_STEP or reused.get('status') != PENDING:
        return reused
    import psycopg
    frozen = Path('scripts/cp6_v2620u_install_diagnostic.py')
    spec = importlib.util.spec_from_file_location('cp6_frozen_u_diagnostic', frozen)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with psycopg.connect(os.environ['PGURL']) as conn, conn.cursor() as cur:
        conn.read_only = True
        snapshot = module.snapshot(cur)
    tables = snapshot['tables']
    counts = (len(tables), sum(t[0] == 'erp' for t in tables), sum(t[0] == 'supabase_migrations' for t in tables))
    digest = names_digest(tables)
    assert counts == (208, 207, 1), ('PRE_U_TABLE_COUNTS_CHANGED', counts)
    if NAMES_SHA256 is not None:
        assert digest == NAMES_SHA256, ('PRE_U_TABLE_NAMES_CHANGED', digest)
    (proof / NAME).write_text(json.dumps({'baseline': snapshot, 'source': 'PRE_U_CAPTURE_IN_THIS_REBUILD',
                                          'frozen_function': str(frozen), 'artifact_id_expired': ARTIFACT_ID},
                                         indent=2) + '\n')
    result = dict(reused, status='PRE_U_CAPTURED_IN_THIS_REBUILD', tables=counts[0], erp_tables=counts[1],
                  platform_tables=counts[2], names_sha256=digest, names_sha256_pinned=NAMES_SHA256,
                  frozen_function_sha256=hashlib.sha256(frozen.read_bytes()).hexdigest())
    print(json.dumps(dict(group='CP6_PRE_U_INVENTORY', **result)), flush=True)
    return result


def finished(reused, steps):
    """Stop-aware (Astra ASTRA-C17-06, Sol SOL-R1-003): a chain that passed U must have resolved the pending marker; a
    chain that stopped before U never needed the inventory, so it is recorded as not applicable instead of demanded."""
    if not any(step.get('name') == U_STEP for step in steps):
        return dict(reused, status='NOT_APPLICABLE_STOPPED_BEFORE_U') if reused.get('status') == PENDING else reused
    assert reused.get('status') != PENDING, 'PRE_U_INVENTORY_NOT_CAPTURED'
    return reused
