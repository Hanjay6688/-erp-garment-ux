"""Mutation controls over actual Originals; zero Native/DB/HTTP execution.

All mutations live in memory. No Original, source worktree, transaction or
frozen manifest is modified. Successful controls confer no extra case credit.
"""
from copy import deepcopy
import argparse

from intake_common import GitBytes, exact, original_zip, originals, require, save, script_pins
import intake_lock_model as lock
import intake_s05 as s05


class ChangedBlob:
    def __init__(self, git, name, transform):
        self._git = git
        self.name = name
        self.transform = transform

    def __getattr__(self, name):
        return getattr(self._git, name)

    def read(self, name, ref=None):
        raw = self._git.read(name, ref)
        return self.transform(raw) if name == self.name and ref is None else raw

    def verify_pin(self, name, expected):
        # Keep the real pin verifier while routing its read through this proxy.
        return GitBytes.verify_pin(self, name, expected)


def control(label, operation, rows):
    try:
        operation()
    except ValueError as error:
        rows.append(dict(id=label, status='REFUSED_AS_REQUIRED', refusal=str(error)))
    else:
        raise AssertionError('ROOT_INTAKE_MUTATION_INCORRECTLY_ACCEPTED:' + label)


def run(s05_root, s05_archive, lock_root, lock_archive):
    with original_zip(s05_archive, s05.ZIP_PIN, 114) as z:
        _, original_s05 = originals(z, s05.RAW_PINS)
    with original_zip(lock_archive, lock.ZIP_PIN, 3) as z:
        _, original_lock = originals(z, lock.RAW_PINS)
    rows = []
    with GitBytes(s05_root, s05.HEAD, s05.TREE) as sg, GitBytes(lock_root, lock.HEAD, lock.TREE) as lg:
        exact(s05.checked(sg, original_s05)['actual_Native_cases'], 10, 'ROOT_CONTROL_ORIGINAL_S05_POSITIVE')
        exact(lock.checked(lg, original_lock)['actual_model_observations'], 32, 'ROOT_CONTROL_ORIGINAL_LOCK_POSITIVE')

        def mutate_s05(label, operation):
            docs = deepcopy(original_s05)
            operation(docs)
            control('S05_' + label, lambda: s05.checked(sg, docs), rows)

        def outer(docs):
            return docs[s05.MAIN]

        def component(docs):
            return outer(docs)['committed'][s05.CASE]

        def both_group_count(docs):
            docs[s05.CASES]['counts']['PASS'] = 10.0
            component(docs)['native']['counts']['PASS'] = 10.0

        changes_s05 = [
            ('CHANGED_COMPONENT_ID', lambda d: outer(d)['committed'].__setitem__('UNDECLARED', outer(d)['committed'].pop(s05.CASE))),
            ('BOOL_FOR_ONE_EXPECTED_CASE', lambda d: outer(d).__setitem__('expected_case_count', True)),
            ('FLOAT_FOR_NATIVE10', lambda d: outer(d).__setitem__('actual_Native_cases', 10.0)),
            ('FLOAT_FOR_GROUP_PASS10', both_group_count),
            ('CHANGED_STRICT_ORIGINAL_ID', lambda d: d[s05.CASES]['planned_case_ids'].__setitem__(0, 'UNDECLARED')),
            ('OUTER_RESTORE_FALSE', lambda d: outer(d).__setitem__('baseline_full22_all_rows_all_sequences_equal', False)),
            ('ROLE_RESTORE_FALSE', lambda d: outer(d)['baseline_role_cleanup'].__setitem__('baseline_roles_exact', False)),
            ('ALL5_WRITER_GATE_FALSE', lambda d: d[s05.PACKAGE]['gate'].__setitem__('writer_runtime', False)),
            ('AUTH_BOOL_FOR_ZERO', lambda d: d[s05.PACKAGE].__setitem__('auth_users_after', False)),
            ('DRILL_ROW_COUNT_FLOAT', lambda d: d[s05.RESTORE]['data'].__setitem__('rows', 1860.0)),
            ('READER_PARENT_CHANGED', lambda d: component(d)['reader_intervals'][2]['actual_reader_verification'].__setitem__('parent_verified_before_addition', False)),
            ('USED_INVERSE_WRONG_ERROR', lambda d: component(d)['separate_committed_business_witness'].__setitem__('actual_used_guard_error', 'UNDECLARED')),
            ('PROTECTED_ROLE_WRONG_SQLSTATE', lambda d: component(d)['current_AC_editor_fixture']['actual_wib_owner_fixture_observations'][6]['actual_error'].__setitem__('sqlstate', 'P0001')),
            ('OWNER_REFUSAL_NOEFFECT_FALSE', lambda d: component(d)['current_AC_editor_fixture']['actual_wib_owner_fixture_observations'][5].__setitem__('all_rows_and_every_sequence_equal', False)),
            ('CURRENT_AC_EDITOR_BODY_CHANGED', lambda d: component(d)['current_editor_preflight_observations'][0].__setitem__('observed_prosrc_sha256', '0' * 64)),
            ('CURRENT_ACCESS_REFUSAL_REMOVED', lambda d: component(d)['native']['cases'][s05.IDS[9]]['actual_raw_reads'][0]['actual_error'].__setitem__('sqlstate', '00000')),
            ('FALSE_S05_FAMILY_ACCEPTANCE', lambda d: component(d)['native']['cases'][s05.IDS[0]].__setitem__('full_family_acceptance', True)),
            ('SOURCE_FULL_PATH_PIN_CHANGED', lambda d: outer(d)['source_declaration']['qualification']['files'].__setitem__('scripts/cp6_bc_probe.py', '0' * 64)),
            ('RELATIVE_SOURCE_UNKNOWN_CONTRACT', lambda d: outer(d)['source_declaration']['current_installation']['predecessor']['predecessor'].__setitem__('contract', 'UNDECLARED')),
        ]
        for label, operation in changes_s05:
            mutate_s05(label, operation)
        control('S05_GIT_CALLBACK_BYTES_CHANGED', lambda: s05.checked(
            ChangedBlob(sg, 'scripts/cp7_accessory_standard_report/cases.py', lambda raw: raw + b'\n'), original_s05), rows)
        control('S05_GIT_FULL_PATH_SOURCE_BYTES_CHANGED', lambda: s05.checked(
            ChangedBlob(sg, 'scripts/cp6_bc_probe.py', lambda raw: raw + b'\n'), original_s05), rows)
        control('S05_GIT_PRODUCER_ROUTE_REPLACED_BY_IDENTICAL_ALIAS', lambda: s05.checked(ChangedBlob(sg,
            'scripts/current-factory-initial-stage/composition.py', lambda raw: raw.replace(
                b'current-finance-factory-progress-followup-qualification',
                b'current-finance-reader-stream-followup-qualification')), original_s05), rows)
        contract = 'cp7.current-consistent-finance-private-opening.v2'
        original_namespace = s05.CONTRACT_DIRS[contract]
        try:
            s05.CONTRACT_DIRS[contract] = 'current-finance-reader-stream-followup-qualification'
            control('S05_BASENAME_PIN_MUST_NOT_BIND_IDENTICAL_OTHER_NAMESPACE',
                    lambda: s05.checked(sg, original_s05), rows)
        finally:
            s05.CONTRACT_DIRS[contract] = original_namespace

        def mutate_lock(label, operation):
            docs = deepcopy(original_lock)
            operation(docs)
            control('LOCK_' + label, lambda: lock.checked(lg, docs), rows)

        def report(docs):
            return docs[lock.REPORT]

        changes_lock = [
            ('IMAGE_ID_OBJECT_FOR_STRING', lambda d: d.__setitem__(lock.IMAGE_ID, {'id': lock.IMAGE})),
            ('DIGEST_STRING_FOR_LIST', lambda d: d.__setitem__(lock.IMAGE_DIGESTS, lock.DIGEST)),
            ('IMAGE_DIGEST_CHANGED', lambda d: d.__setitem__(lock.IMAGE_DIGESTS, ['postgres@sha256:' + '0' * 64])),
            ('PAIR_MISSING', lambda d: report(d)['pairs'].pop()),
            ('PAIR_DUPLICATED', lambda d: report(d)['pairs'].__setitem__(-1, deepcopy(report(d)['pairs'][0]))),
            ('WRONG_ROW_SHARE_SRE_CONFLICT', lambda d: report(d)['pairs'][4].__setitem__('refused', True)),
            ('WRONG_LOCK_SQLSTATE', lambda d: report(d)['pairs'][-1].__setitem__('sqlstate', '57014')),
            ('TWO_ACTUAL_BACKENDS_FALSE', lambda d: report(d)['pairs'][0].__setitem__('two_actual_backends', False)),
            ('MATRIX_COUNT_FLOAT', lambda d: report(d)['matrix_gate'].__setitem__('actual_lock_pairs', 24.0)),
            ('SOURCE_COUNT_FLOAT', lambda d: report(d)['source'].__setitem__('files', 5.0)),
            ('ACTUAL_FK_ROW_SHARE_MISSING', lambda d: report(d)['foreign_key_holders'][0].__setitem__('actual_FK_parent_locks', [])),
            ('EXCLUSIVE_FK_REFUSAL_MISSING', lambda d: report(d)['foreign_key_holders'][1].__setitem__('sqlstate', None)),
            ('BUSY_SEQUENCE_CHANGED', lambda d: report(d)['before_effect_busy']['model_after']['sequences']['before_effect_seq'].__setitem__(1, True)),
            ('BUSY_SEQUENCE_BOOL_FOR_ONE', lambda d: report(d)['before_effect_busy']['model_before']['sequences']['before_effect_seq'].__setitem__(0, True)),
            ('PLAIN_SELECT_UNAVAILABLE', lambda d: report(d)['ordinary_reader'].__setitem__('plain_SELECT_while_EXCLUSIVE_held', False)),
            ('ACTUAL_WAIT_MISSING', lambda d: report(d)['real_blocking'].pop()),
            ('HOLDER_EQUALS_WORKER_PID', lambda d: report(d)['real_blocking'][0].__setitem__('worker_pid', report(d)['real_blocking'][0]['holder_pid'])),
            ('PID_FLOAT', lambda d: report(d)['real_blocking'][0].__setitem__('worker_pid', float(report(d)['real_blocking'][0]['worker_pid']))),
            ('WORKER_ROLLBACK_FALSE', lambda d: report(d)['real_blocking'][0]['worker'].__setitem__('worker_changes_rolled_back', False)),
            ('MODEL_ROWS_SEQUENCES_RESTORE_FALSE', lambda d: report(d).__setitem__('complete_model_rows_sequences_equal', False)),
            ('SCHEMA_OR_SESSION_CLEANUP_FALSE', lambda d: report(d).__setitem__('model_removed_and_no_session_leaks', False)),
            ('ERP_NATIVE_CREDIT_FALSELY_ADDED', lambda d: report(d).__setitem__('actual_ERP_Native_cases', 1)),
            ('ERP_LOCK_PROFILE_FALSELY_QUALIFIED', lambda d: report(d).__setitem__('ERP_lock_profile_qualified', True)),
        ]
        for label, operation in changes_lock:
            mutate_lock(label, operation)
        control('LOCK_GIT_MATRIX_SOURCE_BYTES_CHANGED', lambda: lock.checked(
            ChangedBlob(lg, lock.NS + 'matrix.py', lambda raw: raw + b'\n'), original_lock), rows)

        # Mutations must leave the actual positive input and route state intact.
        require(s05.checked(sg, original_s05)['strict_original_equals_embedded'], 'ROOT_S05_POST_CONTROL_POSITIVE')
        require(lock.checked(lg, original_lock)['model_schema_removed_and_no_session_leaks'], 'ROOT_LOCK_POST_CONTROL_POSITIVE')
    return dict(status='ROOT_SOURCE_ONLY_INTAKE_MUTATIONS_REFUSED',
        positive_actual_originals_before_and_after=True, refused_controls=len(rows), controls=rows,
        actual_new_Native_cases=0, actual_new_ERP_or_model_DB_execution=0,
        actual_HTTP_browser_or_races=0, Originals_or_source_worktrees_modified=False,
        production_go=False, independent_acceptance=False,
        intake_scripts=script_pins('intake_s05.py', 'intake_lock_model.py', 'intake_controls.py'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('s05-source-root', 's05-archive', 'lock-source-root', 'lock-archive', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    save(run(args.s05_source_root, args.s05_archive, args.lock_source_root, args.lock_archive), args.output)
