"""Layered source closure; frozen predecessor readers and source checks stay exact."""
from hashlib import sha256
from pathlib import Path
import ast
import gzip
import importlib.util
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = '911a08e04f741ead342d6436a2f4b003434c0070'
NS = 'scripts/current-s05-lawful-master-dates-qualification'
WORKFLOW = '.github/workflows/cp7-current-s05-lawful-master-dates.yml'
OLD = 'scripts/current-s05-public-default-acl-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def pins(repo, source):
    repo = Path(repo)
    for relative, expected in source['files'].items():
        path = repo/relative
        if (not path.resolve().is_relative_to(repo.resolve())
                or any(p.is_symlink() for p in (path, *path.parents) if p != repo)
                or not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError('S05_LAWFUL_PIN_CHANGED:'+relative)


def native_premise(repo=ROOT, here=HERE):
    repo, here = Path(repo), Path(here)
    declared = json.loads((here/'native-premise/PROVENANCE.json').read_bytes())
    fixture = repo/declared['fixture_path']
    raw = fixture.read_bytes()
    if len(raw) != declared['fixture_bytes'] or sha256(raw).hexdigest() != declared['fixture_sha256']:
        raise ValueError('S05_NATIVE_PREMISE_FIXTURE_CHANGED')
    text = gzip.decompress(raw).decode()
    for name, pin in declared['exact_function_definitions'].items():
        matches = list(re.finditer(r'(?i)CREATE(?: OR REPLACE)? FUNCTION erp\.'+name+r'\(', text))
        if len(matches) != 1:
            raise ValueError('S05_NATIVE_PREMISE_EXACT_FUNCTION_REQUIRED:'+name)
        tail = text[matches[0].start():]
        dollar = re.search(r'\bAS\s+(\$[A-Za-z_0-9]*\$)', tail, re.I)
        token = dollar[1]; end = tail.index(token, dollar.end())+len(token)
        exact = (tail[:end+1]+'\n').encode()
        body = tail[dollar.end():end-len(token)].encode()
        if exact != (here/pin['path']).read_bytes() or sha256(exact).hexdigest() != pin['sha256'] or sha256(body).hexdigest() != pin['prosrc_sha256']:
            raise ValueError('S05_NATIVE_PREMISE_DEFINITION_CHANGED:'+name)
    editor = declared['exact_function_definitions']['save_accessory_bom_edit']
    if editor['prosrc_sha256'] != '6c8c701395ab74874e7cb2f3e78f9912f7380a5a3199cba069b1aec6db09cd85':
        raise ValueError('S05_NATIVE_PREMISE_EDITOR_ABI_CHANGED')
    master = (repo/'scripts/cp6_bf_objects_master.sql').read_text()
    bf = declared['BF_original_source']
    raw_bf = (repo/bf['path']).read_bytes()
    if len(raw_bf) != bf['bytes'] or sha256(raw_bf).hexdigest() != bf['sha256']:
        raise ValueError('S05_NATIVE_PREMISE_BF_SOURCE_CHANGED')
    for name, pin in bf['functions'].items():
        matches = list(re.finditer(r'(?i)CREATE OR REPLACE FUNCTION erp\.'+name+r'\(', master))
        if len(matches) != 1:
            raise ValueError('S05_NATIVE_PREMISE_EXACT_BF_FUNCTION_REQUIRED:'+name)
        tail = master[matches[0].start():]
        dollar = re.search(r'\bAS\s+(\$[A-Za-z_0-9]*\$)', tail, re.I)
        token = dollar[1]; end = tail.index(token, dollar.end())+len(token)
        exact = (tail[:end+1]+'\n').encode()
        if exact != (here/pin['path']).read_bytes() or sha256(exact).hexdigest() != pin['sha256']:
            raise ValueError('S05_NATIVE_PREMISE_BF_DEFINITION_CHANGED:'+name)
    if master.count("if at_time<statement_timestamp()-interval '5 minutes'") != 1:
        raise ValueError('S05_ORIGINAL_BF_DATE_GUARD_REQUIRED')
    return dict(status='EXACT_DECLARED_NATIVE_SOURCE_PREMISE_NOT_RUNTIME_PASS',
                Native_editor_prosrc_sha256=editor['prosrc_sha256'],
                original_BF_five_minute_guard_unchanged=True,
                exact_Native_definitions=len(declared['exact_function_definitions']),
                exact_BF_definitions=len(bf['functions']), Native_executions=0)


def tracked_scope(repo=ROOT):
    repo = Path(repo)
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1')
    result = subprocess.check_output(['git', '-C', str(repo), 'diff', '--name-only', BASE, '--'], env=env).decode().splitlines()
    forbidden = [p for p in result if not (p.startswith(NS+'/') or p == WORKFLOW)]
    if forbidden:
        raise ValueError('S05_FROZEN_911_TRACKED_SOURCE_CHANGED:'+','.join(forbidden))
    return dict(base_head=BASE, all_other_911_tracked_files_unchanged=True,
                allowed_new_prefix=NS, allowed_new_workflow=WORKFLOW)


def offline(repo=ROOT, here=HERE):
    repo, here = Path(repo), Path(here)
    source = json.loads((here/'SOURCE.json').read_bytes())
    config = json.loads((here/'CONFIG.json').read_bytes())
    if (source['contract'] != 'cp7.s05-lawful-master-dates.v1'
            or config['contract'] != source['contract']
            or type(source['Native_executions']) is not int or source['Native_executions'] != 0
            or source['production_go'] is not False or source['independent_acceptance'] is not False):
        raise ValueError('S05_LAWFUL_SOURCE_NOT_ACCEPTANCE')
    pins(repo, source)
    own = {str(p.relative_to(repo)) for p in here.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in here.rglob('*')):
        raise ValueError('S05_LAWFUL_OWN_SOURCE_SYMLINK')
    expected = {p for p in source['files'] if p.startswith(NS+'/')} | {NS+'/SOURCE.json'}
    if own != expected:
        raise ValueError('S05_LAWFUL_UNDECLARED_OWN_SOURCE')
    if sha256((repo/OLD/'SOURCE.json').read_bytes()).hexdigest() != config['inherited_manifest_sha256']:
        raise ValueError('S05_LAWFUL_FROZEN_ACL_MANIFEST_CHANGED')
    inherited = load('s05_lawful_unmodified_predecessor_admission', repo/OLD/'admission.py').offline(repo, repo/OLD)
    cases = (repo/'scripts/cp7_accessory_standard_report/cases.py').read_bytes()
    if sha256(cases).hexdigest() != 'e025be1280630dfb89f62261163194ce072b6f6ad6d909b56ff6c82f75778e98':
        raise ValueError('S05_LAWFUL_ORIGINAL_CALLBACKS_CHANGED')
    tree = ast.parse(cases)
    ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
    if list(ids) != inherited['Native_case_ids'] or len(ids) != 10:
        raise ValueError('S05_LAWFUL_ORIGINAL_TEN_IDS_REQUIRED')
    _, component = load('s05_lawful_offline_one_binding', here/'component_derivation.py').derive(
        (repo/'scripts/current-s05-native10-qualification/component.py').read_bytes())
    _, recipe = load('s05_lawful_offline_two_times', here/'recipe.py').successor_source(cases)
    failure = load('s05_lawful_offline_first_911', here/'first_failure.py').checked(here)
    workflow = load('s05_lawful_offline_full_workflow', here/'workflow_source.py').checked((repo/WORKFLOW).read_text(), repo)
    scope = tracked_scope(repo)
    return dict(status='EXACT_FROZEN_S05_NATIVE10_WITH_LAWFUL_MASTER_FIXTURE_PREPARED',
                source_files=len(source['files']), qualification=source,
                qualification_source_sha256=sha256((here/'SOURCE.json').read_bytes()).hexdigest(),
                Native_case_ids=list(ids), inherited=inherited,
                component_derivation=component, recipe_time_derivation=recipe,
                native_source_premise=native_premise(repo, here), first_failure=failure,
                workflow_derivation=workflow, tracked_scope=scope,
                new_product_SQL_or_Native_writer_or_oracle_changes=0,
                Native_executions=0, database_calls=0, production_go=False, independent_acceptance=False)
