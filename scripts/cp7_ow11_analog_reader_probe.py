"""Qualify the opt-in advisory facade on the strict twelve-stage parent."""
if __name__=='__main__':
    import cp7_f05_analysis_probe as probe

    def runtime(browser_mode=False):
        return probe.run(wa_forward=True,ow14b_rules=True,ow13a_initial=True,
                         ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
                         ow13c_history_inputs=True,ow13c_history_reference=True,
                         ow13c_bounded_stage=True,ow11_analog_reader=True)

    probe.package._writer_runtime=runtime
    # The package records and asserts every gate itself; its success return is None.
    probe.package.run('install')
