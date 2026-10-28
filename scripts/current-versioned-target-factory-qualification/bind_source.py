"""Bind three exact Originals; never replace the failed factory receipt by PASS."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,importlib.util,json
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def bind(args):
    assert not(HERE/'SOURCE.json').exists(),'SOURCE_ALREADY_BOUND'
    c=json.loads((HERE/'CONFIG.json').read_bytes());rows=json.loads(Path(args.bindings).read_bytes())
    assert set(rows)=={c['native_variable'],c['cron_variable'],c['first_failure_variable']}
    spec=importlib.util.spec_from_file_location('versioned_factory_guard',HERE/'source_guard.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);g.source_binding()
    proofs={};actuals={}
    for variable,row in rows.items():
        proof=json.loads(Path(row['proof']).read_bytes());raw=Path(row['original']).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw);failed=variable==c['first_failure_variable']
        assert actual['status']==proof['status']==('INCOMPLETE'if failed else'PASS')and actual['cp6_restored']and actual['advisor_gate']
        expected=c['old_head']if failed else(args.expected_native_head if variable==c['native_variable']else args.expected_cron_head)
        assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']==expected
        proofs[variable]=proof;actuals[variable]=actual
    n=actuals[c['native_variable']];cron=actuals[c['cron_variable']];old=actuals[c['first_failure_variable']]
    parent_path='scripts/current-versioned-target-native-qualification/SOURCE.json';cron_path='scripts/current-versioned-target-cron-qualification/SOURCE.json'
    parent=json.loads((REPO/parent_path).read_bytes());cron_source=json.loads((REPO/cron_path).read_bytes())
    assert n['source_declaration']['qualification']==parent and n['native']['counts']=={'PASS':36}and n['required_case_ids_pass']
    assert cron['source_declaration']['qualification']==cron_source and cron['status']=='PASS'and cron['actual_cron_claim']and cron['manual_steps']==0
    assert cron_source['actual_qualification_originals']['CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT']==proofs[c['native_variable']]
    assert old['source_declaration']['qualification']['files']['scripts/current-factory-finance-qualification/fixture.py']==c['fixture_sha256']
    tree=ast.parse((HERE/'runner.py').read_text());case=ast.literal_eval(next(x.value for x in tree.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='CASE'for t in x.targets)))
    files=set(parent['files'])|set(cron_source['files'])|{parent_path,cron_path,'.github/workflows/cp7-current-versioned-target-factory.yml'}
    files.update(str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file())
    pins=dict(contract=c['contract'],case_ids=[case],files={p:sha256((REPO/p).read_bytes()).hexdigest()for p in sorted(files)},actual_qualification_originals=proofs,production_go=False,independent_acceptance=False)
    with(HERE/'SOURCE.json').open('x')as f:f.write(json.dumps(pins,indent=2)+'\n')
    print(json.dumps(dict(status='SOURCE_BOUND',files=len(files),cases=1,actual_originals=3,failed_original_preserved=True)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in('bindings','expected-native-head','expected-cron-head'):parser.add_argument('--'+name,required=True)
    bind(parser.parse_args())
