"""Root intake of exact PostgreSQL17 lock-model Originals; no database execution."""
from hashlib import sha256
import argparse

from intake_common import (GitBytes, exact, fields, json_bytes, original_zip,
                           originals, require, save, script_pins)

HEAD = 'f852a15ed5b5cdfd009722ad570d7d9bd60607cb'
TREE = '708357afb38804052e175409f89116e445839fff'
BASE = 'a6ded9cd4ce23a6d59cd32e42ca9bb33d793f8cc'
NS = 'scripts/current-global-lock-mechanics-qualification/'
WORKFLOW = '.github/workflows/cp7-global-lock-mechanics.yml'
REPORT = 'LOCK_MECHANICS_REPORT.json'
IMAGE_ID = 'LOCK_MODEL_IMAGE_ID.json'
IMAGE_DIGESTS = 'LOCK_MODEL_IMAGE_DIGESTS.json'
ZIP_PIN = dict(bytes=1917, sha256='8699d99c084ea2a02cf3f99318d53abdfb98082f89a282187491edb5ef61ffca')
RAW_PINS = {
    REPORT: dict(bytes=8814, sha256='853631f572eaece7a3dcbbeeeea9729525c83bcc7399a410c0cf0f31865ae769'),
    IMAGE_ID: dict(bytes=74, sha256='950e13c7bfef846a33135ca707473dfd42850cc13d5f2c6fab95b4bfefc8a1fd'),
    IMAGE_DIGESTS: dict(bytes=85, sha256='0bf5c7e8dc14f44f5db879fba4c19c04a9e32bf815c0b89489d403fa6e96ef07'),
}
DIGEST = 'postgres@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3'
IMAGE = 'sha256:567d5d704a3e5a4864393b623a0d50eb1b5a4ad134cdac7cf19555cb2d8ffe9e'
MODES = ('ACCESS SHARE', 'ROW SHARE', 'ROW EXCLUSIVE', 'SHARE UPDATE EXCLUSIVE',
         'SHARE', 'SHARE ROW EXCLUSIVE', 'EXCLUSIVE', 'ACCESS EXCLUSIVE')
REQUESTS = ('SHARE', 'SHARE ROW EXCLUSIVE', 'EXCLUSIVE')
# Independent result oracle: permitted holder modes from PostgreSQL17 Table13.2.
ALLOWED_HOLDERS = {
    'SHARE': {'ACCESS SHARE', 'ROW SHARE', 'SHARE'},
    'SHARE ROW EXCLUSIVE': {'ACCESS SHARE', 'ROW SHARE'},
    'EXCLUSIVE': {'ACCESS SHARE'},
}
NO_CREDIT = dict(actual_ERP_Native_cases=0, production_go=False, independent_acceptance=False)
BASELINE = dict(rows=dict(root=[[1, 'unchanged']], child=[], effects=[]),
    sequences=dict(effects_id_seq=[1, False], before_effect_seq=[1, False]))
WRITES = ("insert into cp7_lock_mechanics_model.root values(99,'phantom')",
          'insert into cp7_lock_mechanics_model.child values(22,1)')


def source(g, actual):
    raw = g.read(NS + 'SOURCE.json'); declaration = json_bytes(raw)
    fields(declaration, dict(base=BASE, classification='ISOLATED_POSTGRESQL17_MODEL_ONLY',
        runtime_entry=None, **NO_CREDIT), 'ROOT_LOCK_MODEL_SOURCE_DECLARATION')
    exact(actual, dict(head=HEAD, manifest_sha256=sha256(raw).hexdigest(), files=5, base=BASE),
          'ROOT_LOCK_MODEL_ACTUAL_SOURCE_BINDING')
    exact(set(declaration['files']), {NS + name for name in ('README.md', 'matrix.py', 'probe.py', 'test_matrix.py')}
          | {WORKFLOW}, 'ROOT_LOCK_MODEL_EXACT_SOURCE5')
    for name, expected in declaration['files'].items():
        g.verify_pin(name, expected)
    baseline = g.entries(BASE)
    for name, expected in baseline.items():
        exact(g.tree.get(name), expected, 'ROOT_LOCK_MODEL_BASE_PRODUCT_CHANGED:' + name)
    exact(set(g.tree) - set(baseline), set(declaration['files']) | {NS + 'SOURCE.json'},
          'ROOT_LOCK_MODEL_ONLY_SIX_ADDITIVE_PATHS_ALLOWED')
    return dict(manifest_sha256=sha256(raw).hexdigest(), verified_source_pins=5,
        complete_base_blobs_modes_unchanged=True, base_files=len(baseline),
        added_source_paths=6, no_ERP_runtime_entry=True)


