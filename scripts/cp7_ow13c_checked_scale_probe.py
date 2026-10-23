"""Focused Native2: one repeated anchor plus actual checked SAVE2000 timing."""
if __name__ == '__main__':
    import cp7_f05_analysis_probe as probe

    def runtime(browser_mode=False):
        return probe.run(wa_forward=True, ow14b_rules=True, ow13a_initial=True,
                         ow10_supply=True, ow10_reorder=True, ow13c_checked=True,
                         ow13c_scale=True)

    probe.package._writer_runtime = runtime
    probe.package.run('install')
