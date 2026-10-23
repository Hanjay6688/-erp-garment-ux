"""Stateless bounded input pre-use inverse plus exact unchanged nine-stage oracle."""
import cp7_history_bounded as stage
from cp7_ow04_restore_bundle import _catalog_rows


def install_stage(cur):
    before = _catalog_rows(cur)
    state = stage.install_delta(cur)
    stage.admit_catalog(before, _catalog_rows(cur), state)
    stage.rollback_preuse(cur, state)
    assert _catalog_rows(cur) == before, 'BOUNDED_INPUT_PREUSE22_NOT_EXACT'
    state = stage.install_delta(cur)
    stage.admit_catalog(before, _catalog_rows(cur), state)
    return state, dict(stage.verify(cur, state), preuse_22_groups_exactly_restored=True, source_sha256=stage.sources())


def verify_composed(cur, legacy_checker, state):
    stage.verify(cur, state)
    current = _catalog_rows(cur)
    cur.execute('savepoint bounded_history_legacy_oracle')
    try:
        stage.rollback_preuse(cur, state)
        legacy_checker(cur)
    finally:
        cur.execute('rollback to savepoint bounded_history_legacy_oracle')
        cur.execute('release savepoint bounded_history_legacy_oracle')
    assert _catalog_rows(cur) == current, 'BOUNDED_INPUT_LEGACY22_NOT_RESTORED'
    return stage.verify(cur, state)


if __name__ == '__main__':
    import cp7_f05_analysis_probe as probe

    def runtime(browser_mode=False):
        return probe.run(wa_forward=True, ow14b_rules=True, ow13a_initial=True,
                         ow10_supply=True, ow10_reorder=True, ow13c_checked=True,
                         ow13c_history_inputs=True)

    probe.package._writer_runtime = runtime
    probe.package.run('install')
