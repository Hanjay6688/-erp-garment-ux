"""Six new actual checked-save cases plus the retained Native19 caller cases."""
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_cutting_checked_save as checked


def install_stage(cur):
    before = _catalog_rows(cur)
    state = checked.install_delta(cur)
    checked.admit_catalog(before, _catalog_rows(cur), state)
    checked.rollback_preuse(cur, state)
    assert _catalog_rows(cur) == before, 'OW13C_PREUSE_22_NOT_EXACT'
    state = checked.install_delta(cur)
    checked.admit_catalog(before, _catalog_rows(cur), state)
    return state, dict(checked.verify(cur, state), preuse_22_groups_exactly_restored=True,
                       source_sha256=checked.sources())


def verify_composed(cur, legacy_checker, state):
    checked.verify(cur, state)
    current = _catalog_rows(cur)
    cur.execute('savepoint checked_save_legacy_oracle')
    try:
        checked.rollback_preuse(cur, state)
        legacy_checker(cur)
    finally:
        cur.execute('rollback to savepoint checked_save_legacy_oracle')
        cur.execute('release savepoint checked_save_legacy_oracle')
    assert _catalog_rows(cur) == current, 'OW13C_LEGACY_ORACLE_22_NOT_RESTORED'
    return checked.verify(cur, state)


if __name__ == '__main__':
    import cp7_f05_analysis_probe as probe
    import cp7_ow13a_clone_authority as copies
    original_copy = probe.modes.copy_db

    def runtime(browser_mode=False):
        probe.modes.copy_db = lambda name: copies.copied_with_authority(
            original_copy, name, probe.OUT.parent/'CP7_OW13C_CHECKED_SAVE_CLONE_AUTHORITY.json')
        try:
            return probe.run(wa_forward=True, ow14b_rules=True, ow13a_initial=True,
                             ow10_supply=True, ow10_reorder=True, ow13c_checked=True)
        finally:
            probe.modes.copy_db = original_copy

    probe.package._writer_runtime = runtime
    probe.package.run('install')
