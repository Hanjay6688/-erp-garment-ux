"""Stage and check the six exact Mandor adoption files on a disposable checkout."""
from pathlib import Path
import base64
import importlib.util
import json
import subprocess
import sys

from verify_terminal import ADOPTION_FILES, COUNTS, HEAD, JOB, RUN, TREE, exact, pin, require, strict

MANDOR = '7fd3154270320b5c57e65edcd8979d123fdc4347'
MANDOR_TREE = 'd8b5001bc43752db6294ec12fcefcb34b4bfc91b'
AREA = Path('scripts/current-mandor-afui-preparation')


def git(checkout, *args):
    return subprocess.check_output(['git', '-C', str(checkout), *args], text=True).strip()


def require_root(root_path):
    raw = root_path.read_bytes()
    root = strict(raw)
    receipt_raw = root_path.with_name('TERMINAL_RECEIPT.json').read_bytes()
    receipt = strict(receipt_raw)
    exact(receipt, dict(status='AFUI_TERMINAL_ORIGINAL_BYTES_VERIFIED', head=HEAD, run=RUN, job=JOB, attempt=1,
                        conclusion='success', all_member_crc_verified=True, actual_case_credit=15,
                        actual_all_five=True, actual_outer_restore=True, actual_backup_restored_identical=True,
                        actual_worker_reaped=True, first_failed_step=None, main_status='PASS', production_go=False,
                        independent_acceptance=False, ERP_commands_executed=0), 'MANDOR_VERIFIED_EXACT_AFUI_PARENT')
    exact(root, dict(status='ROOT_VERIFIED_CURRENT_AFUI_GOOD_NONPAYABLE_FULL15_ALL5',
                     head=HEAD, tree=TREE, run_id=RUN, job_id=JOB, **COUNTS, actual_business_cases=15,
                     complete15_qualified=True, package_all_five=True, actual_outer_restore=True,
                     prior_runs_aggregated=False, production_go=False, independent_acceptance=False,
                     terminal_verification_receipt=pin(receipt_raw)), 'MANDOR_EXACT_ROOT_BYTES')
    require(root['artifact_id'] == receipt['artifact_id'] and root['archive'] == dict(receipt['archive'], members=receipt['zip_members'])
            and root['qualified_Afui_good_nonpayable_sources'] == receipt['qualified_Afui_good_nonpayable_sources']
            and set(root['originals']) == set(ADOPTION_FILES)
            and all(root['originals'][name] == {key: receipt['members'][name][key] for key in ('bytes', 'sha256')}
                    for name in ADOPTION_FILES), 'MANDOR_EXACT_SOURCE_ORIGINAL_PINS_REQUIRED')
    return raw, root


