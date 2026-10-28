"""Verify imported frozen source and B originals; no database or adoption."""
from pathlib import Path
from hashlib import sha256
import json,subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def check():
    config=json.loads((HERE/'IMPORT.json').read_bytes());expected={}
    assert config['production_go']is config['independent_acceptance']is False
    assert config['default_installer_or_dispatch_changed']is False
    for path,digest in config['manifests'].items():
        raw=(ROOT/path).read_bytes();assert sha256(raw).hexdigest()==digest,path
        for name,pin in json.loads(raw)['files'].items():
            assert name not in expected or expected[name]==pin,('CONFLICTING_PIN',name)
            expected[name]=pin
    expected.update(config['manifests'])
    assert len(expected)==config['frozen_manifest_exact_files']
    for path,digest in config['extra_test_fixture_files'].items():
        assert path not in expected
        expected[path]=digest
    assert len(expected)==config['required_exact_files']
    for path,digest in expected.items():assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    for path in config['current_B_exact_paths']:
        assert(ROOT/path).read_bytes()==subprocess.check_output(
            ['git','-C',str(ROOT),'show',config['current_B_head']+':'+path]),path
    for path in ('src/App.tsx','package.json','package-lock.json',
        'scripts/cp6_t3_aligned_install.py','scripts/cp7_p21_current_chain_rehearsal_probe.py'):
        assert(ROOT/path).read_bytes()==subprocess.check_output(
            ['git','-C',str(ROOT),'show',config['base_head']+':'+path]),path
    return dict(status='PASS_EXACT_SOURCE_CLOSURE_ONLY',exact_files=len(expected),
        frozen_manifests=len(config['manifests']),current_B_exact_files=len(config['current_B_exact_paths']),
        main_dispatch_App_and_package_unchanged=True,business_oracles_unchanged=True,
        actual_database_Auth_browser_cases=0,default_adopted=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    value=check();out=ROOT/'cp6-proof/current-source-closure/SOURCE_CLOSURE.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value))
