"""Bind the reviewed presentation to the current Mandor preparation.

The old component receipts remain historical. Only exact, separately verified
presentation bytes are projected back for their old source comparisons; every
current src file and every other current baseline file is checked independently.
No installer, database, runtime admission, or acceptance evidence is created.
"""
from copy import deepcopy
import json


def verify(root, manifest, git, entries, pin, require):
    namespace = 'scripts/current-unified-candidate/'
    source_name = namespace + 'THEMED_SOURCE.json'
    proof = json.loads((root / source_name).read_bytes())
    require(proof['contract'] == 'cp7.current-mandor-reviewed-theme.v1'
            and proof['runtime_admission'] is False
            and proof['production_go'] is False, 'THEMED_SOURCE_ONLY')
    baseline = proof['current_mandor']['tree']
    donor = proof['reviewed_UI']['tree']
    before, after = entries(baseline), entries(donor)
    fixture = 'tests/fixtures/skuMovingAverageReaderPg17.json'
    delta = {name for name in before.keys() | after.keys()
             if (name.startswith('src/') or name == fixture)
             and before.get(name) != after.get(name)}
    require(delta == set(proof['UI_derivations']) and len(delta) == 80,
            'THEMED_EXACT_79_SRC_AND_ONE_READER_FIXTURE')
    code_allowlist = {
        'src/App.tsx', 'src/main.tsx', 'src/OperationsAdminPages.tsx',
        'src/MobilePrimaryNavigation.tsx', 'src/MobilePrimaryNavigation.dom.test.tsx',
        'src/ConnectedFgStockPage.tsx', 'src/ConnectedFgStockPage.dom.test.tsx',
        'src/fgContract.ts', 'src/fgMovingAverageContract.test.ts', fixture,
    }
    previous = {}
    for name, route in proof['UI_derivations'].items():
        require(name.endswith('.css') or name in code_allowlist,
                'THEMED_PRESENTATION_AND_READER_SCOPE:' + name)
        current = root / name
        raw = git('show', donor + ':' + name)
        require(current.is_file() and not current.is_symlink()
                and current.read_bytes() == raw and pin(raw) == route['after'],
                'THEMED_EXACT_DONOR_BYTES:' + name)
        if name in before:
            previous[name] = git('show', baseline + ':' + name)
            require(pin(previous[name]) == route['before'], 'THEMED_BEFORE_PIN:' + name)
        else:
            require(route['before'] is None, 'THEMED_NEW_SOURCE_WITHOUT_OLD_BYTES:' + name)

    # The entire current UI, including unchanged consumers, equals the donor.
    donor_src = {name for name in after if name.startswith('src/')}
    current_src = {str(path.relative_to(root)) for path in (root / 'src').rglob('*')
                   if path.is_file() or path.is_symlink()}
    require(current_src == donor_src, 'THEMED_COMPLETE_SRC_NAMESPACE')
    for name in donor_src:
        current = root / name
        require(current.is_file() and not current.is_symlink()
                and git('hash-object', str(current)).decode().strip() == after[name]['blob'],
                'THEMED_COMPLETE_SRC_BYTES:' + name)
    for name, blob in proof['identical_build_inputs'].items():
        require(before[name]['blob'] == after[name]['blob'] == blob
                and git('hash-object', str(root / name)).decode().strip() == blob,
                'THEMED_IDENTICAL_BUILD_INPUT:' + name)

    metadata = set(proof['metadata_appenditions'])
    require(metadata == {'docs/cp7/d17-14/KOORDINASI.md', namespace + 'READINESS.txt'},
            'THEMED_EXACT_METADATA_APPENDITIONS')
    for name, suffix in proof['metadata_appenditions'].items():
        previous[name] = git('show', baseline + ':' + name)
        require((root / name).read_bytes() == previous[name] + suffix.encode(),
                'THEMED_EXACT_METADATA_APPEND:' + name)

    gate_paths = {namespace + 'SOURCE.json', namespace + 'check_source.py'}
    new_gate_paths = {source_name, namespace + 'themed_source.py'}
    allowed = delta | metadata | gate_paths | new_gate_paths
    changed = set(git('diff', '--name-only', baseline).decode().splitlines())
    changed.update(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
    require(changed == allowed, 'THEMED_CURRENT_MANDOR_EXACT_CHANGE_BOUNDARY:'
            + str(sorted(changed ^ allowed)))

    old = json.loads(git('show', baseline + ':' + namespace + 'SOURCE.json'))
    expected = deepcopy(old)
    for name in (set(old['files']) & allowed) | new_gate_paths | metadata:
        expected['files'][name] = pin((root / name).read_bytes())
    expected['new_paths'] = sorted(set(old['new_paths']) | (allowed - set(before)))
    expected['UI_integration'] = dict(manifest=source_name,
        status='EXACT_REVIEWED_UI_ON_CURRENT_MANDOR_SOURCE_NOT_ERP_ACCEPTANCE')
    require(manifest == expected, 'THEMED_OLD_MANIFEST_ONLY_DECLARED_PRESENTATION_ROUTES')
    return previous, dict(
        status='EXACT_REVIEWED_UI_ON_CURRENT_MANDOR_SOURCE_NOT_ERP_ACCEPTANCE',
        current_mandor=proof['current_mandor'], reviewed_UI=proof['reviewed_UI'],
        source_paths=79, reader_fixtures=1, entire_src_files_equal_donor=len(donor_src),
        metadata_appenditions=len(metadata), all_other_baseline_files_unchanged=True,
        donor_visual_evidence_reused_not_rerun=True, actual_ERP_cases=0,
        actual_Auth_cases=0, runtime_admission=False, production_go=False)
