"""Early stdlib-only whole-source admission before importing any old module."""
from hashlib import sha1, sha256
from pathlib import Path, PurePosixPath
import importlib.util
import json
import os
import re
import stat
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = '80fab765938f8feaff151cd35fdb7923df987f23'
BASE_TREE = '9161822776b958a60cbe845f7a56d96c31db3dc5'
BCE = 'bce07059f7a351372e40bb7c2e4453876320a2e8'
NS = 'scripts/current-de-sku-global-census-qualification/'
PARENT = 'scripts/current-de-sku-parent-catalogue-qualification/'
HELPER = 'scripts/current-global-actual-writer-census-qualification/'
WORKFLOW = '.github/workflows/cp7-de-sku-global-census.yml'
NAME = 'CP7 A D1 E SKU global writer metadata and full restoration'
CASE = 'D1_E_SKU_GLOBAL_WRITER_CENSUS_SOURCE_ONLY'
LABEL = 'CP7_D1_E_SKU_GLOBAL_CENSUS'


def require(ok, message):
    if not ok: raise ValueError(message)


def document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'GLOBAL_CENSUS_SOURCE_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('GLOBAL_CENSUS_SOURCE_NONFINITE_JSON')))


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def git(*args, root=ROOT):
    return subprocess.check_output(['/usr/bin/git', '-C', str(root), *args],
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))


def regular(name, root=ROOT):
    require(type(name) is str, 'GLOBAL_CENSUS_UNSAFE_SOURCE_PATH')
    rel = PurePosixPath(name)
    require(type(name) is str and bool(rel.parts) and not rel.is_absolute()
            and '..' not in rel.parts and '\\' not in name and str(rel) == name,
            'GLOBAL_CENSUS_UNSAFE_SOURCE_PATH')
    root = Path(root); path = root
    for part in rel.parts:
        path = path / part
        require(not path.is_symlink(), 'GLOBAL_CENSUS_SOURCE_LINK:' + name)
    require(path.is_file() and stat.S_ISREG(path.stat().st_mode), 'GLOBAL_CENSUS_SOURCE_REGULAR_FILE_REQUIRED:' + name)
    return path


def checked(name, expected, root=ROOT):
    path = regular(name, root); raw = path.read_bytes()
    require(pin(raw) == {key: expected[key] for key in ('bytes', 'sha256')}, 'GLOBAL_CENSUS_SOURCE_BYTES_CHANGED:' + name)
    require(expected.get('mode') in ('100644', '100755')
            and bool(path.stat().st_mode & 0o111) == (expected['mode'] == '100755'),
            'GLOBAL_CENSUS_SOURCE_MODE_CHANGED:' + name)
    return raw


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def immutable_parent(root=ROOT):
    require(git('rev-parse', BASE + '^{tree}', root=root).decode().strip() == BASE_TREE,
            'GLOBAL_CENSUS_EXACT_PUBLIC_HELPER_PARENT_TREE_REQUIRED')
    count = 0
    for entry in git('ls-tree', '-rz', BASE, root=root).split(b'\0'):
        if not entry: continue
        metadata, name = entry.split(b'\t', 1); mode, kind, blob = metadata.decode().split(); name = name.decode()
        require(kind == 'blob' and mode in ('100644', '100755'), 'GLOBAL_CENSUS_PARENT_OBJECT_TYPE_CHANGED')
        path = regular(name, root); raw = path.read_bytes()
        require(sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob,
                'GLOBAL_CENSUS_IMMUTABLE_WHOLE_PARENT_CHANGED:' + name)
        require(bool(path.stat().st_mode & 0o111) == (mode == '100755'), 'GLOBAL_CENSUS_PARENT_MODE_CHANGED:' + name)
        count += 1
    return count


