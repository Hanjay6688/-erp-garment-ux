"""Replay the published SKU input setup in a fresh worktree, without a database."""

import argparse
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import re
import socket
import subprocess

import yaml


HEAD = 'a62504d71a6ca1cdbaa59b6fe0fd5739693f100a'
TREE = 'df64669b64e82f4b5027ccad837cc3d014dbcafa'
WORKFLOW = '.github/workflows/cp7-sku-current-parent-money-automatic-native25.yml'
WORKFLOW_SHA = '03e3d898c5efb5e32830ab7d2fffe35a158e08b164329840f44217beb9991567'
# Exact setup steps, with tool installation handled by the private workflow.
# Native, browser, database and SKU owning execution steps stay outside this list.
PREPARATION = (2, 4, 5, 6, 7, 8, *range(12, 46), *range(47, 66), 66)
WORKSPACE_EXPR = '${{ github.workspace }}'
EVIDENCE_PATHS = ('docs/cp7/evidence/p00', 'docs/cp7/evidence/p19', 'docs/cp7/evidence/integration-ab4')
TRIGGER_GUARD = 'scripts/cp7_customer_credit/integration/source_triggers/trigger_guard.py'
# The four retained downloads in step 64 can outlast the normal step deadline.
STEP_TIMEOUT = {64: 900}


def git(root, *args):
    return subprocess.check_output(('git', '-C', str(root), *args), text=True).strip()


def settings(path):
    values = {}
    for line in path.read_text().splitlines():
        name, sep, value = line.partition('=')
        if not sep or not name.isidentifier():
            raise ValueError('UNEXPECTED_RETAINED_WORKFLOW_SETTING')
        values[name] = value
    return values


def checkout_scope(root, args, environment, scratch):
    with (scratch / f'materialize-{root.name}.log').open('ab') as log:
        process = subprocess.run(('git', '-C', str(root), 'sparse-checkout', *args),
                                 env=environment, stdout=log, stderr=subprocess.STDOUT,
                                 timeout=240, check=False)
    if process.returncode:
        raise RuntimeError(f'CHECKOUT_MATERIALIZATION_FAILED:{root.name}')


def materialize_checkout(root, environment, scratch, head, tree):
    # Full source guards hash the physical files, including tracked evidence.
    checkout_scope(root, ('disable',), environment, scratch)
    if (git(root, 'rev-parse', 'HEAD'), git(root, 'rev-parse', 'HEAD^{tree}')) != (head, tree):
        raise ValueError(f'FULL_CHECKOUT_SOURCE_CHANGED:{root.name}')


def verify_live_trigger_sources(backend):
    spec = spec_from_file_location('retained_ow04_trigger_guard', backend / TRIGGER_GUARD)
    guard = module_from_spec(spec)
    spec.loader.exec_module(guard)
    manifest = guard.declarations(backend)
    print('RETAINED_SKU_LIVE_TRIGGER_SOURCES_VERIFIED',
          len(manifest['repository_source_pins']), flush=True)


