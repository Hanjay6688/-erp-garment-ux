"""Writer-only source/workflow freeze; no database, network or runtime import."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = 'scripts/current-s05-native10-qualification'
REPAIR = 'scripts/current-s05-public-default-acl-repair'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def bind():
    old_source_raw = (ROOT/OLD/'SOURCE.json').read_bytes()
    old_source = json.loads(old_source_raw)
    old_config = json.loads((ROOT/OLD/'CONFIG.json').read_bytes())
    workflow = load('s05_acl_writer_workflow', HERE/'workflow_source.py')
    text, derivation = workflow.generated((ROOT/workflow.OLD_PATH).read_bytes())
    (ROOT/workflow.PATH).write_text(text)
    manifest = ROOT/'scripts/cp7_accessory_standard_report/SOURCE.json'
    config = dict(contract='cp7.s05-public-default-acl-qualification.v1',
        base_head='b0e5ac05e2024d5673126b6fe7759591293b9b96',
        base_tree='3820c7348167fc750cc3f3f36645f14f76286e44',
        product_repair_commit='d49461d35d3c59c855bcce293d7da96fe54eeb11',
        inherited_qualifier_manifest_sha256=sha256(old_source_raw).hexdigest(),
        inherited_configuration=old_config, workflow=workflow.PATH,
        root_publish_branch=workflow.BRANCH, workflow_derivation=derivation,
        S05_manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
        Native_executions=0, database_calls=0, independent_acceptance=False, production_go=False)
    (HERE/'CONFIG.json').write_text(json.dumps(config, indent=2)+'\n')
    files = set(old_source['files']) | {OLD+'/SOURCE.json', workflow.PATH}
    for folder in (HERE, ROOT/REPAIR):
        files.update(str(path.relative_to(ROOT)) for path in folder.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'
            and path != HERE/'SOURCE.json')
    pins = {path: sha256((ROOT/path).read_bytes()).hexdigest() for path in sorted(files)}
    source = dict(contract=config['contract'], status='PREPARED_NOT_EXECUTED',
        base_head=config['base_head'], base_tree=config['base_tree'],
        allowed_changes=[REPAIR+'/**', str(HERE.relative_to(ROOT))+'/**', workflow.PATH,
            'scripts/cp7_accessory_standard_report/SOURCE.json',
            'scripts/cp7_accessory_standard_report/stage.py', 'scripts/cp7_accessory_standard_report/report.sql'],
        files=pins, exact_changed_product_paths=sorted('scripts/cp7_accessory_standard_report/'+n
            for n in ('SOURCE.json', 'stage.py', 'report.sql')),
        old_qualifier_files_and_manifests_unchanged=True,
        unchanged_native10_and_separate_committed_used_inverse=True,
        unchanged_six_change_complete_vendor_engine=True,
        unchanged_all22_rows_sequences_roles_CP6_advisors_and_all_five_package_gates=True,
        retained_b0_native_PASS_credit=0, Native_executions=0, database_calls=0,
        actual_CI_extra_tuple_identity_proven=False,
        independent_acceptance=False, production_go=False)
    (HERE/'SOURCE.json').write_text(json.dumps(source, indent=2)+'\n')
    return dict(status='PREPARED_NOT_EXECUTED', files=len(pins), workflow=workflow.PATH,
                SOURCE_sha256=sha256((HERE/'SOURCE.json').read_bytes()).hexdigest())


if __name__ == '__main__':
    if sys.argv[1:] != ['--writer-freeze']:
        raise SystemExit('Only --writer-freeze writes metadata; never call this binder in qualification runtime.')
    print(json.dumps(bind()))
