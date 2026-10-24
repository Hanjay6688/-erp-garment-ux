"""Install consumer/provenance overlays only on disposable browser copy."""
if __name__=='__main__':
    import psycopg
    from urllib.parse import urlparse
    import cp7_f05_analysis_probe as probe
    import cp7_ow11_analog_provenance_cases as native
    import cp7_ow13a_clone_authority as copies
    original_copy,original_setup=probe.modes.copy_db,probe.modes.setup_copy

    def setup(url,verify,test_only_usage):
        assert urlparse(url).path=='/cp6_auditor_browser'
        result=original_setup(url,verify,test_only_usage)
        with psycopg.connect(url)as conn,conn.cursor()as cur:
            native.PARENT_CHECKER=verify
            _,_,_,_,state=native.install(cur)
            result['runtime']=dict(parent=result['runtime'],provenance=native.stage.verify(cur,state),
              consumer_source_sha256=native.consumer.stage.sources(),provenance_source_sha256=native.stage.sources())
            conn.commit()
        return result

    def runtime(browser_mode=False):
        probe.modes.copy_db=lambda name:copies.copied_with_authority(
          original_copy,name,probe.OUT.parent/'CP7_OW11_ANALOG_CONSUMER_BROWSER_CLONE_AUTHORITY.json')
        probe.modes.setup_copy=setup
        try:
            return probe.run(wa_forward=True,ow14b_rules=True,ow13a_initial=True,
              ow10_supply=True,ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,
              ow13c_history_reference=True,ow13c_bounded_stage=True,ow11_analog_choice=True,
              ow11_analog_consumer=True,ow11_analog_provenance=True,ow11_consumer_browser=True)
        finally:probe.modes.copy_db,probe.modes.setup_copy=original_copy,original_setup
    probe.package._writer_runtime=runtime
    probe.package.run('install')
