"""Check retained sources and bind only through the existing closed owner."""
from argparse import ArgumentParser
from contextlib import contextmanager
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import CodeType
from uuid import uuid4
import ast
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

from auth_adapter import Attempt, require
import cleanup_routes
from local_rest import OwnedRest

HERE = Path(__file__).resolve().parent
OWNING = 'daily-audit-20261112/agents/global-owning-caller-sku457/'
SKU = 'scripts/current-sku-automatic-composite-preparation/'
DONOR = 'scripts/current-vendor-receivable-qualification/probe.py'
MODES = 'scripts/cp6_auditor_modes.py'
COMPLETE_IO = 'scripts/cp7_accessory_nonpayable/complete_original_io.py'
HEAD = '56e7b238e68620c5cc172b7961c83a46bda8783a'
TREE = '3b043abbc3f62d73a7986142d435ba3badfcbb04'


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def read(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(node.is_symlink() for node in (path, *path.parents)), 'REGULAR_PINNED_SOURCE_REQUIRED')
    return path.read_bytes()


def declaration():
    value = json.loads(read(HERE / 'SOURCE.json'))
    require(value['git_head'] == HEAD and value['git_tree'] == TREE and len(value['candidate_files']) == 22
            and len(value['retained_files']) == 8 and value['runtime_admission'] is False,
            'EXACT_CLOSED_SOURCE_MANIFEST_REQUIRED')
    return value


def git_sources(repo, manifest):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    require(git('rev-parse', HEAD + '^{tree}').decode().strip() == TREE, 'EXACT_IMMUTABLE_SKU_SOURCE_TREE_REQUIRED')
    return {name: git('show', HEAD + ':' + name) for name in manifest['candidate_files']}


def require_pins(raw, pins):
    require(raw.keys() == pins.keys() and all(pin(raw[name]) == value for name, value in pins.items()),
            'EXACT_SOURCE_BYTES_CHANGED')


