"""Native126 on the disposable stack; default installers remain with A."""
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_initial_analysis_stage as initial
import cp7_target_policy_stage as target


def verify_initial_delta(cur, legacy_checker, state):
    """Prove the unchanged legacy oracle plus the exact declared initial delta.

    The legacy WA verifier deliberately permits no unknown outside-schema
    EXECUTE grants. The new private tick is an explicit part of this stage,
    not an addition to the frozen installer's grant list. Check that oracle
    on the exact predecessor, using this stage's verified inverse in a
    savepoint; then require all 22 current catalogue groups to be restored.
    This is an empty-install gate, never a runtime rollback after an intent.
    """
    initial.verify(cur, state)
    current = _catalog_rows(cur)
    cur.execute('savepoint ow13a_legacy_oracle')
    try:
        initial.rollback_preuse(cur, state)
        legacy_checker(cur)
    finally:
        cur.execute('rollback to savepoint ow13a_legacy_oracle')
        cur.execute('release savepoint ow13a_legacy_oracle')
    if _catalog_rows(cur) != current:
        raise ValueError('OW13A_LEGACY_ORACLE_DID_NOT_RESTORE_ALL_22_GROUPS')
    initial.verify(cur, state)


def verify_composed_install(cur, legacy_checker, states):
    target.verify(cur, states['target'])
    verify_initial_delta(cur, legacy_checker, states['initial'])
    target.verify(cur, states['target'])


def install_stages(cur):
    states={};receipts={}
    for name,module in (('target',target),('initial',initial)):
        before=_catalog_rows(cur)
        state=module.install_delta(cur)
        module.admit_catalog(before,_catalog_rows(cur),state)
        module.rollback_preuse(cur,state)
        if _catalog_rows(cur)!=before:
            raise ValueError('OW13A_NATIVE_PREUSE_22_NOT_EXACTLY_RESTORED: '+name)
        state=module.install_delta(cur)
        module.admit_catalog(before,_catalog_rows(cur),state)
        states[name]=state
        receipts[name]=dict(module.verify(cur,state),preuse_22_groups_exactly_restored=True,
                            source_sha256=module.sources())
    return states,receipts


if __name__=='__main__':
    import cp7_f05_analysis_probe as probe
    probe.package._writer_runtime=lambda browser_mode=False:probe.run(wa_forward=True,ow14b_rules=True,ow13a_initial=True)
    probe.package.run('install')
