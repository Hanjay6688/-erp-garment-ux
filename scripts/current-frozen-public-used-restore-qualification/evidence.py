"""Complete current Native52 and full prior used restore8, without summary substitution."""
from pathlib import Path
from hashlib import sha256
import ast,json

def control_ids(source,function='controls'):
    tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==function);ids=[]
    for n in ast.walk(fn):
        if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='refused'and isinstance(n.args[0],ast.Constant):ids.append(n.args[0].value)
        if isinstance(n,ast.For)and isinstance(n.target,ast.Tuple)and isinstance(n.iter,ast.List):
            if any(isinstance(x,ast.Call)and isinstance(x.func,ast.Name)and x.func.id=='refused'and isinstance(x.args[0],ast.Name)for x in ast.walk(n)):
                ids.extend(row[0]for row in ast.literal_eval(n.iter))
    assert len(ids)==len(set(ids));return sorted(ids)

def validate_prior(repo,cfg,proof,d,product,steps):
    assert proof['head']==cfg['prior_head']
    assert d['label']=='CP7_CURRENT_VERSIONED_PERFORMANCE_USED_RESTORE8'
    assert d['source_declaration']['current_installation']==product.predecessor.predecessor.predecessor.sources()
    old=repo/'scripts/current-versioned-performance-used-restore-qualification'
    for p in old.iterdir():
        if p.is_file()and p.name!='SOURCE.json':
            rel=str(p.relative_to(repo));assert d['source_declaration']['qualification']['files'][rel]==sha256(p.read_bytes()).hexdigest(),rel
    assert d['required_steps_pass']and d['required_steps']==list(steps)
    assert len(d['steps'])==8 and [x['step']for x in d['steps']]==list(steps)
    assert all(x['status']=='PASS'for x in d['steps'])
    assert d['baseline_full22_all_rows_all_sequences_equal']and d['baseline_advisors_equal']
    ids=control_ids((old/'probe.py').read_text())+control_ids((old/'performance_controls.py').read_text(),'run')
    assert len(ids)==len(set(ids))==34
    controls=d['steps'][4]['controls'];assert len(controls)==34
    assert sorted(x['id']for x in controls)==sorted(ids)and all(x['status']=='PASS'for x in controls)
    assert d['steps'][2]['all_rows_sequences_and_full22_unchanged']and d['steps'][3]['all_table_hashes_equal']and d['steps'][5]['all_table_hashes_equal']
    for key,value in d['steps'][7].items():
        if isinstance(value,bool):assert value,key
    counts={k:len(v)for k,v in d.items()if k.endswith('_full_restore_checks')}
    assert counts==dict(finance_full_restore_checks=2,model_full_restore_checks=4,dated_target_full_restore_checks=4,scoped_history_full_restore_checks=8,scoped_model_full_restore_checks=8)
    for name in counts:
        for row in d[name]:
            for key,value in row.items():
                if isinstance(value,bool):
                    wanted=key!='forecast_applied'
                    if name=='scoped_model_full_restore_checks'and key=='policy_unchanged':wanted=row['label']not in('AFTER_POLICY_WITHDRAWAL','AFTER_NEXT_NATIVE_RETURN')
                    if name=='scoped_model_full_restore_checks'and key=='history_unchanged':wanted=not(row['label']=='AFTER_NEXT_NATIVE_RETURN'and row['scope']=='NATIVE_RETURN_TARGET')
                    assert value==wanted,(name,row.get('label'),key)
    assert all(x['all_header_and_item_fields_equal']for x in d['DRAFT_snapshot_checks'])
    check=d['dated_target_prebackup_check']
    assert check['label']=='BEFORE_USED_BACKUP'and check['current_source_state']=='UNCHANGED'
    for key in('exact_all_stored_columns_UTC','exact_old_target_provenance_and_model_input','only_current_source_state_separate','same_UUID_one_baseline_run','no_stock_money_HPP_write'):assert check[key]is True,key
    assert check['forecast_applied']is False

def validate(repo,here,proofs,actuals,product,steps):
    cfg=json.loads((here/'CONFIG.json').read_bytes());parent=json.loads((repo/cfg['native_path']).read_bytes())
    assert set(proofs)==set(actuals)=={cfg['native_variable'],cfg['prior_variable']}
    assert len(steps)==len(set(steps))==8
    verified={}
    for variable,proof in proofs.items():
        d=actuals[variable]
        assert proof['status']==d['status']=='PASS'and d['production_go']is d['independent_acceptance']is False
        assert(d.get('qualification_commit')or d.get('candidate_commit'))==proof['head']
        assert d['cp6_restored']and d['advisor_gate']and d['restore_raw_public_equal']
        if variable==cfg['native_variable']:
            assert proof['head']==cfg['native_head']
            assert d['label']=='CP7_CURRENT_FROZEN_PUBLIC_FINANCE_NATIVE52'
            assert d['source_declaration']['current_installation']==product.sources()
            assert d['source_declaration']['qualification']==parent
            assert d['required_case_ids']==parent['case_ids']and d['required_case_ids_pass']
            assert d['expected_case_count']==d['observed_case_count']==52 and d['native']['counts']=={'PASS':52}
            assert set(d['native']['cases'])==set(parent['case_ids'])
            assert d['baseline_full22_all_rows_all_sequences_equal']and d['baseline_advisors_equal']
            for key in('all22_preinstall_equal','all_rows_and_sequences_equal','global_used_guard_before_any_DDL'):assert d['complete_preuse_removal'][key]is True,key
            for row in d['native']['cases'].values():
                assert row['status']=='PASS'and row['full_boundary_restored']and row['public_schema_unchanged']
                assert all(v in(0,[],{})for v in row.get('session_leaks',{}).values())
                day=row['business_day'];assert day['planned']==day['before']==day['after']
        else:validate_prior(repo,cfg,proof,d,product,steps)
        verified[variable]=dict(proof,observed_status='PASS')
    return verified