def patch(checkout, root_bytes, root):
    require(git(checkout, 'rev-parse', 'HEAD') == MANDOR
            and git(checkout, 'rev-parse', 'HEAD^{tree}') == MANDOR_TREE
            and not git(checkout, 'status', '--porcelain'),
            'MANDOR_REQUIRES_CLEAN_EXACT_PREPARED_TREE')
    require(git(checkout, 'rev-parse', HEAD + '^{tree}') == TREE, 'MANDOR_EXACT_AFUI_TREE_REQUIRED')
    spec = importlib.util.spec_from_file_location('exact_mandor_current_source_fence', checkout / AREA / 'check_source.py')
    fence = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fence)
    require((fence.routes.AFUI, fence.routes.AFUI_TREE) == (HEAD, TREE), 'MANDOR_EXACT_PENDING_AFUI_TARGET')
    workflow = (checkout / AREA / 'current-mandor84.workflow.yml.txt').read_bytes()
    for name in (fence.PARENT_ROOT, fence.ACTIVE_WORKFLOW):
        path = checkout / name
        require(not path.exists() and not path.is_symlink(), 'MANDOR_FIRST_ACTUAL_ADOPTION_PATH_REQUIRED')
    bindings = dict(PARENT_RUN=RUN, PARENT_JOB=JOB, PARENT_ROOT_PIN=pin(root_bytes),
                    RUNTIME_ENTRY=fence.routes.NS + 'qualification.py')
    qualifier = fence.routes.NS + 'admission.py'
    caller = fence.bind_empty_values((checkout / qualifier).read_bytes(), bindings)
    keys = ('status', *COUNTS, 'actual_business_cases', 'complete15_qualified', 'prior_runs_aggregated')
    contract = {key: root[key] for key in keys}
    component = fence.bind_empty_values((checkout / fence.COMPONENT_ADMISSION).read_bytes(),
        dict(PARENT_HEAD=HEAD, PARENT_TREE=TREE, PARENT_ROOT_CONTRACT=contract, **bindings))
    component_manifest = strict((checkout / fence.COMPONENT_SOURCE).read_bytes())
    component_manifest['files'][fence.COMPONENT_ADMISSION] = pin(component)
    manifest = AREA / 'SOURCE.json'
    source = strict((checkout / manifest).read_bytes())
    require(source['classification'] == fence.PREPARED and source['actual_parent_adopted'] is False
            and 'actual_Afui_adoption' not in source, 'MANDOR_PREPARATION_MUST_STILL_BE_CLOSED')
    source.update(classification=fence.ADOPTED, active_workflow_added=True, actual_parent_adopted=True,
                  actual_successor_source_fence_rebinding_pending=False,
                  actual_Afui_adoption={fence.PARENT_ROOT: pin(root_bytes), fence.ACTIVE_WORKFLOW: pin(workflow)})
    source['files'][qualifier] = pin(caller)
    return {fence.PARENT_ROOT: root_bytes, fence.ACTIVE_WORKFLOW: workflow, qualifier: caller,
            fence.COMPONENT_ADMISSION: component,
            fence.COMPONENT_SOURCE: (json.dumps(component_manifest, indent=2) + '\n').encode(),
            str(manifest): (json.dumps(source, indent=2) + '\n').encode()}


def main():
    checkout = Path(sys.argv[1]).resolve()
    root_path = Path(sys.argv[2]).resolve()
    files = patch(checkout, *require_root(root_path))
    for name, raw in files.items():
        (checkout / name).write_bytes(raw)
    checks = (('workflow.py', '--check-owning'), ('check_source.py',))
    for file, *args in checks:
        subprocess.run([sys.executable, '-B', str(AREA / file), *args], cwd=checkout, check=True)
    git(checkout, 'add', '--', *files)
    changed = [row.split('\t', 1) for row in git(checkout, 'diff', '--cached', '--name-status', '--no-renames').splitlines()]
    require(len(changed) == 6 and {name for _, name in changed} == set(files)
            and sorted(status for status, _ in changed) == ['A', 'A', 'M', 'M', 'M', 'M'],
            'MANDOR_EXACT_SIX_ADOPTION_FILES')
    tree = git(checkout, 'write-tree')
    bundle = dict(status='MANDOR_ADOPTED_EXACT_SOURCE_AND_OWNING_WORKFLOW_STATIC_PASS',
                  prepared_head=MANDOR, prepared_tree=MANDOR_TREE, staged_tree=tree,
                  owning_workflow_activated=False, actual_ERP_cases=0,
                  files={name: dict(pin(raw), body=base64.b64encode(raw).decode('ascii')) for name, raw in files.items()})
    for name, record in bundle['files'].items():
        record['blob'] = git(checkout, 'rev-parse', ':' + name)
    encoded = base64.b64encode(json.dumps(bundle, separators=(',', ':')).encode()).decode('ascii')
    chunks = [encoded[start:start + 4096] for start in range(0, len(encoded), 4096)]
    for number, chunk in enumerate(chunks, 1):
        print(f'CP7_MANDOR_PATCH_B64_PART {number} {len(chunks)} {chunk}', flush=True)
    print('CP7_MANDOR_PATCH_STATIC_PASS ' + json.dumps(dict(tree=tree, files=len(files), actual_ERP_cases=0)), flush=True)


if __name__ == '__main__':
    main()
