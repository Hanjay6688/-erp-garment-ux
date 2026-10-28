"""The exact previous diagnostic is necessary but is not performance acceptance."""
from pathlib import Path
from hashlib import sha256
import json
HEAD='7caf6b84a357ab670ac0e4c0c190fadb2738c2e7'

def validate(repo,proof,raw,product,parent):
    assert proof['head']==HEAD and proof['status']=='PASS'
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    d=json.loads(raw);declared=json.loads((repo/'scripts/current-finance-reader-diagnostic/SOURCE.json').read_bytes())
    assert d['label']=='CP7_D17_18_FINANCE_READER_DIAGNOSTIC1'and d['status']=='PASS'
    assert d['qualification_commit']==HEAD
    assert d['source_declaration']['qualification']==declared
    assert d['source_declaration']['current_installation']==product.sources()
    assert d['source_declaration']['retained_admission']==parent
    for path,digest in declared['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    for key in ('required_case_ids_pass','cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','used_guard_refused_before_DDL'):
        assert d[key]is True,key
    assert d['complete_preuse_removal']and d['production_go']is d['independent_acceptance']is False
    assert d['observed_case_count']==d['expected_case_count']==len(d['committed'])==1
    c=next(iter(d['committed'].values()));assert c['status']=='PASS'
    assert set(c['pairs'])=={'SMALL','FACTORY_1200X3'}
    for name,pair in c['pairs'].items():
        assert pair['status']=='PASS'and pair['entire_official_report_equal']
        old,new=pair['unchanged_official'],pair['readonly_opening_candidate']
        assert old['report_sha256']==new['report_sha256']and old['rows']==new['rows']
        assert new['table_write_attempts']=={}and new['all_data_and_sequences_unchanged_before_rollback']
        assert old['all22_all_data_and_sequences_restored']and new['all22_all_data_and_sequences_restored']
    assert c['pairs']['FACTORY_1200X3']['unchanged_official']['table_write_attempts']['erp.opening_balance_items']==[0,10800,0]
    return dict(proof,actual_reader_diagnostic_verified=True,performance_qualification=False)
