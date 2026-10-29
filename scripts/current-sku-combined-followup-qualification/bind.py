"""Writer-only binder for this new child. Never regenerate pins in CI."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
BASE = '21c69cf25defcee854beb08e998062d7e883d968'
TREE = 'a0d2c0da83bf5dc29f2c6b2e02abe6d7ed68f89e'
PRIOR = '961c22f8d3fa6fd2c16a8932a23b6d3a347d0c98'
PRIOR_TREE = '63b22c8b764ec02f3aa4842b2309338e32e306b5'
PRIOR_COMBINED = '6466a7b7dbdb04e34103ab57c7e863723115cdea'
IMPORTS = {
    'scripts/current-sku-pair-concurrency-qualification/': 'b7b9a5e88aecb7792a1d0daf9ca6fa7e206e4341',
    'scripts/current-sku-pair-browser-qualification/': '1dab4c6061fa67367abe640b252f7b85c9caae05',
    'scripts/current-staged-ai-browser-qualification/': '81d5c57f31b169eb3229ebbed3c8522a0f0c3d71',
    'scripts/current-sku-group-cost-qualification/': 'edc2b8502c0dc12c5611320274a203ff22609732',
}
RECONCILED = {'scripts/current-sku-pair-browser-qualification/' + name
              for name in ('SOURCE.json', 'source_guard.py', 'test_plan.py', 'README.md')}
RECONCILED |= {'scripts/current-sku-group-cost-qualification/' + name
               for name in ('SOURCE.json', 'source_guard.py', 'cases.py', 'README.md')}


def load_transition():
    spec=importlib.util.spec_from_file_location('sku_combined_exact_UTC_transition',HERE/'successor.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def prepared_metadata(git):
    """Derive only exact pin metadata, never callback or financial bodies."""
    transition=load_transition();result={}
    prefixes=('scripts/current-sku-pair-browser-qualification/','scripts/current-sku-group-cost-qualification/')
    for prefix in prefixes:
        browser=prefix==prefixes[0];head=PRIOR_COMBINED if browser else IMPORTS[prefix]
        raw=git('show',head+':'+prefix+'SOURCE.json');expected=json.loads(raw);changed=set()
        if browser:
            replacements={
                'source_guard.py':((PRIOR,BASE),(PRIOR_TREE,TREE)),
                'test_plan.py':((PRIOR,BASE),),
                'README.md':((
                    'The combined preparation now pins\nbackend961c22f8/tree63b22c8b: only the reviewed explicit-null pair-delete repair\n'
                    'and its three-line client regression changed among the 654 pinned inputs.\n'
                    'Fixture, browser journey, financial oracles and all other input bytes stay\nunchanged.',
                    'The first combined preparation pinned\nbackend961c22f8/tree63b22c8b with the explicit-null pair-delete repair and its\n'
                    'client regression. The successor pins backend21c69cf2/treea0d2c0da and\n'
                    'additionally changes only two UTC function attributes plus an explanatory\n'
                    'comment in conversion.sql. Fixture, browser journey, financial oracles and\n'
                    'all other input bytes stay unchanged. Native961 remains INCOMPLETE6/7;\n'
                    'the successor prerequisite is still null until its full terminal PASS.'),),
            }
            runtime=('scripts/cp7_sku_pair_conversion/conversion.sql',)
        else:
            replacements={
                'source_guard.py':((PRIOR,BASE),(PRIOR_TREE,TREE)),
                'cases.py':(("assert backend_commit=='"+PRIOR+"'","assert backend_commit=='"+BASE+"'"),),
                'README.md':((PRIOR,BASE),(PRIOR_TREE,TREE)),
            }
            runtime=('scripts/cp7_sku_pair_conversion/conversion.sql','scripts/current-sku-pair-conversion-qualification/cases.py')
        for name,pairs in replacements.items():
            original=git('show',head+':'+prefix+name)
            if not browser and name=='README.md':
                # The README has two occurrences of the same backend pin.
                assert original.decode().count(PRIOR)==2
                assert original.decode().count(PRIOR_TREE)==1
                derived=original.decode().replace(PRIOR,BASE).replace(PRIOR_TREE,TREE).encode()
            else:derived=transition.replacements(original,pairs)
            result[prefix+name]=derived;expected['files'][prefix+name]=sha256(derived).hexdigest();changed.add(prefix+name)
        for name in runtime:
            old=git('show',PRIOR+':'+name);new=git('show',BASE+':'+name)
            assert expected['files'][name]==sha256(old).hexdigest(),name
            assert (ROOT/name).read_bytes()==new,name
            expected['files'][name]=sha256(new).hexdigest();changed.add(name)
        expected['backend_candidate']=dict(commit=BASE,tree=TREE)
        expected['UTC_successor_derivation']=dict(prior_manifest_sha256=sha256(raw).hexdigest(),prior_head=PRIOR,
            permitted_changed_inputs=sorted(changed),product_change='ONLY_TWO_UTC_FUNCTION_ATTRIBUTES_AND_EXPLANATORY_COMMENT',
            Native_case_change='SAME_MIXED_CASE_FIVE_CALLER_ZONES_ALL_FIELDS_EQUAL'if not browser else 'NOT_IN_BROWSER_INPUT_GRAPH',
            callback_financial_assertion_bodies_changed=False,fixture_browser_oracles_changed=False,
            retained961_usable_prerequisite=False,actual_execution=False)
        result[prefix+'SOURCE.json']=(json.dumps(expected,indent=2)+'\n').encode()
    assert set(result)==RECONCILED
    return result


def reconcile_prepared(git):
    for name,derived in prepared_metadata(git).items():
        assert (ROOT/name).read_bytes()==derived,'UNREVIEWED_PREPARED_METADATA:'+name
    for prefix in ('scripts/current-sku-pair-browser-qualification/','scripts/current-sku-group-cost-qualification/'):
        for name,digest in json.loads((ROOT/prefix/'SOURCE.json').read_bytes())['files'].items():
            assert sha256((ROOT/name).read_bytes()).hexdigest()==digest,'UNREVIEWED_PREPARED_INPUT:'+name


def bind():
    if os.environ.get('CI'): raise ValueError('SKU_COMBINED_SOURCE_CANNOT_BE_REGENERATED_IN_CI')
    git = lambda *args: subprocess.check_output(['git', '-C', str(ROOT), *args])
    transition=load_transition().admit_transition(git)
    reconcile_prepared(git)
    original_import_sha256={}
    for prefix, head in IMPORTS.items():
        names = git('diff-tree', '--no-commit-id', '--name-only', '-r', head).decode().splitlines()
        assert all(name.startswith(prefix) for name in names)
        actual={str(path.relative_to(ROOT))for path in(ROOT/prefix).rglob('*')if path.is_file()}
        assert actual==set(names), 'UNDECLARED_IMPORTED_NAMESPACE_FILE:'+prefix
        for name in names:
            original=git('show',head+':'+name);original_import_sha256[name]=sha256(original).hexdigest()
            if name not in RECONCILED: assert (ROOT / name).read_bytes() == original, name
    old = json.loads((ROOT / 'scripts/current-sku-pair-native-adapter/SOURCE.json').read_bytes())
    for name, expected in old['files'].items():
        assert sha256((ROOT / name).read_bytes()).hexdigest() == expected, 'OLD_NATIVE21C_INPUT_CHANGED:' + name
    unchanged = sorted(set(old['files']) | {'scripts/current-sku-pair-native-adapter/SOURCE.json', '.github/workflows/cp7-sku-pair-native.yml'})
    for name in unchanged: assert (ROOT / name).read_bytes() == git('show', BASE + ':' + name), name
    paths = set(unchanged)
    for prefix in IMPORTS:
        manifest = ROOT / prefix / 'SOURCE.json'; value = json.loads(manifest.read_bytes()); paths.add(str(manifest.relative_to(ROOT)))
        files = value['files']
        paths.update(row['path'] for row in files) if isinstance(files, list) else paths.update(files)
        paths.update(str(path.relative_to(ROOT)) for path in (ROOT / prefix).rglob('*') if path.is_file())
    changed = set(git('diff', '--name-only', BASE).decode().splitlines())
    own = set(str(path.relative_to(ROOT)) for path in HERE.rglob('*') if path.is_file() and path.name != 'SOURCE.json')
    workflow = '.github/workflows/cp7-sku-combined-followup.yml'
    changed |= own | {workflow, 'scripts/current-sku-combined-followup-qualification/SOURCE.json'}
    prefixes = tuple(IMPORTS) + ('scripts/current-sku-combined-followup-qualification/',)
    assert all(name.startswith(prefixes) or name == workflow for name in changed), 'UNDECLARED_COMBINED_PATH'
    paths |= changed
    paths.discard('scripts/current-sku-combined-followup-qualification/SOURCE.json')
    files = {}
    for name in sorted(paths):
        assert '__pycache__' not in name and not name.endswith('.pyc'), name
        raw = (ROOT / name).read_bytes(); files[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    waiting=json.loads((HERE / 'CONFIG.json').read_bytes())['accepted_native7'] is None
    source = dict(status='PREPARED_PENDING_TERMINAL_NATIVE21C_PIN' if waiting else 'PREPARED_RETAINED_NATIVE21C_PINNED_NOT_EXECUTED', base_head=BASE,
                  accepted_native21c_proof_is_placeholder=waiting, reviewed_base_transition=transition,
                  imports=IMPORTS, original_import_sha256=original_import_sha256,
                  allowed_changes=sorted(changed), unchanged_native21c_files=unchanged,
                  files=files, counts=dict(base_Native=7, cost_Native=3, conversion_races=3, administrative_Native_permission_waits=6, real_Auth_browser=4),
                  group_recovery_supported=False, actual_execution=False, production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n')
    return dict(status=source['status'], source_files=len(files), declared_child_paths=len(changed))


if __name__ == '__main__': print(json.dumps(bind()))
