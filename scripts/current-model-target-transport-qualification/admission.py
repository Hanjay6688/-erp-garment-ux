"""Admit Native20, policy/v2 transport10, and all eleven target controls.

Target transport may be one complete Original or both complete same-head
partition Originals. Partial/cancelled runs never supply missing case credit.
"""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys


TARGET_FULL='MODEL_TARGET_TRANSPORT_ORIGINAL_REPORT'
TARGET_PARTS=('MODEL_TARGET_TRANSPORT_PART_A_ORIGINAL_REPORT','MODEL_TARGET_TRANSPORT_PART_B_ORIGINAL_REPORT')
# Reviewed exact selector from B2b335934; it returns original operations unchanged.
PART_PROVIDER_SHA256='44f62a6571ffc329e15e9fa1c0cbb799dd51928de3c6b3550828fa2e46c0b048'


def target_prerequisites(proofs,transport,product):
    selected=set(proofs)&({TARGET_FULL}|set(TARGET_PARTS))
    assert selected in({TARGET_FULL},set(TARGET_PARTS)), 'TARGET_TRANSPORT_REQUIRES_FULL_OR_BOTH_PARTS'
    full=transport.target.IDS
    assert {k:len(v)for k,v in full.items()}==dict(native=1,races=7,http=3)
    expected={TARGET_FULL:full,TARGET_PARTS[0]:dict(native=full['native'],races=full['races'][:4]),
              TARGET_PARTS[1]:dict(native=full['native'],races=full['races'][4:],http=full['http'])}
    result={};part_sources=[]
    for variable in sorted(selected):
        proof=proofs[variable];raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw);ids=expected[variable];count=sum(map(len,ids.values()))
        assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and actual['observed_case_count']==count
        assert actual['required_case_ids']==ids and actual['required_case_counts']=={k:len(v)for k,v in ids.items()}
        assert actual['model_target_source_sha256']==product.target.verify_sources()
        for group,names in ids.items():
            observed=actual[group];rows=observed.get('races'if group=='races'else'cases',{})
            assert observed['counts']=={'PASS':len(names)}and set(rows)==set(names)
            assert all(row['status']=='PASS'for row in rows.values())
        if variable!=TARGET_FULL:
            part='A'if variable==TARGET_PARTS[0]else'B'
            assert actual['transport_part']==part and actual['model_target_transport_part_qualified']
            assert actual['full11_requires_both_same_head_Originals']and not actual['model_target_transport_qualified']
            assert actual['coverage']==dict(unique_required_cases=11,duplicate_catalog_anchor_credit=0,part_case_counts=dict(A=5,B=7))
            sources=actual['transport_part_source_sha256']
            assert set(sources)=={'cp7_ow11_model_target_transport_parts.py','cp7_ow11_model_target_transport_cases.py'}
            assert sources['cp7_ow11_model_target_transport_parts.py']==PART_PROVIDER_SHA256
            assert sources['cp7_ow11_model_target_transport_cases.py']==sha256(Path(transport.target.__file__).read_bytes()).hexdigest()
            part_sources.append(sources)
        else:assert actual['model_target_transport_qualified']
        result[variable]=dict(proof,observed_status='PASS')
    if selected==set(TARGET_PARTS):
        assert proofs[TARGET_PARTS[0]]['head']==proofs[TARGET_PARTS[1]]['head'], 'TARGET_PARTS_DIFFERENT_HEADS'
        assert part_sources[0]==part_sources[1], 'TARGET_PARTS_DIFFERENT_PROVIDERS'
    return result


def admitted(repo,here,ids,product,native,transport):
    predecessor=native.admitted()
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==28
    assert pins['groups']==transport.GROUPS
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_RETAINED_MODEL_TRANSPORT_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    originals=target_prerequisites(pins['actual_qualification_originals'],transport,product)
    for variable,proof in pins['actual_qualification_originals'].items():
        if variable in originals:continue
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw)
        assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate'],variable
        if variable=='CURRENT_MODEL_TARGET_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.sources()
            assert actual['native']['counts']=={'PASS':20}and actual['observed_case_count']==20
            assert actual['required_case_ids_pass']and actual['required_case_ids']==predecessor['qualification']['case_ids']
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        elif variable in('MODEL_POLICY_TRANSPORT_ORIGINAL_REPORT','MODEL_V2_TRANSPORT_ORIGINAL_REPORT'):
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and actual['observed_case_count']==10
            component='policy'if variable=='MODEL_POLICY_TRANSPORT_ORIGINAL_REPORT'else'evaluation'
            assert actual['required_case_ids']==transport.MODULES[component].IDS
            assert actual['native']['counts']=={'PASS':1}
            assert actual['races']['counts']=={'PASS':6}and actual['http']['counts']=={'PASS':3}
            assert actual['model_policy_source_sha256']==product.predecessor.policy.verify_sources()
            if component=='evaluation':assert actual['model_evaluation_v2_source_sha256']==product.predecessor.evaluation.verify_sources()
        else:raise ValueError('CURRENT_MODEL_TARGET_TRANSPORT_UNDECLARED_ORIGINAL: '+variable)
        originals[variable]=dict(proof,observed_status='PASS')
    assert set(originals)-({TARGET_FULL}|set(TARGET_PARTS))=={'CURRENT_MODEL_TARGET_ORIGINAL_REPORT','MODEL_POLICY_TRANSPORT_ORIGINAL_REPORT','MODEL_V2_TRANSPORT_ORIGINAL_REPORT'}
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(qualified_current_model_target=predecessor,current_installation=product.sources(),
        qualification=pins,actual_originals_verified=originals,actual_loaded_modules_verified=loaded,
        retained_business_source_binding=transport.source_binding(),original_B_case_bodies_unchanged=True)
