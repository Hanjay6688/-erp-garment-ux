"""Fresh Reader3 after actual original11 PASS, on the same actual installation."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABEL = 'CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES'
FACTORY = 'scripts/current-attendance-period-choice-readers-qualification/cases.py'


def exact_group(group, ids):
    if (group.get('status') != 'PASS' or group.get('error') or group.get('counts') != {'PASS': len(ids)}
            or group.get('planned_case_ids') != list(ids) or set(group.get('cases', {})) != set(ids)
            or group.get('complete_boundary_restored') is not True):
        raise ValueError('S03_NATIVE14_EXACT_COMPLETE_STRICT_GROUP_REQUIRED')
    for key, row in group['cases'].items():
        if (row.get('status') != 'PASS' or row.get('full_boundary_restored') is not True
                or row.get('public_schema_unchanged') is not True or row.get('error')):
            raise ValueError('S03_NATIVE14_STRICT_CASE_BOUNDARY_FAILED:' + key)


def retain(native, report):
    root = ROOT / 'cp6-proof/t3'; root.mkdir(parents=True, exist_ok=True)
    files = []
    for name in (LABEL + '.json', LABEL + '_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path = native.r1.OUT / name
        if not path.is_file():
            continue
        raw = path.read_bytes(); target = root / name
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('S03_NATIVE14_READER_FIRST_ORIGINAL_CANNOT_BE_OVERWRITTEN:' + name)
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(raw)
        files.append(dict(name=name, bytes=len(raw), sha256=sha256(raw).hexdigest()))
    report['reader3_strict_originals'] = files


def run(native, control, state, report, verify, original11):
    import json
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    exact_group(original11, cfg['original_Native11_ids'])
    spec = importlib.util.spec_from_file_location('s03_native14_actual_authored_reader3', ROOT / FACTORY)
    reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
    if list(reader.IDS) != cfg['reader_Native3_ids'] or len(reader.IDS) != 3:
        raise ValueError('S03_NATIVE14_EXACT_AUTHORED_READER3_IDS_REQUIRED')

    def cases(cursor, today):
        # Same accepted physical harness overlay removal/restoration as original11.
        with control.product_catalog(cursor):
            planned = reader.cases(cursor, today, state=state, evidence=report, fresh_original11=original11)
        if tuple(key for key, _ in planned) != reader.IDS or len(planned) != 3:
            raise ValueError('S03_NATIVE14_EXACT_THREE_READER_CALLBACKS_REQUIRED')
        return planned

    from cp7_catalog_state import exact_public_catalog
    try:
        with exact_public_catalog(native, retain_raw=True) as public:
            group = native.strict_group(LABEL, cases, verify)
    finally:
        retain(native, report)
    report.update(reader_native3=group, reader3_public_catalog_observation=public,
        both_groups_same_actual_installation=True, reader3_requires_actual_fresh_original11=True,
        combined_strict14_fabricated=False)
    exact_group(group, cfg['reader_Native3_ids'])
    return group
