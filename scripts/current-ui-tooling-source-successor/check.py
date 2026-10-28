"""Verify imported frozen source and B originals; no database or adoption."""
import importlib.util
from pathlib import Path
from hashlib import sha256
import json,subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def check():
    spec=importlib.util.spec_from_file_location('scoped_tooling_successor',ROOT/'scripts/current-tooling-source-successor/tooling.py');tooling=importlib.util.module_from_spec(spec);spec.loader.exec_module(tooling)
    tooling.derivation();successor=tooling.checked()
    spec=importlib.util.spec_from_file_location('scoped_A_UI_successor',HERE/'ui_binding.py');ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
    ui.derivation();frontend=ui.checked()
    config=json.loads((ROOT/'scripts/current-source-closure-preparation/IMPORT.json').read_bytes());expected={}
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
    assert expected[tooling.SCRIPT]==tooling.OLD
    assert expected[ui.PANEL]==ui.OLD
    for path,digest in expected.items():
        declared=successor['files'][path]if path==tooling.SCRIPT else frontend['files'][path]if path==ui.PANEL else digest
        assert sha256((ROOT/path).read_bytes()).hexdigest()==declared,path
    for path in config['current_B_exact_paths']:
        assert(ROOT/path).read_bytes()==subprocess.check_output(
            ['git','-C',str(ROOT),'show',config['current_B_head']+':'+path]),path
    for item in config['test_dependency_provenance']:
        raw=(ROOT/item['path']).read_bytes()
        assert len(raw)==item['bytes'] and sha256(raw).hexdigest()==item['sha256'],item['path']
        assert raw==subprocess.check_output(['git','-C',str(ROOT),'show',
            item['source_head']+':'+item['source_path']]),item['path']
    fixture_changes=config['fixture_setup_changes']
    for path,item in fixture_changes.items():
        raw=(ROOT/path).read_bytes()
        assert sha256(raw).hexdigest()==item['after_sha256'],path
        before=subprocess.check_output(['git','-C',str(ROOT),'show',config['base_head']+':'+path])
        assert sha256(before).hexdigest()==item['before_sha256'],path
        restored=raw.replace(b"\n const rounding = extractFunction(current, 'cp7_analysis_native.rounded_suggestion')",b'')
        restored=restored.replace(b'${fact}${rounding}${ref}',b'${fact}${ref}')
        restored=restored.replace(b"'cp7_analysis_native.fact', 'cp7_analysis_native.rounded_suggestion',",b"'cp7_analysis_native.fact',")
        assert restored==before,('ONLY_ADD_EXACT_PRODUCT_DEPENDENCY',path)
    resolution=config['qualification_test_resolution']
    for path,digest in resolution['files'].items():
        assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    raw=(ROOT/resolution['provider_path']).read_bytes()
    assert sha256(raw).hexdigest()==resolution['provider_sha256']
    assert raw==subprocess.check_output(['git','-C',str(ROOT),'show',
        resolution['provider_head']+':'+resolution['provider_source_path']])
    assert sha256((ROOT/resolution['unchanged_default_parser']).read_bytes()).hexdigest()==resolution['unchanged_default_parser_sha256']
    assert resolution['product_or_existing_test_bodies_changed']is resolution['default_Vite_configuration_changed']is False
    for path in ('src/App.tsx','package.json','package-lock.json','vite.config.ts',
        'scripts/cp6_t3_aligned_install.py','scripts/cp7_p21_current_chain_rehearsal_probe.py'):
        assert(ROOT/path).read_bytes()==subprocess.check_output(
            ['git','-C',str(ROOT),'show',config['base_head']+':'+path]),path
    return dict(status='PASS_SCOPED_JS_UI_SUCCESSORS_SOURCE_ONLY',unchanged_exact_files=len(expected)-2,
        replaced_A_UI_files=1,new_UI_test_files=1,frontend_successor=frontend,
        replaced_tooling_files=1,new_tested_helper_files=2,successor=successor,
        frozen_manifests=len(config['manifests']),current_B_exact_files=len(config['current_B_exact_paths']),
        main_dispatch_App_and_package_unchanged=True,business_oracles_unchanged=True,
        actual_database_Auth_browser_cases=0,default_adopted=False,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    value=check();out=ROOT/'cp6-proof/current-ui-tooling-source-successor/SOURCE_CLOSURE.json'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value))
