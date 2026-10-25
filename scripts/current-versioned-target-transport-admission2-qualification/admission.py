"""Exact Native36, prior full policy/model transport and both B v2 partitions."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess
from cp7_current_transport_original_schema import checked_group
PARTS=('MODEL_TARGET_TRANSPORT_V2_A_ORIGINAL_REPORT','MODEL_TARGET_TRANSPORT_V2_B_ORIGINAL_REPORT')
VARS={'CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT','CURRENT_MODEL_TARGET_TRANSPORT_ORIGINAL_REPORT',*PARTS}


def admitted(repo,here,ids,product,native,transport):
    parent=native.admitted();assert parent['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes());assert pins['contract']=='cp7.current-versioned-target-transport28-qualification.v2'
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==28 and pins['groups']==transport.GROUPS
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_VERSIONED_TRANSPORT_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    binding=transport.source_binding();proofs=pins['actual_qualification_originals'];assert set(proofs)==VARS
    originals={};heads=set();runs=set();unique=set()
    for variable,proof in proofs.items():
        raw=Path(os.environ[variable]).read_bytes();assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw);assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        assert actual['production_go']is False and actual['independent_acceptance']is False
        if variable=='CURRENT_VERSIONED_TARGET_NATIVE_ORIGINAL_REPORT':
            assert actual['qualification_commit']==proof['head']
            assert actual['source_declaration']['qualification']==parent['qualification']and actual['source_declaration']['current_installation']==product.sources()
            assert actual['native']['counts']=={'PASS':36}and actual['observed_case_count']==36 and actual['required_case_ids_pass']
            assert actual['required_case_ids']==parent['qualification']['case_ids']and actual['complete_preuse_removal']
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']and actual['restore_raw_public_equal']
            assert all(r['status']=='PASS'and r['full_boundary_restored']and r['public_schema_unchanged']for r in actual['native']['cases'].values())
        elif variable=='CURRENT_MODEL_TARGET_TRANSPORT_ORIGINAL_REPORT':
            assert actual['candidate_commit']==proof['head']=='6e30a61b0f6c1bbcc50b3a6a82c0ebd52af47ae3'
            assert actual['label']=='CP7_CURRENT_MODEL_TARGET_TRANSPORT28'
            assert actual['source_declaration']['current_installation']==product.predecessor.predecessor.predecessor.sources()
            assert actual['required_case_ids_pass']and actual['observed_case_count']==28 and actual['complete_preuse_removal']and actual['restore_raw_public_equal']
            for component in('policy','evaluation'):
                path='scripts/'+Path(transport.MODULES[component].__file__).name
                assert actual['source_declaration']['qualification']['files'][path]==sha256((repo/path).read_bytes()).hexdigest()
                for kind in('http','races'):assert set(actual['transport_groups'][component+'_'+kind]['races'if kind=='races'else'cases'])==set(transport.GROUPS[component+'_'+kind])
            expected_groups=actual['source_declaration']['qualification']['groups']
            assert set(actual['transport_groups'])==set(expected_groups)
            for name,g in actual['transport_groups'].items():
                checked_group(g,expected_groups[name],races=name.endswith('_races'))
                rows=g['races'if name.endswith('_races')else'cases'];assert all(r['status']=='PASS'for r in rows.values())
        else:
            assert proof==parent['qualification']['actual_qualification_originals'][variable]
            heads.add(proof['head']);runs.add(proof['run_id'])
            part='A'if variable==PARTS[0]else'B';assert actual['transport_part']==part
            target=transport.target.IDS
            required=dict(native=target['native'],races=target['races'][:4])if part=='A'else dict(native=target['native'],races=target['races'][4:],http=target['http'])
            assert actual['required_case_ids']==required and actual['required_case_ids_pass']and actual['required_case_counts_pass']and all(actual['restore_components'].values())
            assert actual['observed_case_count']==sum(map(len,required.values()))
            for group,names in required.items():
                g=actual[group];rows=g['races'if group=='races'else'cases'];assert set(rows)==set(names)and g['counts']=={'PASS':len(names)}
                unique.update(names);assert all(r['status']=='PASS'for r in rows.values())
                if group=='native':assert all(r['full_boundary_restored']and r['public_schema_unchanged']for r in rows.values())
                else:checked_group(g,names,races=group=='races')
            found=0
            for name,values in actual.items():
                if name.endswith('source_sha256')and isinstance(values,dict):
                    found+=1
                    for path,digest in values.items():
                        path=path if path.startswith(('scripts/','src/'))else'scripts/'+path
                        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
            assert found
        originals[variable]=dict(proof,observed_status='PASS')
    assert len(heads)==len(runs)==1 and len(unique)==11
    return dict(qualified_current_versioned_target=parent,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=originals,retained_business_source_binding=binding,retained_policy_model_cases=18,exact_versioned_target_cases=10,
        B_transport_unique_cases=11,repeated_catalog_anchor_credit=0,production_go=False,independent_acceptance=False)
