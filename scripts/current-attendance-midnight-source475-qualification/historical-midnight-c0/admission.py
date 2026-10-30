"""Fail-closed source/retained original11/package admission; no DB or network."""
from pathlib import Path
import ast
import gzip
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'f265ba2691ad03a2b7405806dc3aa4c5788b62fd'
FROZEN_GRAPH_SHA = '97a11f7cafce085d516f45c9aeb2b2beeae28e4b7999776698bc8b48f6380993'
OWN_FILES = ('admission.py','cases.py','oracle.py','test_preparation.py','README.md')
PACKAGE_GATES = ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')
ORIGINAL_GATES = ('cp6_restored','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal',
                  'advisor_gate','used_guard_refused_before_DDL','required_case_ids_pass')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def sources(root=ROOT, manifest_path=HERE/'SOURCE.json'):
    manifest = json.loads(Path(manifest_path).read_bytes())
    assert manifest['version'] == 'cp7.s03.midnight-output-additional-native1.v1'
    assert manifest['status'] == 'PREPARED' and manifest['frozen_base'] == BASE
    assert manifest['actual_Native_credit'] == 0 and type(manifest['actual_Native_credit']) is int
    assert manifest['production_go'] is False and manifest['independent_acceptance'] is False
    frozen = manifest['frozen_component_and_original11_files']
    if len(frozen) != 80 or sha(canonical(frozen).encode()) != FROZEN_GRAPH_SHA:
        raise ValueError('S03_MIDNIGHT_FROZEN_GRAPH_CHANGED')
    for name, expected in frozen.items():
        if sha((Path(root)/name).read_bytes()) != expected:
            raise ValueError('S03_MIDNIGHT_FROZEN_FILE_CHANGED:'+name)
    own = manifest['own_files']
    if set(own) != set(OWN_FILES):
        raise ValueError('S03_MIDNIGHT_EXACT_OWN_FILES_REQUIRED')
    for name, expected in own.items():
        if sha((Path(manifest_path).parent/name).read_bytes()) != expected:
            raise ValueError('S03_MIDNIGHT_OWN_FILE_CHANGED:'+name)
    return manifest


def original_ids(root=ROOT):
    path = Path(root)/'scripts/current-attendance-period-choice-qualification/cases.py'
    for node in ast.parse(path.read_text()).body:
        if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='IDS'for target in node.targets):
            ids = ast.literal_eval(node.value)
            assert len(ids) == len(set(ids)) == 11
            return tuple(ids)
    raise ValueError('S03_MIDNIGHT_ORIGINAL11_IDS_MISSING')


def admit_group(group, ids):
    counts, cases = group['counts'], group['cases']
    if(group['status'] != 'PASS' or tuple(group['planned_case_ids']) != tuple(ids)
       or group['complete_boundary_restored']is not True
       or type(counts.get('PASS')) is not int or counts['PASS'] != 11
       or any(type(v)is not int or v<0 for v in counts.values())
       or sum(counts.values()) != 11 or set(cases) != set(ids)
       or any(row['status'] != 'PASS' for row in cases.values())):
        raise ValueError('S03_MIDNIGHT_EXACT_QUALIFIED_ORIGINAL11_REQUIRED')
    return dict(PASS=11,FAIL=0,INCOMPLETE=0,case_ids=list(ids),
                inherited_group_boundary_flag=True,per_case_full_sequence_restore_claim=False)


def read_pinned(path, pin):
    content = Path(path).read_bytes()
    if pin['encoding'] == 'gzip':
        if sha(content) != pin['gzip_sha256']:
            raise ValueError('S03_MIDNIGHT_RETAINED_GZIP_CHANGED')
        raw = gzip.decompress(content)
    elif pin['encoding'] == 'raw':
        raw = content
    else:
        raise ValueError('S03_MIDNIGHT_RETAINED_ENCODING_REQUIRED')
    if type(pin['raw_bytes'])is not int or len(raw) != pin['raw_bytes'] or sha(raw) != pin['raw_sha256']:
        raise ValueError('S03_MIDNIGHT_RETAINED_RAW_CHANGED')
    return json.loads(raw)


def at_path(document, path):
    if not isinstance(path,list) or not path or not all(isinstance(key,str)and key for key in path):
        raise ValueError('S03_MIDNIGHT_EXACT_ORIGINAL_JSON_PATH_REQUIRED')
    for key in path:
        document = document[key]
    return document


def admit(fresh_original11, retained_original, *, state_sources):
    """retained_original={native: raw/gzip Path, package: raw/gzip Path}.

    Both accepted pins are null in this preparation. Only root may bind real
    terminal original11/package bytes and exact group/source JSON paths after
    full PASS. No fabricated raw result can unlock fixture creation here.
    """
    manifest = sources()
    pin, package_pin = manifest['accepted_original11'], manifest['accepted_package_original']
    if pin is None or package_pin is None:
        raise ValueError('S03_MIDNIGHT_RETAINED_NATIVE11_PIN_PENDING')
    ids = original_ids()
    fresh = admit_group(fresh_original11,ids)
    original = read_pinned(retained_original['native'],pin)
    package = read_pinned(retained_original['package'],package_pin)
    if(original['status'] != 'PASS' or type(original['actual_Native_cases'])is not int
       or original['actual_Native_cases'] != 11 or original['qualification_commit'] != pin['qualification_commit']
       or any(original[field]is not True for field in ORIGINAL_GATES)):
        raise ValueError('S03_MIDNIGHT_RETAINED_ORIGINAL11_FULL_GATES_REQUIRED')
    retained = admit_group(at_path(original,pin['Native_group_path']),ids)
    if not state_sources or canonical(at_path(original,pin['installation_source_path'])) != canonical(state_sources):
        raise ValueError('S03_MIDNIGHT_ACTUAL_INSTALLATION_SOURCE_CHANGED')
    if(package['status'] != 'ALL_STAGES_INSTALLED' or set(package['gate']) != set(PACKAGE_GATES)
       or any(package['gate'][key]is not True for key in PACKAGE_GATES)):
        raise ValueError('S03_MIDNIGHT_RETAINED_PACKAGE5_REQUIRED')
    return dict(status='QUALIFIED_ORIGINAL11_AND_PACKAGE_ADMITTED',fresh_original11=fresh,
                retained_original11=retained,retained_original_sha256=pin['raw_sha256'],
                current_source_equal=True,additional_Native_credit_before_execution=0,
                production_go=False,independent_acceptance=False)
