"""Closed source transition only; no product/DB/network imports or launcher.

The sole Git ancestor is public8be4. This does not rewrite/adopt the frozen
282-pin declaration, nor pretend its failed15/17 is current qualification.
"""
from pathlib import Path, PurePosixPath
from hashlib import sha256, sha1
import argparse, gzip, json, os, re, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREFIX = 'scripts/current-credit-e1-consumer-phase-successor/'
BASE = '8be4c15a37dcfc6186e32f396df78291ff1b957c'
PRODUCT = ('scripts/cp7_credit_correction_de/note_carry/06_owning.sql',
           'scripts/cp7_credit_correction_de/note_carry/07_profile_closure.sql')
OLD_SOURCE = 'scripts/current-credit-e1-current-d1-native17-qualification/SOURCE.json'
OLD_SOURCE_SHA = '7a92b13976bd8cc24d19bc9f3ccb379f8a582bf7370ded4b23739296603d14fc'


def regular(root, relative):
    rel = PurePosixPath(relative)
    if str(rel) != relative or rel.is_absolute() or not rel.parts or '..' in rel.parts:
        raise ValueError('E_PHASE_INVALID_RELATIVE_SOURCE:' + relative)
    at = Path(root)
    if at.is_symlink():
        raise ValueError('E_PHASE_SOURCE_SYMLINK:' + str(at))
    for part in rel.parts:
        at = at/part
        if at.is_symlink():
            raise ValueError('E_PHASE_SOURCE_SYMLINK:' + relative)
    if not at.is_file():
        raise ValueError('E_PHASE_REGULAR_SOURCE_REQUIRED:' + relative)
    return at