def outputs(names, root=ROOT):
    """Only called after every source byte and mode has been admitted."""
    accepted = set(); proofs = {}
    history = document(regular('scripts/current-workflow-history-isolation/ARCHIVE.json', root).read_bytes())
    sku_profile = document(regular(NS + 'SKU_GENERATED_RECEIPTS.json', root).read_bytes())
    prefix = 'cp6-proof/t3/'
    fixed = {prefix + name for name in (
        'FROZEN_SOURCE_WORKTREES.json','ALIGNED_CHAIN.json','CLONE_install.txt',
        'CLONE_install.connection-fence.txt','CLONE_install.database-identity.txt',
        'CLONE_install.source-erp.sql','CLONE_install.clone-erp.sql',
        'T3_PACKAGE_FILES_INSTALL.json','T3_PACKAGE_INSTALL.json','SKU_TARGETED_CLIENT.json',
        'T3_BACKUP_RESTORE_DRILL.json','GLOBAL_ACTUAL_WRITER_SUPPLEMENT.json',LABEL + '.json',
        'disposable-startup-attempts/STARTUP_ATTEMPTS.json')}
    fixed.update(row['path'] for row in history['files'])
    fixed.update(prefix + 'RETAINED_SKU21C/' + name for name in sku_profile['retained21_files'])
    patterns = (r'cp6-proof/t3/ARTIFACT_FETCH/[0-9a-f]{32}-[1-3]\.(?:json|stdout\.txt|stderr\.txt)',
                r'cp6-proof/t3/disposable-startup-attempts/attempt-[1-4]-(?:start|stop)\.log')
    # Reject unknown paths and every symlink before ANY old output-reader
    # import. The exact inherited readers below still validate full contents.
    require(all(name in fixed or any(re.fullmatch(pattern, name) for pattern in patterns) for name in names),
            'GLOBAL_CENSUS_UNKNOWN_UNTRACKED_SOURCE_BEFORE_IMPORT')
    for name in names: regular(name, root)
    for label, filename in (('early', 'generated_receipts.py'), ('later', 'generated_later.py'), ('SKU', 'generated_sku.py')):
        # These exact bce readers accept the explicit HERE parameter. No old
        # implementation, global, manifest, or function is monkeypatched.
        reader = load('global_census_output_' + label, Path(root) / PARENT / filename)
        found, proof = reader.admit(root, Path(root) / NS, names)
        require(not accepted & set(found), 'GLOBAL_CENSUS_OUTPUT_CLASS_OVERLAP')
        accepted.update(found); proofs[label] = proof
    for row in history['files']:
        name = row['path']
        if name in names:
            raw = regular(name, root).read_bytes()
            require(pin(raw) == {key: row[key] for key in ('bytes', 'sha256')}
                    and raw == regular(row['archive'], root).read_bytes(), 'GLOBAL_CENSUS_ARCHIVED_WORKFLOW_OUTPUT_CHANGED')
            accepted.add(name)
    original = 'cp6-proof/t3/GLOBAL_ACTUAL_WRITER_SUPPLEMENT.json'
    report_name = 'cp6-proof/t3/' + LABEL + '.json'
    if original in names or report_name in names:
        require({original, report_name} <= set(names), 'GLOBAL_CENSUS_PARTIAL_NEW_ORIGINAL_OUTPUT')
        report = document(regular(report_name, root).read_bytes())
        require(report.get('label') == LABEL and report.get('qualification_commit') == git('rev-parse', 'HEAD', root=root).decode().strip(),
                'GLOBAL_CENSUS_OUTPUT_REPORT_IDENTITY_CHANGED')
        case = report['committed'][CASE]
        integration = load('global_census_original_output_reader', Path(root) / HELPER / 'integration.py')
        integration.read_original(Path(root) / 'cp6-proof/t3', case['global_writer_supplemental_reference'], case['read_before']['catalog'])
        accepted.update((original, report_name))
        proofs['supplement'] = dict(classification='SEPARATE_ORIGINAL_OUTPUT_ONLY_NOT_RUNTIME_PASS',
                                   actual_Native_credit=0, source_authority=False)
    # The gate runs after the inherited package has produced its full restore
    # drill. This is only a closed output class; the complete inherited gate
    # still checks report restoration and all five package obligations.
    drill_name = 'cp6-proof/t3/T3_BACKUP_RESTORE_DRILL.json'
    if drill_name in names:
        drill = document(regular(drill_name, root).read_bytes())
        require(set(drill) == {'label','status','source','target','installed_stages','production_go',
            'release_evidence','dump','restore','catalog','data','engine','source_cron_jobs','checks'},
            'GLOBAL_CENSUS_RESTORE_OUTPUT_FIELDS_CHANGED')
        require(drill['label'] == 'T3_PREP_BACKUP_RESTORE_DRILL' and drill['source'] == 'cp6_rollback'
            and drill['target'] == 'cp6_restore_drill' and drill['production_go'] is False
            and drill['release_evidence'] is False, 'GLOBAL_CENSUS_RESTORE_OUTPUT_SCOPE_CHANGED')
        require(drill['status'] == 'RESTORED_IDENTICAL' and set(drill['checks']) == {
            'restore_errors_only_pg_cron','catalog_explained','data_identical','engine_answer_present','engine_equal'}
            and all(v is True for v in drill['checks'].values()), 'GLOBAL_CENSUS_RESTORE_OUTPUT_INCOMPLETE')
        accepted.add(drill_name)
        proofs['restore_drill'] = dict(classification='COMPLETE_RESTORE_OUTPUT_ONLY_NOT_RUNTIME_AUTHORITY',
                                      actual_Native_credit=0)
    require(set(names) <= accepted, 'GLOBAL_CENSUS_UNKNOWN_UNTRACKED_SOURCE:' + ','.join(sorted(set(names) - accepted)))
    return proofs


