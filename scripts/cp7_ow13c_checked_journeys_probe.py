"""Native31: retain all Native25 controls, add checked-save races and UI recovery."""
if __name__ == '__main__':
    import cp7_b_f05_analysis_probe as probe
    import cp7_ow13a_clone_authority as copies
    original_copy = probe.modes.copy_db

    def runtime(browser_mode=False):
        probe.modes.copy_db = lambda name: copies.copied_with_authority(
            original_copy, name, probe.OUT.parent/'CP7_OW13C_CHECKED_JOURNEYS_CLONE_AUTHORITY.json')
        try:
            return probe.run(wa_forward=True, ow14b_rules=True, ow13a_initial=True,
                             ow10_supply=True, ow10_reorder=True, ow13c_checked=True, ow13c_journeys=True)
        finally:
            probe.modes.copy_db = original_copy

    probe.package._writer_runtime = runtime
    probe.package.run('install')
