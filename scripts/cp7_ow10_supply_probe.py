"""Private WIP producer/reader on real Native jobs, retaining every126 control.

Disposable database only. No default installer, cron, live ROP or real WA.
"""
if __name__ == '__main__':
    import cp7_b_f05_analysis_probe as probe
    import cp7_ow13a_clone_authority as copies
    original_copy = probe.modes.copy_db

    def runtime(browser_mode=False):
        probe.modes.copy_db = lambda name: copies.copied_with_authority(
            original_copy, name, probe.OUT.parent / 'CP7_OW10_CLONE_AUTHORITY.json')
        try:
            return probe.run(wa_forward=True, ow14b_rules=True,
                             ow13a_initial=True, ow10_supply=True)
        finally:
            probe.modes.copy_db = original_copy

    probe.package._writer_runtime = runtime
    probe.package.run('install')
