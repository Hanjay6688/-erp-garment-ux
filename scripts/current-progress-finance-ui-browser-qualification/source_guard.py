from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json

def check(repo,here,overrides=None):
    overrides=overrides or {}
    host=json.loads((here/'HOST_SOURCE.json').read_bytes())
    assert len(host['files'])==113
    for path,digest in host['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    p=repo/'scripts/cp7_current_progress_finance_ui/source_guard.py'
    spec=importlib.util.spec_from_file_location('exact_progress_host_source',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    exact=m.verify()
    origin=json.loads((here/'ORIGIN.json').read_bytes())
    assert sha256((here/'browser_fixture.py').read_bytes()).hexdigest()==origin['prior_runtime_source_files']['scripts/cp7_current_frozen_finance_ui/browser_fixture.py']
    required=json.loads((here/'BUSINESS_GUARDS.json').read_bytes())
    for path,guards in required.items():
        text=overrides.get(path,(repo/path).read_text())
        for guard in guards:
            expected=2 if guard=='assert.deepEqual(state(),readyState)'else 1
            assert text.count(guard)==expected,(path,guard)
        if path.endswith('.py'):ast.parse(text)
    probe=(here/'probe.py').read_text()
    for guard in ["report['observed_case_count']==2 and len(copies.COPY_ADMISSIONS)==2",'product.verify(cur,STATE)','product.rollback_preuse(cur,STATE)','previous.restore_state.prove','advisor_delta',"group.get('database_remaining')==0"]:
        assert guard in probe,guard
    return dict(exact,host_exact_files=113,business_guards=sum(map(len,required.values())),separate_full_clones=2,actual_browser_executed=False)
