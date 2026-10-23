"""One retained anchor + actual SAVE2000 in a committed, single-session clone."""
def committed_group(provider,checker,phase):
    import cp6_auditor_modes as modes
    raw=modes.run_races(provider,checker,phase+'_committed_scale')
    # The unchanged runner is used for commit-capable isolated setup only.
    # Keep the real case result; do not award any concurrency/race coverage.
    raw['cases']=raw.pop('races')
    raw['planned_case_ids']=raw.pop('planned_race_ids',[])
    raw['copy_per_committed_case']=raw.pop('copy_per_race',True)
    raw.update(mode='COMMITTED_SCALE_SINGLE_SESSION',concurrency_test=False,race_case_credit=0)
    return raw


if __name__=='__main__':
    import cp7_f05_analysis_probe as probe
    import cp7_ow13a_clone_authority as copies
    original_copy=probe.modes.copy_db

    def runtime(browser_mode=False):
        probe.modes.copy_db=lambda name:copies.copied_with_authority(
            original_copy,name,probe.OUT.parent/'CP7_OW13C_BOUNDED_SAVE_CLONE_AUTHORITY.json')
        try:
            return probe.run(wa_forward=True,ow14b_rules=True,ow13a_initial=True,
                             ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
                             ow13c_history_inputs=True,ow13c_history_reference=True,
                             ow13c_bounded_stage=True,ow13c_bounded_save=True)
        finally:
            probe.modes.copy_db=original_copy

    probe.package._writer_runtime=runtime
    probe.package.run('install')
