"""Labelled in-memory doubles only; never Original files or runtime admission."""
from copy import deepcopy
from midnight_common import HERE, ID, CASE, LABEL, document, digest
import midnight_admission as admission

CLASSIFICATION = 'LOCAL_IN_MEMORY_CONTROL_ONLY_NATIVE0_NOT_ORIGINAL'


def group(ids):
    return dict(classification=CLASSIFICATION, Native_credit=0, status='PASS',
        counts={'PASS': len(ids)}, planned_case_ids=list(ids), complete_boundary_restored=True,
        cases={key: dict(status='PASS', full_boundary_restored=True, public_schema_unchanged=True) for key in ids})


def parent():
    cfg = deepcopy(document((HERE / 'CONFIG.json').read_bytes()))
    cfg['state'] = 'ROOT_BOUND_ACTUAL_SUCCESSOR14'
    sources = dict(classification=CLASSIFICATION, contract='LOCAL_PRODUCT_SOURCE_DOUBLE',
                   files=cfg['prepared_backend_runtime7'], predecessor={'LOCAL_DOUBLE': True})
    head, tree = 'b' * 40, 'c' * 40
    cfg['backend_binding'] = dict(head=head, tree=tree, runtime_files=cfg['prepared_backend_runtime7'],
        product_sources_sha256=digest(sources), files={'LOCAL_SOURCE_DOUBLE': {}},
        source_manifest=dict(path='LOCAL_SOURCE_DOUBLE', bytes=1, sha256='a' * 64))
    original_pin = dict(encoding='raw', stored=dict(bytes=1, sha256='a' * 64),
                        raw=dict(bytes=1, sha256='a' * 64))
    cfg['accepted_parent14'] = dict(status='ROOT_VERIFIED_NATIVE14_SIX_ORIGINALS_ALL5',
        head=head, tree=tree, run_id='23', workflow='LOCAL_PARENT_WORKFLOW_DOUBLE',
        outer_case_id='LOCAL_PARENT14', original11_ids=cfg['expected_parent11_ids'],
        reader3_ids=cfg['expected_parent3_ids'], originals={key: dict(original_pin,
            path='scripts/current-attendance-midnight-native1-qualification/accepted-parent14/' + key + '.json')
            for key in ('strict11', 'reader3', 'outer14', 'package', 'files', 'drill')})
    bound = cfg['accepted_parent14']
    strict, reader = group(bound['original11_ids']), group(bound['reader3_ids'])
    component = dict(status='PASS', native=strict, reader_native3=reader, actual_Native_cases=14,
        required_Native_case_ids=bound['original11_ids'] + bound['reader3_ids'],
        both_groups_same_actual_installation=True, reader3_requires_actual_fresh_original11=True,
        combined_strict14_fabricated=False,
        actual_installed_capture=dict(originals={str(i): CLASSIFICATION for i in range(15)},
            clones={'one': CLASSIFICATION, 'two': CLASSIFICATION},
            actual_all22={str(i): {} for i in range(22)}, source_derived_local_ABI_used=False),
        used_guard_refused_before_DDL=True, committed_choice_and_allocation={'LOCAL_DOUBLE': True},
        independent_Native_pool_oracle={'LOCAL_DOUBLE': True}, original_accrual_and_source_binding_unchanged=True,
        used_inverse_refusal_before={'LOCAL_ALL22_ROWS_SEQUENCES': True},
        used_inverse_refusal_after={'LOCAL_ALL22_ROWS_SEQUENCES': True})
    outer = dict(status='PASS', qualification_commit=head, required_case_ids=['LOCAL_PARENT14'],
        committed={'LOCAL_PARENT14': component}, actual_Native_cases=14, required_case_ids_pass=True,
        source_declaration=dict(current_installation=sources),
        restore_components={k: True for k in admission.RESTORE}, baseline_role_cleanup=dict(baseline_roles_exact=True),
        **{k: True for k in ('cp6_restored', 'baseline_full22_all_rows_all_sequences_equal',
            'baseline_advisors_equal', 'advisor_gate', 'used_guard_refused_before_DDL')})
    package = dict(status='ALL_STAGES_INSTALLED', gate={k: True for k in admission.FIVE},
        writer_runtime=dict(status='PASS'), primary_unchanged=True, backup_restore_drill='RESTORED_IDENTICAL',
        auth_users_before=0, auth_users_after=0, run_identity=dict(tool_head=head, github_sha=head,
            run_id='23', workflow=bound['workflow'], mode='install', job='p21'))
    files = dict(status='ALL_FILES_INSTALLED', files=[dict(key=str(i), status='PASS') for i in range(30)])
    drill = dict(status='RESTORED_IDENTICAL', checks={'LOCAL_DOUBLE': True},
                 catalog=dict(differ={}), data=dict(differ={}), engine=dict(equal=True))
    return cfg, sources, dict(strict11=strict, reader3=reader, outer14=outer,
                             package=package, files=files, drill=drill)


def new_result():
    cfg, sources, docs = parent()
    raw = group([ID])
    raw['cases'][ID].update(classification=CLASSIFICATION, source_cents=100003, exact_epoch_delta_us=1,
        full_business_rows_and_sequences_unchanged_for_reads=True, choice_waiting_without_allocation=True,
        original_accrual_unchanged=True, previews={k: dict(denominator=v) for k, v in
                                                 dict(BEFORE=5, AFTER=5, BOTH=10).items()})
    component = dict(status='PASS', midnight_native1=raw, required_Native_case_ids=[ID],
        actual_Native_cases=1, single_attempt=True, day_rollover_retry=False,
        fresh_original11_or14_reexecuted=False, combined_strict15_fabricated=False,
        actual_installed_capture=docs['outer14']['committed']['LOCAL_PARENT14']['actual_installed_capture'],
        committed_choice_and_allocation={'LOCAL_DOUBLE': True}, independent_Native_pool_oracle={'LOCAL_DOUBLE': True},
        used_guard_refused_before_DDL=True, original_accrual_and_source_binding_unchanged=True,
        used_inverse_refusal_before={'LOCAL_ALL22_ROWS_SEQUENCES': True},
        used_inverse_refusal_after={'LOCAL_ALL22_ROWS_SEQUENCES': True}, committed_used_witness_additional_cases=0)
    outer = dict(docs['outer14'], label=LABEL, qualification_commit='d' * 40, required_case_ids=[CASE],
        committed={CASE: component}, observed_case_count=1, expected_case_count=1,
        actual_Native_cases=1, actual_two_session_races=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0)
    package = deepcopy(docs['package'])
    package['run_identity'].update(tool_head='d' * 40, github_sha='d' * 40,
                                   workflow=cfg['workflow_name'], run_id='24')
    return outer, raw, package, docs['files'], docs['drill'], docs, cfg, 'd' * 40
