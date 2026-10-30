"""Lossless private qualification derivation of exactly three old callbacks."""
from pathlib import Path
from hashlib import sha256
from types import ModuleType
import ast
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = 'scripts/current-attendance-period-choice-qualification/cases.py'
READER = 'scripts/current-attendance-period-choice-readers-qualification/cases.py'
READER_SHA = 'eebe27396c93d4b2b14062f778a4f6a4a9c9ae840bed164e11196d90bc603630'
READER_BEFORE = "        payroll=f.earned(cur,s['contractor'],out,D('20.02'))"
READER_AFTER = "        payroll=LAWFUL.earned(cur,s,out,D('20.02'),core=core,evidence=evidence)"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def substitute(raw, pairs):
    value = raw.decode()
    for before, after in pairs:
        if before == after or value.count(before) != 1:
            raise ValueError('S03_LAWFUL_ONE_EXACT_PRIVATE_ANCHOR_REQUIRED')
        value = value.replace(before,after,1)
    restored = value
    for before, after in reversed(pairs):
        if restored.count(after) != 1:
            raise ValueError('S03_LAWFUL_ONE_REVERSE_PRIVATE_ANCHOR_REQUIRED')
        restored = restored.replace(after,before,1)
    if restored.encode() != raw:
        raise ValueError('S03_LAWFUL_LOSSLESS_ORIGINAL_REQUIRED')
    return value, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(value.encode()).hexdigest(),
        counted_changes=len(pairs), reverse_restores_all_original_bytes=True)


def derive(raw):
    contract = json.loads((HERE/'CALLBACK_CHANGES.json').read_bytes())
    if sha256(raw).hexdigest() != contract['original_sha256']:
        raise ValueError('S03_LAWFUL_ORIGINAL15FE_REQUIRED')
    changes = contract['changes']
    if len(changes) != 3 or [r['function']for r in changes] != ['coexist','corrections','finished']:
        raise ValueError('S03_LAWFUL_EXACT_THREE_CALLBACKS_REQUIRED')
    value, proof = substitute(raw,[(r['before'],r['after'])for r in changes])
    old_tree,new_tree = ast.parse(raw),ast.parse(value)
    def functions(tree):
        factory = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='cases')
        return {n.name:ast.dump(n,include_attributes=False)for n in factory.body if isinstance(n,ast.FunctionDef)}
    old,new = functions(old_tree),functions(new_tree)
    if old.keys()!=new.keys() or {k for k in old if old[k]!=new[k]} != {r['function']for r in changes}:
        raise ValueError('S03_LAWFUL_CALLBACK_SCOPE_CHANGED')
    # Drop only the factory before comparing every top-level helper/import/ID.
    strip = lambda tree:[ast.dump(n,include_attributes=False)for n in tree.body if not(isinstance(n,ast.FunctionDef)and n.name=='cases')]
    if strip(old_tree)!=strip(new_tree):
        raise ValueError('S03_LAWFUL_ORIGINAL_HELPER_OR_USED_WITNESS_CHANGED')
    return value,dict(proof, adapted_callback_ids=[r['case']for r in changes],
        original_eight_callbacks_unchanged=True, original_helpers_and_committed_witness_unchanged=True,
        original_eleven_runtime_callbacks_byte_exact=False, original_financial_assertions_retained_except_named_false_cache_predicate=True)


def runtime():
    raw = (ROOT/ORIGINAL).read_bytes(); value,proof = derive(raw)
    module = ModuleType('s03_lawful_private_three_callbacks_eight_exact')
    module.__file__ = str(ROOT/ORIGINAL)
    module.LAWFUL = load('s03_lawful_explicit_fixture_API',HERE/'lawful_fixture.py')
    module.CORE = module
    exec(compile(value,module.__file__,'exec'),module.__dict__)
    module.PRIVATE_DERIVATION = proof
    return module


def reader_runtime():
    raw = (ROOT/READER).read_bytes()
    if sha256(raw).hexdigest()!=READER_SHA:
        raise ValueError('S03_LAWFUL_READER_ORIGINAL_EEBE_REQUIRED')
    value,proof = substitute(raw,[(READER_BEFORE,READER_AFTER)])
    module = ModuleType('s03_lawful_private_reader3_same_explicit_P2_API')
    module.__file__ = str(ROOT/READER)
    module.LAWFUL = load('s03_lawful_Reader3_explicit_fixture_API',HERE/'lawful_fixture.py')
    exec(compile(value,module.__file__,'exec'),module.__dict__)
    module.PRIVATE_DERIVATION = dict(proof, financial_reader_oracles_unchanged=True,
        only_active_disjoint_callback_P2_fixture_changed=True, global_monkeypatch=False)
    return module