def load(path, label):
    spec = spec_from_file_location(label, path)
    module = module_from_spec(spec)
    exec(compile(read(path), str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def code_at(code, *parts):
    for part in parts:
        matches = [value for value in code.co_consts if isinstance(value, CodeType) and value.co_name == part]
        require(len(matches) == 1, 'UNIQUE_RETAINED_FUNCTION_CODE_REQUIRED')
        code = matches[0]
    return code


def exact_module_functions(module, raw, *routes):
    code = compile(raw, str(Path(module.__file__)), 'exec', dont_inherit=True)
    for route in routes:
        owner = module
        for part in route:
            owner = getattr(owner, part)
        require(owner.__code__ == code_at(code, *route) and owner.__globals__ is module.__dict__
                and owner.__closure__ is None, 'EXACT_LIVE_FUNCTION_CODE_REQUIRED')


@contextmanager
def source_fence():
    attempts = []
    active = True

    def refuse(event, args):
        if active and (event.startswith('socket.') or event in ('urllib.Request', 'http.client.connect', 'subprocess.Popen')):
            attempts.append(event)
            raise RuntimeError('GLOBAL_AUTH_SOURCE_IO_REFUSED')

    sys.addaudithook(refuse)
    try:
        yield attempts
        require(not attempts, 'SOURCE_FENCE_ATTEMPTED_RUNTIME')
    finally:
        active = False


def source_check(workspace, repo):
    manifest = declaration()
    candidate = git_sources(repo, manifest)
    require_pins(candidate, manifest['candidate_files'])
    retained = {name: read(Path(workspace) / name) for name in manifest['retained_files']}
    require_pins(retained, manifest['retained_files'])
    with tempfile.TemporaryDirectory(prefix='cp7-global-auth-pinned-sources-') as temp, source_fence() as attempts:
        directory = Path(temp)
        for name, raw in (candidate | retained).items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        sku = load(directory / SKU / 'package.py', 'exact_retained_sku_package_derivation')
        package = load(directory / OWNING / 'package_routes.py', 'exact_retained_global_package_derivation')
        sku_source, sku_proof = sku.derive(candidate[DONOR], focused=True)
        global_source, global_proof = package.derive(sku_source)
        revised, auth_proof = cleanup_routes.derive(global_source)
        require(sku_proof['source_sha256'] == global_proof['parent_sha256']
                and global_proof['derived_sha256'] == auth_proof['retained_sha256'], 'UNBROKEN_DONOR_DERIVATION_REQUIRED')
        owner = ast.parse(retained[OWNING + 'owning.py'])
        assignments = {node.targets[0].id: node.value for node in owner.body if isinstance(node, ast.Assign)
                       and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}
        gates = assignments['GATES'].keywords
        require(len(gates) == 8 and all(isinstance(item.value, ast.Constant) and item.value.value is None for item in gates)
                and isinstance(assignments['REVIEWED_FIXTURES'], ast.Constant)
                and assignments['REVIEWED_FIXTURES'].value is None, 'EXISTING_ADMISSION_GATES_MUST_STAY_CLOSED')
        package_code = compile(candidate['scripts/cp6_t3_package_run.py'], '<retained T3 package>', 'exec', dont_inherit=True)
        outer = code_at(package_code, 'run')
        require('--force' in repr(outer.co_consts) and 'primary_unchanged' in repr(outer.co_consts),
                'EXACT_OUTER_T3_FORCEDISCARD_AND_PRIMARY_PROOF_REQUIRED')
        modes = compile(candidate[MODES], '<retained Auth wire>', 'exec', dont_inherit=True)
        for route in (('_call',), ('_status_env',), ('Http', '_auth'), ('Http', '_rpc'), ('HttpUser', 'rpc')):
            code_at(modes, *route)
        patch = ''.join(difflib.unified_diff(global_source.splitlines(keepends=True), revised.splitlines(keepends=True),
                                             'retained/global_owning_writer.py', 'proposal/global_owning_writer.py'))
    return (dict(status='CLOSED_GLOBAL_AUTH_RECOVERY_SOURCE_CHECKED', exact_source_pins=30,
                 candidate=dict(head=HEAD, tree=TREE), original_admission={item.arg: None for item in gates},
                 reviewed_fixtures=None, donor_bytes=manifest['candidate_files'][DONOR],
                 retained_outer_T3=manifest['candidate_files']['scripts/cp6_t3_package_run.py'],
                 auth_routes=auth_proof, source_fence_attempts=attempts, runtime_admission=False,
                 actual_ERP_cases=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
                 retained_donor_round_trip=True, patch=pin(patch.encode())), patch)


def make_attempt(owner, candidate, modes, originals, *, actor_plan, rpc_plan):
    owner.require_gates()
    candidate = Path(candidate).absolute()
    owner.fixture_location(candidate)
    manifest = declaration()['candidate_files']
    modes_path = Path(modes.__file__).absolute()
    modes_raw = read(modes_path)
    require(modes_path == candidate / MODES and pin(modes_raw) == manifest[MODES], 'EXACT_CANDIDATE_AUTH_WIRE_REQUIRED')
    exact_module_functions(modes, modes_raw, ('_call',), ('_status_env',), ('Http', '_auth'), ('Http', '_rpc'),
                           ('HttpUser', '__init__'), ('HttpUser', 'rpc'))
    io_raw = read(originals.__file__)
    require(pin(io_raw) == manifest[COMPLETE_IO], 'EXACT_ORIGINALS_WRITER_REQUIRED')
    exact_module_functions(originals, io_raw, ('save_sorted',))
    require(type(actor_plan) is tuple and bool(actor_plan)
            and all(type(item) is tuple and len(item) == 2 and all(type(value) is str for value in item)
                    and re.fullmatch(r'[A-Z][A-Z0-9_]{1,39}', item[0])
                    and re.fullmatch(r'[a-zA-Z0-9_-]{1,48}', item[1]) for item in actor_plan)
            and len(set(actor_plan)) == len(actor_plan),
            'EXACT_REVIEWED_ACTOR_PLAN_REQUIRED')
    require(type(rpc_plan) is tuple and bool(rpc_plan)
            and all(type(name) is str and re.fullmatch(r'[a-z][a-z0-9_]{1,79}', name) for name in rpc_plan)
            and len(set(rpc_plan)) == len(rpc_plan),
            'EXACT_REVIEWED_RPC_PLAN_REQUIRED')
    run, ordinal, head = (os.environ.get(key, '') for key in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA'))
    require(re.fullmatch(r'[1-9][0-9]{0,17}', run) and re.fullmatch(r'[1-9][0-9]{0,3}', ordinal)
            and re.fullmatch(r'[a-f0-9]{40}', head), 'EXACT_OWNING_RUN_IDENTITY_REQUIRED')
    attempt = run + '-' + ordinal
    transport = OwnedRest(modes, candidate, attempt, uuid4().hex[:12])
    output = candidate / 'cp6-proof/t3'

    def retain(name, value):
        output.mkdir(parents=True, exist_ok=True)
        return originals.save_sorted(output / name, value, 'GLOBAL_AUTH_CONFLICTING_OWNING_ORIGINAL')

    return Attempt(connect=lambda *args, **kwargs: modes.psycopg.connect(*args, **kwargs), transport=transport,
                   retain=retain, attempt=attempt, allowed_actors=actor_plan, allowed_rpcs=rpc_plan, head=head)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--patch', type=Path)
    args = parser.parse_args()
    result, patch = source_check(args.workspace, args.repo)
    if args.patch is not None:
        args.patch.write_text(patch)
    print(json.dumps(result, indent=2, sort_keys=True))