def preflight(require_clean=True, root=ROOT):
    root = Path(root)
    seal = regular(NS + 'SOURCE.json', root)
    require(not seal.stat().st_mode & 0o111, 'GLOBAL_CENSUS_SOURCE_SEAL_MODE_CHANGED')
    cfg = document(seal.read_bytes())
    require(cfg.get('base') == BASE and cfg.get('base_tree') == BASE_TREE and cfg.get('original_catalogue_source') == BCE,
            'GLOBAL_CENSUS_EXACT_SUCCESSOR_BASE_REQUIRED')
    require(cfg.get('runtime_entry') is None and 'runtime_entry' in cfg
            and cfg.get('metadata_only_entry') == NS + 'probe.py --metadata-runtime'
            and type(cfg.get('actual_Native_credit')) is int and cfg['actual_Native_credit'] == 0
            and cfg.get('production_go') is False and cfg.get('independent_acceptance') is False,
            'GLOBAL_CENSUS_METADATA_ONLY_SOURCE_REQUIRED')
    count = immutable_parent(root)
    files = cfg['files']; require(type(files) is dict and bool(files), 'GLOBAL_CENSUS_NONEMPTY_SOURCE_SET_REQUIRED')
    allowed = set(files) | {NS + 'SOURCE.json'}
    require(all(name.startswith(NS) or name == WORKFLOW for name in allowed), 'GLOBAL_CENSUS_SUCCESSOR_SCOPE_ESCAPE')
    for name, expected in files.items(): checked(name, expected, root)
    own = {str(p.relative_to(root)) for p in (root / NS).rglob('*') if p.is_file() or p.is_symlink()}
    require(own == {name for name in allowed if name.startswith(NS)}, 'GLOBAL_CENSUS_EXACT_OWN_SOURCE_SET_REQUIRED')
    changed = set(git('diff', '--name-only', BASE, 'HEAD', root=root).decode().splitlines())
    require(changed <= allowed, 'GLOBAL_CENSUS_UNDECLARED_COMMITTED_SOURCE')
    # No old imports occurred above. Source/profile readers below are now exact.
    profiles = load('global_census_profiles_after_source', root / NS / 'producer_profiles.py').validate(root)
    generated = {}
    if require_clean:
        require(not git('status', '--porcelain', '--untracked-files=no', root=root).strip(), 'GLOBAL_CENSUS_DIRTY_TRACKED_SOURCE')
        require(changed == allowed, 'GLOBAL_CENSUS_COMMITTED_SOURCE_SET_INCOMPLETE')
        names = {n.decode() for n in git('ls-files', '--others', '--exclude-standard', '-z', root=root).split(b'\0') if n}
        generated = outputs(names, root)
    return dict(status='EXACT_WHOLE_80FAB_TREE_PLUS_BOUNDED_METADATA_SUCCESSOR', parent_files=count,
        successor_files=len(files), profile_transitions=profiles, generated_output_proofs=generated,
        old_frozen_guards_edited=False, old_source_manifests_resealed=False, old_runtime_qualification_inferred=False,
        metadata_only_entry=cfg['metadata_only_entry'], runtime_entry=None, actual_Native_credit=0,
        production_go=False, independent_acceptance=False)


def admitted(repo=None, here=None, product=None):
    proof = preflight()
    if product is not None:
        require(Path(product.__file__).resolve() == (ROOT / PARENT / 'stage.py').resolve(),
                'GLOBAL_CENSUS_EXACT_UNCHANGED_PARENT_STAGE_REQUIRED')
        proof['actual_stage_sources'] = product.sources()
    return proof
