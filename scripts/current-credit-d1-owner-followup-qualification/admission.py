"""Explicit source child and original Native13 admission; no SQL on import."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import gzip
import importlib.util
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-credit-d1-owner-followup-qualification/'
CONT = 'scripts/current-credit-d1-continuation-qualification/'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def cfg():
    return json.loads((HERE/'CONFIG.json').read_bytes())


def source_only():
    config, source = cfg(), json.loads((HERE/'SOURCE.json').read_bytes())
    for name, pin in source['files'].items():
        raw = (ROOT/name).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('D1_CONT_DECLARED_CHILD_SOURCE_CHANGED:'+name)
    git = lambda *args: subprocess.check_output(['git','-C',str(ROOT),*args])
    if git('rev-parse',config['frozen_parent_head']+'^{tree}').decode().strip() != config['frozen_parent_tree']:
        raise ValueError('D1_CONT_EXACT_FROZEN_PARENT_TREE_REQUIRED')
    for name, digest in source['frozen_parent_files'].items():
        raw = (ROOT/name).read_bytes()
        if raw != git('show',config['frozen_parent_head']+':'+name) or sha256(raw).hexdigest() != digest:
            raise ValueError('D1_CONT_FROZEN_D1_PARENT_CHANGED:'+name)
    actual = set(git('diff','--name-only',config['frozen_parent_head'],'HEAD').decode().splitlines())
    if not actual <= set(source['allowed_child_paths']):
        raise ValueError('D1_CONT_UNALLOCATED_CHILD_PATH')
    if git('status','--porcelain','--untracked-files=no').strip():
        raise ValueError('D1_CONT_CLEAN_COMMITTED_SOURCE_REQUIRED')
    if json.loads((ROOT/'scripts/current-credit-de-native-qualification/SOURCE.json').read_bytes()) != source['frozen_D1_source']:
        raise ValueError('D1_CONT_FROZEN_D1_DECLARATION_CHANGED')
    load('continuation_bounded_original_transition',HERE/'transition.py').check()
    failure = config['retained_failed_a994']
    load('continuation_retained_failure_gate',HERE/'gate.py').retained_failure(config,gzip.decompress((ROOT/failure['path']).read_bytes()))
    return source


def historical_D1_admission(raw, parent):
    if not re.fullmatch('[a-f0-9]{40}', parent):
        raise ValueError('D1_CONT_EXPLICIT_PUBLIC_PARENT_COMMIT_REQUIRED')
    old = "changed = git('diff', '--name-only', cfg['base_head'], 'HEAD').decode().splitlines()"
    new = "changed = git('diff', '--name-only', cfg['base_head'], '"+parent+"').decode().splitlines()"
    text = raw.decode()
    if text.count(old) != 1:
        raise ValueError('D1_CONT_EXACT_HISTORICAL_ADMISSION_ANCHOR_REQUIRED')
    return text.replace(old,new,1), dict(counted_changes=1,original_sha256=sha256(raw).hexdigest(),
        fixed_historical_diff_head=parent,all_current_old_hash_checks_retained=True)


def retained(product, source):
    config = cfg(); gate = load('continuation_actual_parent_gate',HERE/'gate.py'); pin = gate.selected(config)
    folder = Path(os.environ['CP7_D1_CONT_NATIVE13_ORIGINALS'])
    raw = {key:(folder/pin[key]['name']).read_bytes()for key in gate.ORIGINALS}
    ids = json.loads((ROOT/'scripts/current-credit-de-native-qualification/CONFIG.json').read_bytes())['native_case_ids']
    return gate.admitted(config,raw,product.sources(),source['frozen_D1_source'],ids)


@load('continuation_scoped_admission_arguments',HERE/'argv_scope.py').inherited_entrypoint
def admitted(product, derivation):
    config = cfg(); load('continuation_closed_before_runtime',HERE/'gate.py').selected(config)
    source = source_only(); proof, _ = retained(product,source)
    original = ROOT/'scripts/current-credit-de-native-qualification/admission.py'
    text, historical = historical_D1_admission(original.read_bytes(),config['frozen_parent_head'])
    old = ModuleType('continuation_frozen_historical_D1_admission'); old.__file__ = str(original)
    exec(compile(text,str(original),'exec'),old.__dict__)
    prior = old.admitted(ROOT,original.parent,product,derivation)
    if prior['current_installation'] != product.sources() or derivation != config['runner_derivation']:
        raise ValueError('D1_CONT_EXACT_CURRENT_PARENT_AND_SIX_CHANGE_ENGINE_REQUIRED')
    return dict(status='EXACT_QUALIFIED_D1_AND_CONTINUATION3_SOURCE_ADMITTED',qualification=source,
        current_installation=prior['current_installation'],retained_Native13=proof,
        historical_D1_admission=prior,historical_scope_derivation=historical,runner_derivation=derivation,
        actual_Native_case_ids=config['fresh_native_case_ids'],retained_Native13_reexecuted=False,
        fresh_cases_credited=0,D_complete=False,E_complete=False,production_go=False,independent_acceptance=False)
