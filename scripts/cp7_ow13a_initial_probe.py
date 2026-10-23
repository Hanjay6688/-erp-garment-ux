"""Native126 on the disposable stack; default installers remain with A."""
from cp7_ow04_restore_bundle import _catalog_rows
import cp7_initial_analysis_stage as initial
import cp7_target_policy_stage as target


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
