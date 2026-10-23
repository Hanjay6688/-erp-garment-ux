"""Focused Native caller qualification; Native133 is separate evidence."""
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_reorder_inputs as inputs
import cp7_reorder_reader_stage as reader
import cp7_reorder_caller_stage as caller

MODULES = [('inputs', inputs), ('reader', reader), ('caller', caller)]


def install_stages(cur):
    states, receipts = {}, {}
    for name, module in MODULES:
        before = _catalog_rows(cur)
        state = module.install_delta(cur)
        module.admit_catalog(before, _catalog_rows(cur), state)
        module.rollback_preuse(cur, state)
        assert _catalog_rows(cur) == before, 'OW10R_PREUSE_22_NOT_EXACT: '+name
        state = module.install_delta(cur)
        module.admit_catalog(before, _catalog_rows(cur), state)
        states[name] = state
        receipts[name] = dict(module.verify(cur, state), preuse_22_groups_exactly_restored=True,
                              source_sha256=module.sources())
    return states, receipts


def verify_composed(cur, legacy_checker, states):
    for name, module in MODULES:
        module.verify(cur, states[name])
    current = _catalog_rows(cur)
    cur.execute('savepoint reorder_legacy_oracle')
    try:
        for name, module in reversed(MODULES):
            module.rollback_preuse(cur, states[name])
        legacy_checker(cur)
    finally:
        cur.execute('rollback to savepoint reorder_legacy_oracle')
        cur.execute('release savepoint reorder_legacy_oracle')
    assert _catalog_rows(cur) == current, 'OW10R_LEGACY_CHECK_DID_NOT_RESTORE_ALL_22'
    for name, module in MODULES:
        module.verify(cur, states[name])
    return dict(caller='cp7.reorder-caller-stage.v1', exact_legacy_oracle_and_all_22_groups=True,
                full_A_chain_qualified=False, production_go=False)


if __name__ == '__main__':
    import cp7_b_f05_analysis_probe as probe
    import cp7_ow13a_clone_authority as copies
    original_copy = probe.modes.copy_db

    def runtime(browser_mode=False):
        probe.modes.copy_db = lambda name: copies.copied_with_authority(
            original_copy, name, probe.OUT.parent/'CP7_OW10_REORDER_CLONE_AUTHORITY.json')
        try:
            return probe.run(wa_forward=True, ow14b_rules=True, ow13a_initial=True,
                             ow10_supply=True, ow10_reorder=True)
        finally:
            probe.modes.copy_db = original_copy

    probe.package._writer_runtime = runtime
    probe.package.run('install')
