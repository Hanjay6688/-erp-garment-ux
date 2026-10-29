"""Labelled in-memory report/schema doubles only; never actual Native evidence."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


gate = load('s03_reader14_local_structural_result_gate', HERE / 'result_gate.py')
reader = load('s03_reader14_local_fresh_group_gate', HERE / 'reader_group.py')


def doubles():
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    cfg['runtime_files'] = {'LOCAL_STRUCTURAL_SOURCE_DOUBLE_' + str(i): 'd' * 64 for i in range(7)}
    def group(ids):
        return dict(status='PASS', counts={'PASS': len(ids)}, planned_case_ids=ids, complete_boundary_restored=True,
            cases={key: dict(status='PASS', full_boundary_restored=True, public_schema_unchanged=True) for key in ids})
    old, new = group(cfg['original_Native11_ids']), group(cfg['reader_Native3_ids'])
    component = dict(status='PASS', native=old, reader_native3=new, actual_Native_cases=14,
        required_Native_case_ids=cfg['Native_case_ids'], both_groups_same_actual_installation=True,
        reader3_requires_actual_fresh_original11=True, combined_strict14_fabricated=False,
        actual_installed_capture=dict(originals={str(i): 'SYNTHETIC_LOCAL_CAPTURE_DOUBLE' for i in range(15)},
            clones={'one': 'LOCAL', 'two': 'LOCAL'}, actual_all22={str(i): {} for i in range(22)}, source_derived_local_ABI_used=False),
        used_guard_refused_before_DDL=True, original_accrual_and_source_binding_unchanged=True,
        used_inverse_refusal_before=dict(actual_all22={'LOCAL': 'DOUBLE'}, full_data_and_sequences={'sequence:LOCAL': 1}),
        used_inverse_refusal_after=dict(actual_all22={'LOCAL': 'DOUBLE'}, full_data_and_sequences={'sequence:LOCAL': 1}),
        committed_choice_and_allocation=dict(classification='SYNTHETIC_UNIT_ONLY_NOT_COMMITTED'),
        independent_Native_pool_oracle=dict(classification='SYNTHETIC_UNIT_ONLY_NOT_NATIVE'))
    outer = dict(status='PASS', label=gate.LABEL, required_case_ids=[gate.CASE], expected_case_count=1, observed_case_count=1,
        qualification_commit='b' * 40, committed={gate.CASE: component}, cp6_restored=True,
        baseline_full22_all_rows_all_sequences_equal=True, baseline_advisors_equal=True,
        advisor_gate=True, used_guard_refused_before_DDL=True, required_case_ids_pass=True,
        restore_components=dict(LOCAL_STRUCTURAL_RESTORE_DOUBLE=True), baseline_role_cleanup=dict(baseline_roles_exact=True),
        actual_Native_cases=14, actual_two_session_races=0, actual_Auth_HTTP_cases=0, actual_browser_cases=0,
        source_declaration=dict(current_installation=dict(files=cfg['runtime_files'])))
    package = dict(status='ALL_STAGES_INSTALLED', gate={key: True for key in gate.FIVE}, primary_unchanged=True,
        backup_restore_drill='RESTORED_IDENTICAL', auth_users_before=0, auth_users_after=0, writer_runtime=dict(status='PASS'),
        run_identity=dict(tool_head='b' * 40, github_sha='b' * 40, workflow='CP7 A S03 attendance choice plus owning readers Native14',
            job='p21', mode='install', run_id='1'))
    files = dict(status='ALL_FILES_INSTALLED', files=[dict(key=str(i), status='PASS') for i in range(30)])
    drill = dict(status='RESTORED_IDENTICAL', checks=dict(LOCAL_STRUCTURAL_DRILL_DOUBLE=True), data=dict(differ={}), catalog=dict(differ={}), engine=dict(equal=True))
    return outer, old, new, package, files, drill, cfg


class ResultControls(TestCase):
    def test_labelled_structural_complete_gate_double_passes_without_extra_case_credit(self):
        value = gate.checked(*doubles())
        self.assertEqual(value['actual_Native_cases'], 14)
        self.assertEqual(value['actual_groups'], [11, 3])
        self.assertFalse(value['combined_strict14_fabricated'])
        self.assertFalse(value['production_go'])

    def test_bad_fresh11_closes_reader_before_importing_any_factory_or_cursor(self):
        cfg = doubles()[-1]
        with patch.object(reader.importlib.util, 'spec_from_file_location', side_effect=AssertionError('READER_FACTORY_IMPORTED_BEFORE_FRESH11')):
            for group in (dict(status='INCOMPLETE'), dict(status='PASS', counts={'PASS': 11})):
                with self.assertRaisesRegex(ValueError, 'COMPLETE_STRICT_GROUP'):
                    reader.run(None, None, None, {}, None, group)

    def test_original11_and_reader3_exactIDs_both_restored_and_unprojected_are_required(self):
        mutations = [(1, lambda v: v['planned_case_ids'].pop()),
            (2, lambda v: v['counts'].update(PASS=2)),
            (2, lambda v: v['cases'][next(iter(v['cases']))].update(full_boundary_restored=False)),
            (1, lambda v: v['cases'][next(iter(v['cases']))].update(public_schema_unchanged=False)),
            (2, lambda v: v.update(error='LOCAL_DECLARED_GROUP_FAILURE'))]
        for index, mutate in mutations:
            values = list(deepcopy(doubles())); mutate(values[index])
            with self.assertRaisesRegex(ValueError, 'STRICT_GROUP|CASE_BOUNDARY'):
                gate.checked(*values)

    def test_count14_does_not_accept_a_fabricated_combined_group_or_unknownID(self):
        values = list(deepcopy(doubles())); values[1]['counts'] = {'PASS': 14}
        with self.assertRaisesRegex(ValueError, 'COMPLETE_STRICT_GROUP'):
            gate.checked(*values)
        values = list(deepcopy(doubles())); values[0]['committed'][gate.CASE]['combined_strict14_fabricated'] = True
        with self.assertRaisesRegex(ValueError, 'BOTH_EXACT_RAW_GROUPS'):
            gate.checked(*values)

    def test_nested_groups_must_equal_exact_separate_raw_originals(self):
        values = list(deepcopy(doubles())); values[0]['committed'][gate.CASE]['reader_native3'] = dict(status='PASS', counts={'PASS': 3})
        with self.assertRaisesRegex(ValueError, 'BOTH_EXACT_RAW_GROUPS'):
            gate.checked(*values)

    def test_capture15_clones2_current_runtime7_cannot_be_old13_or_static_seed(self):
        for mutate in (lambda v: v['actual_installed_capture']['originals'].pop('14'),
                       lambda v: v['actual_installed_capture'].update(source_derived_local_ABI_used=True),
                       lambda v: v['actual_installed_capture']['clones'].pop('one')):
            values = list(deepcopy(doubles())); mutate(values[0]['committed'][gate.CASE])
            with self.assertRaisesRegex(ValueError, 'REAL_CAPTURE15'):
                gate.checked(*values)
        values = list(deepcopy(doubles())); values[0]['source_declaration']['current_installation']['files'] = {'old': 'LOCAL'}
        with self.assertRaisesRegex(ValueError, 'CURRENT_RUNTIME7'):
            gate.checked(*values)

    def test_used_guard_must_be_committed_and_preserve_all22_data_sequences_and_accrual(self):
        for mutate in (lambda v: v.update(committed_choice_and_allocation=None),
                       lambda v: v.update(original_accrual_and_source_binding_unchanged=False),
                       lambda v: v['used_inverse_refusal_after']['full_data_and_sequences'].update(changed=1)):
            values = list(deepcopy(doubles())); mutate(values[0]['committed'][gate.CASE])
            with self.assertRaisesRegex(ValueError, 'COMMITTED_ALLOCATE_USED_WITNESS'):
                gate.checked(*values)

    def test_full_outer_rows_sequences_roles_CP6_advisors_and_every_restore_required(self):
        for mutate in (lambda v: v.update(cp6_restored=False),
                       lambda v: v.update(baseline_full22_all_rows_all_sequences_equal=False),
                       lambda v: v['restore_components'].update(ROLE_DOUBLE=False),
                       lambda v: v['baseline_role_cleanup'].update(baseline_roles_exact=False)):
            values = list(deepcopy(doubles())); mutate(values[0])
            with self.assertRaisesRegex(ValueError, 'RESTORE|ROLES_EXACT'):
                gate.checked(*values)

    def test_all5_writer_primary_Auth_drill_and_packagefiles_are_mandatory(self):
        for mutate in (lambda v: v['gate'].update(writer_runtime=False),
                       lambda v: v.update(auth_users_after=1),
                       lambda v: v.update(primary_unchanged=False)):
            values = list(deepcopy(doubles())); mutate(values[3])
            with self.assertRaisesRegex(ValueError, 'ALL5_PACKAGE_GATES'):
                gate.checked(*values)
        values = list(deepcopy(doubles())); values[4]['files'].pop()
        with self.assertRaisesRegex(ValueError, 'THIRTY_PACKAGE_FILES'):
            gate.checked(*values)
        values = list(deepcopy(doubles())); values[5]['catalog']['differ'] = {'LOCAL': 'DIFFER'}
        with self.assertRaisesRegex(ValueError, 'COMPLETE_BACKUP_DRILL'):
            gate.checked(*values)

    def test_a_different_parent_package_or_source_head_cannot_cover_new14(self):
        values = list(deepcopy(doubles())); values[3]['run_identity'].update(tool_head='c' * 40, github_sha='c' * 40)
        with self.assertRaisesRegex(ValueError, 'SAME_CURRENT_OUTER_PACKAGE_RUN_SOURCE'):
            gate.checked(*values)


if __name__ == '__main__':
    main(verbosity=2)