def pin(root, relative, expected):
    path = regular(root, relative)
    raw = path.read_bytes()
    if type(expected.get('bytes')) is not int or len(raw) != expected['bytes'] or sha256(raw).hexdigest() != expected.get('sha256'):
        raise ValueError('E_PHASE_SOURCE_BYTES_CHANGED:' + relative)
    return raw


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], env={**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0'})


def blob(raw):
    return sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def functions(source):
    spec = __import__('importlib.util', fromlist=['util']).spec_from_file_location('e_phase_local_source_parser', HERE/'fixture.py')
    value = __import__('importlib.util', fromlist=['util']).module_from_spec(spec)
    spec.loader.exec_module(value)
    return {name: value.function(source, name) for name in re.findall(r'create function ([a-z0-9_.]+)\(', source)}


def derivation(root=ROOT):
    old_own = regular(root, PREFIX+'evidence/BEFORE_06_owning.sql').read_text()
    old_profile = regular(root, PREFIX+'evidence/BEFORE_07_profile_closure.sql').read_text()
    own = regular(root, PRODUCT[0]).read_text()
    profile = regular(root, PRODUCT[1]).read_text()
    anchor = "cp7_credit.consumer_dependency_graph_v1((p->>'sale_id')::uuid)"
    if old_own.count(anchor) != 2:
        raise ValueError('E_PHASE_ORIGINAL_TWO_GRAPH_CALLS_REQUIRED')
    derived = old_own.replace(anchor, "cp7_credit.consumer_joined_graph_v1((p->>'sale_id')::uuid,null)", 2)
    anchor = "sources:=cp7_credit.consumer_capture_sources_v1(jsonb_build_object('sale_ids',sales));"
    if derived.count(anchor) != 1:
        raise ValueError('E_PHASE_ORIGINAL_ONE_CAPTURE_CALL_REQUIRED')
    if derived.replace(anchor, 'sources:=cp7_credit.consumer_capture_sources_v1(graph);', 1) != own:
        raise ValueError('E_PHASE_ONLY_THREE_GRAPH_ABI_CHANGES_ALLOWED')
    before, after = functions(old_profile), functions(profile)
    helper = 'cp7_credit_note_carry_de.consumer_status_refresh_allowed_v1'
    if set(after) != set(before) | {helper}:
        raise ValueError('E_PHASE_EXACT_ONE_NEW_PRIVATE_FUNCTION_REQUIRED')
    target = 'cp7_credit_note_carry_de.assert_profile_v1'
    for name in before.keys() - {target}:
        if before[name] != after[name]:
            raise ValueError('E_PHASE_OTHER_PROFILE_BODY_CHANGED:' + name)
    old_if = "if raw_ar is distinct from gross-incoming or status is distinct from(case when incoming=gross then'PAID'when incoming>0 then'PARTIAL_PAID'else'POSTED'end)then"
    if before[target].count(old_if) != 1:
        raise ValueError('E_PHASE_ORIGINAL_COMBINED_GUARD_REQUIRED')
    addition = """ perform cp7_credit.assert_financial_materialization_provenance(p_actual);
 if status is distinct from(case when incoming=gross then'PAID'when incoming>0 then'PARTIAL_PAID'else'POSTED'end)
  and cp7_credit_note_carry_de.consumer_status_refresh_allowed_v1(p_sale,p_actual,status)is distinct from true then
  raise exception 'CP7_CREDIT_NOTE_CARRY_RAW_AR_OR_STATUS_CHANGED';end if;
"""
    expected = before[target].replace(old_if, 'if raw_ar is distinct from gross-incoming then', 1)
    expected = expected.removesuffix('end $$;') + addition + 'end $$;'
    if expected != after[target]:
        raise ValueError('E_PHASE_FINANCIAL_PROFILE_BODY_CHANGED_BEYOND_APPROVAL')
    body = re.sub(r'--[^\n]*', '', after[helper])
    if re.search(r'\b(insert|update|delete|truncate|execute|set_config|current_effective_paid|assert_current_materialized_profile)\b', body, re.I):
        raise ValueError('E_PHASE_HELPER_MUST_BE_READONLY_AND_NONRECURSIVE')
    if "language plpgsql stable security definer set search_path=''set timezone='UTC'" not in body:
        raise ValueError('E_PHASE_PRIVATE_STABLE_EMPTY_SEARCH_PATH_REQUIRED')
    return dict(graph_ABI_substitutions=3, existing_profile_function_changes=1, new_private_functions=1,
                all_other_profile_bodies_exact=True, helper_direct_full_profile_recursion=False)


def historical_proofs(root):
    archive = json.loads(regular(root, 'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes())
    if len(archive['files']) != 24 or archive['source_body_changes'] != 0 or archive['frozen_manifest_changes'] != 0:
        raise ValueError('E_PHASE_EXACT_HISTORICAL_PROOFS_REQUIRED')
    answer = {}
    for item in archive['files']:
        rel = item['path']
        if PurePosixPath(rel).parts[:2] != ('.github', 'workflows'):
            raise ValueError('E_PHASE_HISTORICAL_PROOF_SCOPE_CHANGED')
        expected = dict(bytes=item['bytes'], sha256=item['sha256'])
        raw = pin(root, item['archive'], expected)
        if pin(root, rel, expected) != raw:
            raise ValueError('E_PHASE_HISTORICAL_PROOF_BYTES_CHANGED')
        for name in item['frozen_manifests']:
            if json.loads(regular(root, name).read_bytes())['files'][rel] != item['sha256']:
                raise ValueError('E_PHASE_HISTORICAL_MANIFEST_CHANGED')
        answer[rel] = expected
    return answer


def require_execution(config):
    if config.get('state') != 'CLOSED_SOURCE_REPAIR_ONLY' or config.get('accepted_native17') is not None:
        raise ValueError('E_PHASE_ROOT_NEW_QUALIFIER_REQUIRED')
    raise ValueError('E_PHASE_FRESH_NATIVE17_NOT_QUALIFIED')


def check(root=ROOT, here=HERE):
    root, here = Path(root), Path(here)
    manifest = json.loads(regular(root, PREFIX+'SOURCE.json').read_bytes())
    if manifest['base_public_head'] != BASE or manifest['product_exceptions'] != list(PRODUCT):
        raise ValueError('E_PHASE_PUBLIC_BASE_AND_TWO_EXCEPTIONS_REQUIRED')
    if sha256(regular(root, OLD_SOURCE).read_bytes()).hexdigest() != OLD_SOURCE_SHA:
        raise ValueError('E_PHASE_FROZEN_282_SOURCE_CHANGED')
    retained = gzip.decompress(regular(root, PREFIX+'evidence/retained_8be4/SOURCE.json.gz').read_bytes())
    if retained != regular(root, OLD_SOURCE).read_bytes():
        raise ValueError('E_PHASE_RETAINED_282_ORIGINAL_CHANGED')
    entries = {}
    for entry in git(root, 'ls-tree', '-r', '-z', BASE).split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('E_PHASE_UNSUPPORTED_BASE_GIT_MEMBER')
        entries[name.decode()] = (mode, oid)
    proofs = historical_proofs(root)
    tracked = set(git(root, 'ls-files', '-z').decode().split('\0')) - {''}
    untracked = set(git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')) - {''}
    own = {p for p in manifest['files'] if p.startswith(PREFIX)} | {PREFIX+'SOURCE.json'}
    if not tracked <= set(entries) | own or not untracked <= own | set(proofs):
        raise ValueError('E_PHASE_UNKNOWN_SOURCE_OR_RECEIPT:' + repr(sorted((tracked | untracked) - set(entries) - own - set(proofs))))
    if set(proofs) & tracked:
        raise ValueError('E_PHASE_HISTORICAL_WORKFLOW_MUST_REMAIN_UNTRACKED')
    if {str(p.relative_to(root)) for p in here.rglob('*') if p.is_file() or p.is_symlink()} != own:
        raise ValueError('E_PHASE_OWN_NAMESPACE_NOT_CLOSED')
    for relative, expected in manifest['files'].items():
        pin(root, relative, expected)
    for relative, (mode, oid) in entries.items():
        path = regular(root, relative)
        if relative not in PRODUCT and blob(path.read_bytes()) != oid:
            raise ValueError('E_PHASE_UNREVIEWED_BASE_FILE_CHANGED:' + relative)
        if bool(path.stat().st_mode & 0o111) != (mode == '100755'):
            raise ValueError('E_PHASE_BASE_FILE_MODE_CHANGED:' + relative)
    for path in PRODUCT:
        old = regular(root, PREFIX+'evidence/BEFORE_'+Path(path).name).read_bytes()
        if blob(old) != entries[path][1]:
            raise ValueError('E_PHASE_BEFORE_PRODUCT_NOT_EXACT_PUBLIC_BASE')
    rule = derivation(root)
    group = json.loads(gzip.decompress(regular(root, PREFIX+'evidence/retained_8be4/CP7_CREDIT_E1_NATIVE17_CASES.json.gz').read_bytes()))
    if group['status'] != 'INCOMPLETE' or group['counts'] != {'PASS': 15, 'INCOMPLETE': 2} or group['missing'] != []:
        raise ValueError('E_PHASE_FIRST_FAILURE_MUST_REMAIN_FAILURE')
    cfg = json.loads(regular(root, PREFIX+'CONFIG.json').read_bytes())
    if cfg['accepted_native17'] is not None or cfg['production_go'] is not False or cfg['independent_acceptance'] is not False:
        raise ValueError('E_PHASE_EXECUTION_GATE_MUST_REMAIN_CLOSED')
    return dict(status='CLOSED_EXACT_PUBLIC_SOURCE_TRANSITION_ONLY', source_pins=len(manifest['files']),
                whole_public_base_files=len(entries), historical_untracked_proofs=len(proofs), derivation=rule,
                retained_actual_E_counts=group['counts'], fresh_actual_Native=0, production_go=False, independent_acceptance=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--runtime', action='store_true')
    args = parser.parse_args()
    if args.runtime:
        require_execution(json.loads((HERE/'CONFIG.json').read_bytes()))
    if not args.check:
        parser.error('--check required; this namespace provides no actual runner')
    print(json.dumps(check()))


if __name__ == '__main__':
    main()
