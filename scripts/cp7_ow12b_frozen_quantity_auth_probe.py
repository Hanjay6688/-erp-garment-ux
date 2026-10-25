"""Install frozen choice plus public request composition only on the disposable browser clone."""
if __name__=='__main__':
    import psycopg
    from urllib.parse import urlparse
    import cp7_f05_analysis_probe as probe
    import cp7_ow12b_frozen_choice_cases as native
    import cp7_ow12b_frozen_facade_cases as facade
    import cp7_ow13a_clone_authority as copies
    original_copy,original_setup=probe.modes.copy_db,probe.modes.setup_copy

    def setup(url,verify,test_only_usage):
        assert urlparse(url).hostname in('localhost','127.0.0.1')and urlparse(url).path=='/cp6_auditor_browser'
        result=original_setup(url,verify,test_only_usage)
        with psycopg.connect(url)as conn,conn.cursor()as cur:
            native.PARENT_CHECKER=verify;s=native.install(cur)
            public=facade.stage.install_delta(cur,lambda c:native.stage.verify(c,s['current']))
            result['runtime']=dict(parent=result['runtime'],frozen_choice_installed=native.stage.verify(cur,s['current']),frozen_choice_source_sha256=native.sources(),frozen_public_facade=facade.stage.verify(cur,public),frozen_facade_source_sha256=facade.sources())
            conn.commit()
        return result

    def runtime(browser_mode=False):
        probe.modes.copy_db=lambda name:copies.copied_with_authority(original_copy,name,
          probe.OUT.parent/'CP7_OW12B_FROZEN_QUANTITY_AUTH_CLONE_AUTHORITY.json')
        probe.modes.setup_copy=setup
        try:
            return probe.run(wa_forward=True,ow14b_rules=True,ow13a_initial=True,
              ow10_supply=True,ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,
              ow13c_history_reference=True,ow13c_bounded_stage=True,ow11_model_history_runtime=True,
              ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_quantity_auth=True)
        finally:probe.modes.copy_db,probe.modes.setup_copy=original_copy,original_setup
    probe.package._writer_runtime=runtime
    probe.package.run('install')
