"""Opt-in read-only stage and actual Auth UI; not a default installer."""
import cp7_product_analog_reader_stage as stage
from cp7_ow04_restore_bundle import _catalog_rows


def install_stage(cur,legacy_checker):
    before=_catalog_rows(cur)
    state=stage.install_delta(cur,legacy_checker)
    stage.rollback_readonly(cur,state)
    assert _catalog_rows(cur)==before,'ANALOG_READER_PREUSE22_NOT_EXACT'
    state=stage.install_delta(cur,legacy_checker)
    return state,dict(stage.verify(cur,state),preuse_22_groups_exactly_restored=True,
                      source_sha256=stage.sources(),kernel_manifest=stage.kernel.verify_sources())


def verify_composed(cur,legacy_checker,state):
    stage.verify(cur,state)
    current=_catalog_rows(cur)
    cur.execute('savepoint analog_reader_parent_oracle')
    try:
        stage.rollback_readonly(cur,state)
        legacy_checker(cur)
    finally:
        cur.execute('rollback to savepoint analog_reader_parent_oracle')
        cur.execute('release savepoint analog_reader_parent_oracle')
    assert _catalog_rows(cur)==current,'ANALOG_READER_PARENT22_NOT_RESTORED'
    return stage.verify(cur,state)


if __name__=='__main__':
    import cp7_f05_analysis_probe as probe
    import cp7_ow13a_clone_authority as copies
    original_copy=probe.modes.copy_db

    def runtime(browser_mode=False):
        probe.modes.copy_db=lambda name:copies.copied_with_authority(
            original_copy,name,probe.OUT.parent/'CP7_OW11_ANALOG_BROWSER_CLONE_AUTHORITY.json')
        try:
            return probe.run(wa_forward=True,ow14b_rules=True,ow13a_initial=True,
                             ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
                             ow13c_history_inputs=True,ow13c_history_reference=True,
                             ow13c_bounded_stage=True,ow11_analog_browser=True)
        finally:probe.modes.copy_db=original_copy

    probe.package._writer_runtime=runtime
    # The package records and asserts every gate itself; its success return is None.
    probe.package.run('install')
