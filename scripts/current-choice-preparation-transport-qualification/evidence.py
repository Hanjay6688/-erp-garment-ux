from pathlib import Path
from hashlib import sha256
import json

def validate(repo,here,proof,raw,product,parent):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    assert cfg['choice_head'] is not None,'ACTUAL_NATIVE6_PASS_REQUIRED_BEFORE_BINDING'
    assert proof['status']=='PASS'and proof['head']==cfg['choice_head']
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    d=json.loads(raw);declared=json.loads((repo/cfg['choice_declaration']).read_bytes())
    assert d['label']=='CP7_D17_18_CHOICE_NATIVE6'and d['status']=='PASS'
    assert d['qualification_commit']==proof['head']
    assert d['source_declaration']['qualification']==declared
    assert d['source_declaration']['current_installation']==product.sources()
    assert d['source_declaration']['qualified_public_parent']==parent
    assert parent['current_installation']==product.predecessor.predecessor.sources()
    for path,digest in declared['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert d['native']['counts']=={'PASS':6}
    assert d['observed_case_count']==d['expected_case_count']==6
    assert d['required_case_ids']==declared['case_ids']and set(d['native']['cases'])==set(declared['case_ids'])
    for case in d['native']['cases'].values():
        assert case['status']=='PASS'and case['full_boundary_restored']and case['public_schema_unchanged']
        assert all(v in(0,[],{})for v in case.get('session_leaks',{}).values())
    for key in ('required_case_ids_pass','cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
        assert d[key]is True,key
    assert d['complete_preuse_removal']and d['production_go']is d['independent_acceptance']is False
    return dict(proof,actual_choice_native6_verified=True)
