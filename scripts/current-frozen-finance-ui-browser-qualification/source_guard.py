from pathlib import Path
import importlib.util,json,ast
REQUIRED={
 'scripts/cp7_current_frozen_finance_ui/browser.mjs':[
  "assert.equal(result.readiness,mobile?'BLOCKED':'READY')",
  "assert.equal(result.metrics.length,24)",
  "assert.ok(unknown.every(m=>!Object.hasOwn(m.value,'value')))",
  "assert.deepEqual(after.original,exact.original)",
  "assert.deepEqual(after.page_set,exact.page_set)",
  "assert.deepEqual(state(),readyState)",
  "assert.ok(calls.every(c=>c.millis<8000))",
  "rows.every(x=>x.ratio>=4.5)",
  "assert.equal(replay.status,403)",
  "await route.abort('failed')",
  "await route.fulfill({response})",
  "assert.equal(f.source_preparation.after.status,'READY')",
  "assert.equal(f.source_preparation.readiness_rules_unchanged,true)",
  "assert.equal(f.source_preparation.report_output_not_fabricated,true)",
 ],
 'scripts/cp7_current_frozen_finance_ui/browser_fixture.py':[
  "u.path=='/cp6_auditor_browser'",
  "set local statement_timeout='8s'",
  "'BASELINE_OFFICIAL_REPORT_NOT_READY'",
  "original['financial_source'] is None",
  "helpers.ready(cur,key,actor)",
  'private_SQL_advancement_only=True',
  'helpers.chain.prepare_attendance_pools(cur,today)',
  'helpers.chain.period.aw.quiet_seed(cur,start,today)',
 ],
}
def check(repo,here,overrides=None):
    overrides=overrides or {}
    p=repo/'scripts/cp7_current_frozen_finance_ui/verify_sources.py'
    spec=importlib.util.spec_from_file_location('A_finance_UI_exact_inputs',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    exact=m.check()
    for path,requirements in REQUIRED.items():
        text=overrides.get(path,(repo/path).read_text())
        for required in requirements:
            expected=2 if required=='assert.deepEqual(state(),readyState)' else 1
            assert text.count(required)==expected,(path,required,expected,text.count(required))
        if path.endswith('.py'):ast.parse(text)
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert len(cfg['case_ids'])==len(set(cfg['case_ids']))==2
    probe=(here/'probe.py').read_text()
    assert "report['observed_case_count']==2 and len(copies.COPY_ADMISSIONS)==2" in probe
    for required in ['product.verify(cur,STATE)','product.rollback_preuse(cur,STATE)','previous.restore_state.prove','advisor_delta','group.get(\'database_remaining\')==0']:
        assert required in probe,required
    return dict(exact,source_business_guards=sum(map(len,REQUIRED.values())),separate_full_clones=2,actual_browser_executed=False)