def checked(g, docs):
    report = docs[REPORT]
    exact(docs[IMAGE_ID], IMAGE, 'ROOT_LOCK_MODEL_IMAGE_ID_STRING_REQUIRED')
    exact(docs[IMAGE_DIGESTS], [DIGEST], 'ROOT_LOCK_MODEL_EXACT_IMAGE_DIGEST_LIST_REQUIRED')
    fields(report, dict(status='PASS', classification='ACTUAL_POSTGRESQL17_SYNTHETIC_LOCK_MODEL',
        ERP_writer_trigger_FK_census_closed=False, ERP_lock_profile_qualified=False,
        complete_model_rows_sequences_equal=True, model_removed_and_no_session_leaks=True,
        **NO_CREDIT), 'ROOT_LOCK_MODEL_REPORT')
    require(report['server_version'].startswith('PostgreSQL 17.6 (Debian 17.6-2.pgdg12+1)'),
            'ROOT_LOCK_MODEL_ACTUAL_POSTGRESQL17_6_REQUIRED')
    expected_pairs = [(held, requested) for held in MODES for requested in REQUESTS]
    exact([(row['held'], row['requested']) for row in report['pairs']], expected_pairs,
          'ROOT_LOCK_MODEL_EXACT_ORDERED_24_PAIRS_REQUIRED')
    for row in report['pairs']:
        refused = row['held'] not in ALLOWED_HOLDERS[row['requested']]
        fields(row, dict(refused=refused, sqlstate='55P03' if refused else None,
            two_actual_backends=True, holder_lock_observed=True), 'ROOT_LOCK_MODEL_ACTUAL_PAIR')
    exact(report['matrix_gate'], dict(actual_lock_pairs=24, source_contract='PostgreSQL17 Table13.2',
        SHARE_ROW_EXCLUSIVE_excludes_ROW_SHARE=False, EXCLUSIVE_excludes_ROW_SHARE=True,
        EXCLUSIVE_allows_plain_SELECT=True, ERP_relation_set_qualified=False, **NO_CREDIT),
        'ROOT_LOCK_MODEL_MATRIX_GATE')
    exact(report['foreign_key_holders'], [dict(requested=requested, actual_FK_parent_locks=['RowShareLock'],
        sqlstate=state, classification='ACTUAL_FK_LOCK_MECHANICS_NOT_ERP_FK_CLOSURE')
        for requested, state in (('SHARE ROW EXCLUSIVE', None), ('EXCLUSIVE', '55P03'))],
        'ROOT_LOCK_MODEL_TWO_REAL_FOREIGN_KEY_HOLDERS_REQUIRED')
    busy = report['before_effect_busy']
    exact(busy, dict(sqlstate='55P03', model_before=BASELINE, model_after=BASELINE,
        complete_model_noeffect=True, actual_ERP_Native_cases=0), 'ROOT_LOCK_MODEL_BUSY_BEFORE_SEQUENCE_OR_ROW')
    exact(report['ordinary_reader'], dict(plain_SELECT_while_EXCLUSIVE_held=True,
        rows=BASELINE['rows']['root']), 'ROOT_LOCK_MODEL_PLAIN_SELECT_REQUIRED')
    expected_waits = [(release, sql) for release in ('commit', 'rollback') for sql in WRITES]
    exact([(row['release'], row['sql']) for row in report['real_blocking']], expected_waits,
          'ROOT_LOCK_MODEL_EXACT_FOUR_ACTUAL_WAIT_SCHEDULES')
    pids = []
    for row in report['real_blocking']:
        fields(row, dict(actual_holder_blocks_worker=True, all_model_rows_sequences_restored=True,
            worker=dict(completed_after_release=True, worker_changes_rolled_back=True)),
            'ROOT_LOCK_MODEL_ACTUAL_WAIT_AND_RESTORE_REQUIRED')
        for key in ('holder_pid', 'worker_pid'):
            require(type(row[key]) is int and row[key] > 0, 'ROOT_LOCK_MODEL_REAL_BACKEND_PID_REQUIRED')
        require(row['holder_pid'] != row['worker_pid'], 'ROOT_LOCK_MODEL_DISTINCT_BACKENDS_REQUIRED')
        pids.extend((row['holder_pid'], row['worker_pid']))
    exact(len(set(pids)), 8, 'ROOT_LOCK_MODEL_FOUR_DISTINCT_HOLDER_WORKER_PAIRS')
    return dict(status='ROOT_VERIFIED_STANDALONE_PG17_LOCK_MECHANICS32_RAW_SOURCE',
        classification='INTERNAL_WRITER_ROOT_INTAKE_STANDALONE_SYNTHETIC_MODEL_ONLY',
        head=HEAD, tree=TREE, run_id='41029331511', job_id=123975000845, artifact_id=12965455698,
        archive_name='ERP_Global_Lock_Mechanics_PG17_f852_20261030.zip',
        private_Original_Library_file_id='libfile_5044abf64ee48191a49ed4cef538b44a',
        CI_identity_binding='Root archive acquisition metadata; report independently binds exact public head and manifest.',
        archive=ZIP_PIN, archive_members=3, archive_CRC_ok=True, originals=RAW_PINS,
        source=source(g, report['source']), actual_server='PostgreSQL 17.6',
        actual_image_id=IMAGE, actual_image_repo_digests=[DIGEST],
        image_ID_JSON_type='string', image_digests_JSON_type='list',
        actual_model_observations=32, actual_mode_pairs=24, actual_FK_holder_cases=2,
        before_effect_busy_cases=1, ordinary_SELECT_cases=1, actual_blocked_writer_schedules=4,
        distinct_actual_holder_worker_pids=True, actual_pg_blocking_pids_observed=True,
        before_effect_rows_and_both_sequences_equal=True, all_model_rows_sequences_restored=True,
        model_schema_removed_and_no_session_leaks=True,
        SHARE_ROW_EXCLUSIVE_excludes_ROW_SHARE=False, EXCLUSIVE_excludes_ROW_SHARE=True,
        EXCLUSIVE_allows_plain_SELECT=True, ERP_relation_set_qualified=False,
        ERP_writer_trigger_FK_census_closed=False, ERP_lock_profile_qualified=False,
        ERP_owning_hooks_qualified=False, accepted_transactions_reexecuted=False,
        actual_Auth_HTTP_cases=0, actual_browser_cases=0, formal_total_unchanged='5/16', **NO_CREDIT)


def intake(root, archive):
    with original_zip(archive, ZIP_PIN, 3) as z:
        exact(set(z.namelist()), set(RAW_PINS), 'ROOT_LOCK_MODEL_EXACT_THREE_ORIGINAL_NAMES')
        _, docs = originals(z, RAW_PINS)
    with GitBytes(root, HEAD, TREE) as g:
        value = checked(g, docs)
    value['intake_scripts'] = script_pins('intake_lock_model.py')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'archive', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    save(intake(args.source_root, args.archive), args.output)
