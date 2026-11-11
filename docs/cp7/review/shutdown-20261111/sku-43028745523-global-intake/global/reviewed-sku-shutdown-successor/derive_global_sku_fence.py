"""Bind the reviewed SKU lineage into the still closed Global source.

The pending path checks all 209 prepared paths. The verified path requires
the actual SKU Root and all 219 source paths. The eight runtime gates stay closed.
"""
from hashlib import sha256

from reviewed_sku_source import CANDIDATE, CANDIDATE_TREE, DELTA, LINEAGE, WORKFLOW

PREIMAGE = dict(bytes=9164, sha256='65e21a8c6f1796d24c03f57ccc078b8aa8b42826f2b34b3066c74ffdba90e3bb')
PREPARED_COUNT = 209
FULL_SCOPE_COUNT = 219
ROW_ANCHOR = "    result = {}\n    for name, row in value['files'].items():\n"
PENDING_LINE = "    current_sku = pending_sku(manifest['pending_current_SKU_preparation'], expected)\n"
SOURCE_CHECK = """    bound = manifest.get('reviewed_current_SKU_source')
    if bound is None:
        current_sku = pending_sku(manifest['pending_current_SKU_preparation'], expected)
        report = dict(exact_current_SKU_preparation_paths=len(current_sku), pending_current_SKU_head=SKU_HEAD)
    else:
        base.require(not observe_sparse, 'GLOBAL_VERIFIED_SKU_REQUIRES_COMPLETE_SOURCE')
        current_sku = reviewed_sku(bound, expected)
        report = dict(exact_verified_SKU_source_paths=len(current_sku), verified_SKU_head=bound['head'])
"""
BOUND = """    return sku_rows(value, baseline, before, after)


SKU_ROOT_NAME = 'SKU25_PARENT_ROOT_ACTUAL_INTAKE.json'
SKU_OWNING_PATHS = frozenset(__PATHS__)
SKU_REVIEWED_LINEAGE = __LINEAGE__
SKU_REVIEWED_ACTUAL_HEAD = __ACTUAL_HEAD__
SKU_REVIEWED_ACTUAL_TREE = __ACTUAL_TREE__


def reviewed_sku(value, baseline):
    require = base.require
    path = HERE / SKU_ROOT_NAME
    require(path.is_file() and not path.is_symlink(), 'GLOBAL_VERIFIED_SKU_ROOT_REGULAR_FILE_REQUIRED')
    raw = path.read_bytes()
    root = json.loads(raw)
    require(root.get('status') == 'ROOT_VERIFIED_CURRENT_SKU_NATIVE25_BROWSER2_ALL5'
            and root.get('actual_business_cases') == 27 and root.get('actual_Native_cases') == 25
            and root.get('actual_browser_cases') == 2 and root.get('package_all_five') is True
            and root.get('actual_outer_restore') is True and root.get('prior_runs_aggregated') is False
            and root.get('production_go') is False and root.get('independent_acceptance') is False
            and root.get('complete_global_input_review') is False,
            'GLOBAL_VERIFIED_SKU_ROOT_REQUIRED')
    for name, key in (('MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json', 'mandor_root'),
                      ('CUMULATIVE_RUNTIME_BINDING.json', 'mandor_cumulative_decision')):
        parent = ROOT / 'scripts/current-sku-automatic-composite-preparation' / name
        require(parent.is_file() and not parent.is_symlink(), 'GLOBAL_CUMULATIVE_MANDOR_REGULAR_INPUT_REQUIRED')
        parent_raw = parent.read_bytes()
        require(root.get(key) == dict(bytes=len(parent_raw), sha256=sha256(parent_raw).hexdigest()),
                'GLOBAL_CUMULATIVE_MANDOR_ORIGINAL_BINDING_CHANGED')
    require(root.get('mandor_evidence_mode') == 'CUMULATIVE_15_PLUS_2',
            'GLOBAL_EXPLICIT_CUMULATIVE_MANDOR_MODE_REQUIRED')
    require((value['base_head'], value['base_tree']) == (SKU_BASE, SKU_BASE_TREE)
            and (root['head'], root['tree']) == (SKU_REVIEWED_ACTUAL_HEAD, SKU_REVIEWED_ACTUAL_TREE)
            and (value['head'], value['tree'], value['actual_run'], value['actual_job'])
                == (root['head'], root['tree'], root['run_id'], root['job_id'])
            and all(type(root[k]) is int and root[k] > 0 for k in ('run_id', 'job_id', 'artifact_id'))
            and value['actual_Root'] == dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
            and value['actual_full25_catalogue'] == root['global_parent_catalogue']['original']
            and root['global_parent_catalogue']['fingerprint']['groups'] == 25,
            'GLOBAL_SKU_SOURCE_MUST_MATCH_ACTUAL_ROOT_AND_CATALOGUE')
    reviewed = value['reviewed_owning_source']
    head, tree = root['head'], root['tree']
    require(set(reviewed) == {'head', 'tree', 'run_id', 'job_id', 'parents', 'files'}
            and all(reviewed[key] == root[key] for key in ('head', 'tree', 'run_id', 'job_id'))
            and reviewed['parents'] == [SKU_REVIEWED_LINEAGE[-2][0]]
            and set(reviewed['files']) == SKU_OWNING_PATHS,
            'GLOBAL_EXACT_REVIEWED_SKU_SOURCE_REQUIRED')
    git = base.git
    refs = [commit + '^{tree}' for commit, _ in SKU_REVIEWED_LINEAGE]
    trees = [source_tree for _, source_tree in SKU_REVIEWED_LINEAGE]
    require(git('rev-parse', SKU_BASE + '^{tree}', *refs).decode().splitlines() == [SKU_BASE_TREE, *trees],
            'GLOBAL_VERIFIED_SKU_ANCESTRY_OR_TREE_CHANGED')
    for (previous, _), (commit, _) in zip(SKU_REVIEWED_LINEAGE, SKU_REVIEWED_LINEAGE[1:]):
        require(git('rev-list', '--parents', '-n', '1', commit).decode().split() == [commit, previous],
                'GLOBAL_VERIFIED_SKU_ANCESTRY_OR_TREE_CHANGED')
    before, closed, after = (entries(t) for t in (SKU_BASE_TREE, trees[0], tree))
    changed = {name for name in closed.keys() | after.keys() if closed.get(name) != after.get(name)}
    require(changed == SKU_OWNING_PATHS and len(changed) == __DELTA_COUNT__, 'GLOBAL_EXACT_SKU_OWNING_DELTA_REQUIRED')
    for name in sorted(changed):
        old, new = closed.get(name), after.get(name)
        require(new is not None and new['mode'] == '100644'
                and (old is None or old['mode'] == '100644'),
                'GLOBAL_EXACT_REGULAR_SKU_OWNING_SOURCE_REQUIRED:' + name)
        expected = dict(old_mode=old['mode'] if old else '000000', new_mode=new['mode'],
                        before=old['blob'] if old else '0' * 40, after=new['blob'],
                        status='M' if old else 'A')
        require(reviewed['files'][name] == expected, 'GLOBAL_REVIEWED_SKU_OWNING_BLOB_CHANGED:' + name)
    paths = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    prepared = {name for name in before.keys() | closed.keys() if before.get(name) != closed.get(name)}
    require(len(prepared) == __PREPARED_COUNT__ and len(paths) == __FULL_COUNT__
            and paths == set(value['files']) == prepared | changed,
            'GLOBAL_COMPLETE_VERIFIED_SKU_SOURCE_PATHS_REQUIRED')
    return sku_rows(value, baseline, before, after)


def sku_rows(value, baseline, before, after):
    require = base.require
"""


