"""Seven real scoped-model Auth/concurrency controls; separate from Native6."""
if __name__ == '__main__':
    import cp7_f05_analysis_probe as probe
    import cp7_ow13a_clone_authority as copies
    original_copy = probe.modes.copy_db

    def runtime(browser_mode=False):
        probe.modes.copy_db = lambda name: copies.copied_with_authority(
            original_copy, name,
            probe.OUT.parent / 'CP7_OW11_MODEL_SCOPED_EVALUATION_TRANSPORT_CLONE_AUTHORITY.json')
        try:
            return probe.run(wa_forward=True, ow14b_rules=True, ow13a_initial=True,
                ow10_supply=True, ow10_reorder=True, ow13c_checked=True,
                ow13c_history_inputs=True, ow13c_history_reference=True,
                ow13c_bounded_stage=True, ow11_model_history_runtime=True,
                ow11_model_scoped_evaluation=True, ow11_model_scoped_transport=True)
        finally:
            probe.modes.copy_db = original_copy

    probe.package._writer_runtime = runtime
    probe.package.run('install')
