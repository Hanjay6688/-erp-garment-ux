"""Opt-in Native6 for immutable prospective model evaluation v2."""
if __name__=='__main__':
    import cp7_f05_analysis_probe as probe

    def runtime(browser_mode=False):
        return probe.run(wa_forward=True,ow14b_rules=True,ow13a_initial=True,
          ow10_supply=True,ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,
          ow13c_history_reference=True,ow13c_bounded_stage=True,ow11_model_policy=True,
          ow11_model_evaluation_v2=True)

    probe.package._writer_runtime=runtime
    probe.package.run('install')