def prepare(root, temp, *, settings_file=None):
    auditor = root / 'auditor'
    if git(auditor, 'rev-parse', 'HEAD') != HEAD or git(auditor, 'rev-parse', 'HEAD^{tree}') != TREE:
        raise ValueError('SKU_INPUTS_REQUIRE_EXACT_PUBLIC_SOURCE')
    data = (auditor / WORKFLOW).read_bytes()
    if sha256(data).hexdigest() != WORKFLOW_SHA:
        raise ValueError('SKU_INPUTS_REQUIRE_EXACT_WORKFLOW_BYTES')
    job = yaml.load(data, Loader=yaml.BaseLoader)['jobs']['p21']
    scratch = temp / 'cp7-inputs'
    scratch.mkdir(mode=0o700)
    environment = dict(os.environ)
    environment.update({name: value.replace(WORKSPACE_EXPR, str(root)) for name, value in job['env'].items()})
    environment.update(GITHUB_WORKSPACE=str(root), GIT_TERMINAL_PROMPT='0')
    for port in (54321, 54322, 54323, 54329):
        with socket.socket() as listener:
            if listener.connect_ex(('127.0.0.1', port)) == 0:
                raise ValueError('SKU_INPUTS_EXPECT_NO_DISPOSABLE_DATABASE')
    outputs = {}
    for index in PREPARATION:
        if index == 65:
            print('Materialize the complete auditor tree for the retained source check.', flush=True)
            materialize_checkout(auditor, environment, scratch, HEAD, TREE)
        step = job['steps'][index]
        command = step['run']
        name = ' '.join(step['name'].split())
        here = root / step.get('working-directory', '.')
        step_env = dict(environment)
        variables = scratch / 'environment'
        extra_path = scratch / 'path'
        github_output = scratch / 'output'
        for file in (variables, extra_path, github_output):
            file.write_text('')
        step_env.update(GITHUB_ENV=str(variables), GITHUB_PATH=str(extra_path), GITHUB_OUTPUT=str(github_output))
        for key, value in step.get('env', {}).items():
            if value == '${{ github.token }}':
                assert key == 'GH_TOKEN' and environment.get('GH_TOKEN')
                step_env[key] = environment['GH_TOKEN']
            elif value in ('${{ steps.qualified_heads.outputs.B }}', '${{ steps.qualified_heads.outputs.native }}'):
                output_name = value.removesuffix(' }}').rsplit('.', 1)[-1]
                step_env[key] = outputs[output_name]
            else:
                raise ValueError('UNEXPECTED_RETAINED_WORKFLOW_EXPRESSION')
        print(f'SKU input preparation {index:02d}: {name}', flush=True)
        log_path = scratch / f'step-{index:02d}.log'
        deadline = str(STEP_TIMEOUT.get(index, 360))
        with log_path.open('wb') as log:
            result = subprocess.run(
                ('timeout', '--kill-after=10s', deadline, 'bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c', command),
                cwd=here, env=step_env, stdout=log, stderr=subprocess.STDOUT, check=False,
            )
        if result.returncode in (124, 137, -9):
            print(f'Retained input deadline: step={index:02d} seconds={deadline}', flush=True)
        if result.returncode:
            tail = log_path.read_bytes()[-16384:].decode(errors='replace')
            for row in tail.splitlines():
                match = re.fullmatch(r'(?:ValueError|AssertionError): ([A-Z][A-Z0-9_]{7,110})(?::.*)?', row)
                if match:
                    print('Retained input check:', match[1], flush=True)
            if 'CalledProcessError:' in tail:
                print('Retained input subprocess failed.', flush=True)
            for git_object in sorted(set(re.findall(r"'show', '([a-f0-9]{40}):[A-Za-z0-9./_-]+'", tail))):
                print('Required historical Git object:', git_object, flush=True)
            for git_object in sorted(set(re.findall(r"'(?:rev-parse|ls-tree|diff)', [^\r\n]*?'([a-f0-9]{40})(?:\^\{(?:tree|commit)\}|:[A-Za-z0-9./_-]+)?'", tail))):
                print('Retained source check Git object:', git_object, flush=True)
            for row in tail.splitlines():
                missing = re.fullmatch(r"FileNotFoundError: \[Errno 2\] No such file or directory: '([^']+)'", row)
                if missing:
                    path = Path(missing[1])
                    if path.is_relative_to(root) and re.fullmatch(r'[A-Za-z0-9./_-]+', path.relative_to(root).as_posix()):
                        print('Retained source path missing:', path.relative_to(root).as_posix(), flush=True)
            for reason, patterns in {
                'disk-space': ('no space left on device',),
                'git-object': ('bad object', 'could not fetch', 'unable to read sha1', 'missing blob'),
                'git-transport': ('rpc failed', 'unexpected disconnect', 'early eof'),
                'artifact-access': ('http 403', 'http 404', 'http 410'),
            }.items():
                if any(pattern in tail.lower() for pattern in patterns):
                    print('Retained input failure category:', reason, flush=True)
            raise RuntimeError(f'SKU_INPUT_PREPARATION_REFUSED_{index:02d}_EXIT_{result.returncode}')
        outputs.update(settings(github_output))
        environment.update(settings(variables))
        paths = extra_path.read_text().splitlines()
        if paths:
            environment['PATH'] = os.pathsep.join((*reversed(paths), environment['PATH']))
    if settings_file is not None:
        materialize_checkout(root / 'qualified-mandor-parent', environment, scratch,
                             'a0e7d5616a0ac470876409d31c41388159f17692',
                             '9e4cea296f2370d7ead31a6ac2b05c132fb09521')
        materialize_checkout(root / 'qualified-afui-parent', environment, scratch,
                             'fd797083eab093d9dc97f2d52ca61dc37812b437',
                             '02a8812e9eae2272a976d1dbd1e21aff8c022467')
        # Some older provider modules read their checked-in catalogue proof
        # bytes at source admission. Their unrelated documentation stays sparse.
        for folder in ('writer', 'qualified-sku090b', 'qualified-sku-money', 'qualified-sku-automatic',
                       'candidate', 'harness', 'frozen', 'finance-frozen', 'model-frozen', 'target-frozen',
                       'history-frozen', 'scoped-model-frozen', 'versioned-target-frozen',
                       'B-performance-frozen', 'B-frozen-units-qualified'):
            checkout_scope(root / folder, ('add', *EVIDENCE_PATHS), environment, scratch)
        verify_live_trigger_sources(root / 'qualified-sku090b')
        # Hand off new settings from the original setup within this job only.
        # The inherited GitHub token is required for GETs and stays in this step.
        delta = {name: value for name, value in environment.items()
                 if not name.startswith('GITHUB_') and name != 'GH_TOKEN'
                 and os.environ.get(name) != value}
        descriptor = os.open(settings_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            json.dump(delta, output)
    return dict(status='RETAINED_SKU_INPUTS_PREPARED', stages=len(PREPARATION),
                original_sku_run=43347020525, actual_sku_cases=0, actual_global_cases=0, production_go=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('--settings-file', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.workspace.resolve(), Path(os.environ['RUNNER_TEMP']).resolve(),
                             settings_file=args.settings_file)), flush=True)
