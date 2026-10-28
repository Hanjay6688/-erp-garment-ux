"""Bind the old unchanged UI oracles to the actual qualified combined backend."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,subprocess


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def admitted(repo,here,ids,product,native,groups):
    config=json.loads((here/'CONFIG.json').read_bytes())
    load('combined_UI_closed_runtime_gate',here/'evidence.py').gate(config)
    assert list(ids)==config['case_ids'] and groups==config['groups'] and len(ids)==2
    source=json.loads((here/'SOURCE.json').read_bytes())
    assert source['contract']==config['contract'] and source['case_ids']==list(ids)
    assert source['production_go']is source['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    actual,accepted=product.qualification()
    prior_here=repo/'scripts/current-progress-finance-ui-browser-qualification'
    prior=load('combined_UI_original_full_admission',prior_here/'admission.py')
    import cp7_current_choice_preparation.installation as prior_product
    unchanged_UI=prior.admitted(repo,prior_here,ids,prior_product,native,groups)
    guard=load('combined_UI_unchanged_browser_guards',here/'source_guard.py').check(repo,here)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    return dict(qualification=source,current_installation=product.sources(),
        accepted_combined_runtime=accepted,complete_combined_declaration=actual['source_declaration'],
        unchanged_prior_UI_source=unchanged_UI,source_guard=guard,actual_cron_claim=False,
        default_adopted=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    here=Path(__file__).resolve().parent
    probe=load('combined_UI_admission_probe',here/'probe.py')
    result=probe.admitted()
    print(json.dumps(dict(status='SOURCE_ADMITTED',pins=len(result['qualification']['files']),
        actual_browser_executed=False,actual_Auth_executed=False)))