def derive(raw):
    if dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) != PREIMAGE:
        raise ValueError('GLOBAL_EXACT_CURRENT_CLOSED_SKU_FENCE_PREIMAGE_REQUIRED')
    source = raw.decode()
    status = "return dict(status='GLOBAL_AUTOMATIC_EXACT_SOURCE_PREPARATION_NOT_RUNTIME', parent=source,"
    upgraded = ("return dict(status=('GLOBAL_AUTOMATIC_VERIFIED_SKU_SOURCE_REVIEW_NOT_RUNTIME' if bound else\n"
                "                        'GLOBAL_AUTOMATIC_EXACT_SOURCE_PREPARATION_NOT_RUNTIME'), parent=source,")
    report = ("                exact_current_SKU_preparation_paths=len(current_sku),\n"
              "                pending_current_SKU_head=SKU_HEAD, actual_current_SKU_Root_adopted=False,")
    fence = "    base.require(all(getattr(install.admission, name) is None for name in install.GATES),\n"
    preserve = ("    base.require(manifest.get('active_workflow_added') is False, 'GLOBAL_CLOSED_WORKFLOW_REQUIRED')\n"
                "    if bound is not None:\n"
                f"        base.require({WORKFLOW!r} in current_sku, 'GLOBAL_EXACT_SKU_WORKFLOW_SOURCE_REQUIRED')\n")
    pending_scope_end = "            'GLOBAL_AUTOMATIC_COMPLETE_CURRENT_SKU_PATHS_REQUIRED')\n"
    values = {'__PATHS__': repr(tuple(sorted(DELTA))), '__LINEAGE__': repr(LINEAGE),
              '__ACTUAL_HEAD__': repr(CANDIDATE), '__ACTUAL_TREE__': repr(CANDIDATE_TREE),
              '__DELTA_COUNT__': str(len(DELTA)),
              '__FULL_COUNT__': str(FULL_SCOPE_COUNT), '__PREPARED_COUNT__': str(PREPARED_COUNT)}
    bound = BOUND
    for before, after in values.items():
        bound = bound.replace(before, after)
    routes = ((pending_scope_end + ROW_ANCHOR, pending_scope_end + bound + ROW_ANCHOR),
              (PENDING_LINE, SOURCE_CHECK), (status, upgraded),
              (report, '                **report, actual_current_SKU_Root_adopted=False,'),
              (fence, preserve + fence))
    revised = source
    for before, after in routes:
        if revised.count(before) != 1:
            raise ValueError('GLOBAL_EXACT_SOURCE_FENCE_ANCHOR_REQUIRED')
        revised = revised.replace(before, after, 1)
    recovered = revised
    for before, after in reversed(routes):
        if recovered.count(after) != 1:
            raise ValueError('GLOBAL_EXACT_SOURCE_FENCE_INVERSE_REQUIRED')
        recovered = recovered.replace(after, before, 1)
    if recovered.encode() != raw:
        raise ValueError('GLOBAL_SKU_FENCE_EXACT_REVERSAL_REQUIRED')
    compile(revised, 'check_source.py', 'exec', dont_inherit=True)
    return revised.encode()
