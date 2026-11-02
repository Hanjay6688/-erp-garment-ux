"""Exact engine and typed future-result refusal controls, zero ERP credit."""
from copy import deepcopy
import unittest
from . import package_engine as engine,qualification_gate as gate

class PackagePreparationControls(unittest.TestCase):
    def test_supervisor_recovers_original_process_engine_and_refuses_parent_before_worker(self):
        from . import runtime_supervisor as supervisor
        from unittest.mock import patch
        raw=(supervisor.ROOT/supervisor.ORIGINAL).read_bytes();text,proof=supervisor.derive(raw)
        for before,after in reversed(supervisor.CHANGES):text=text.replace(after,before,1)
        self.assertEqual(text.encode(),raw);self.assertTrue(proof['process_engine_and_original_360_330_20_10_budgets_unchanged'])
        with patch('sys.argv',['runtime_supervisor.py']),self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
            supervisor.main()

    def test_typed_copy_gate_refuses_bool_database_count_and_missing_auth_census(self):
        report=dict(status='RUN_COMPLETE',counts={'PASS':1},planned_case_ids=['HTTP'],database_remaining=0,real_auth=True,
            jwt_signed_by_runtime=False,test_only_usage_grant=False,auth_counts=dict(before=[1,1,0,0],after=[1,1,0,0],restored=True),
            cleanup=dict(cleanup_failures=[],rest_remaining=False),cases={'HTTP':dict(status='PASS',session_leaks=[],real_Auth_HTTP=True)})
        for mode in('bool_db','missing_auth','bool_case_count'):
            bad=deepcopy(report)
            if mode=='bool_db':bad['database_remaining']=False
            elif mode=='missing_auth':bad['auth_counts']={'restored':True}
            else:bad['counts']={'PASS':True}
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.copies(bad,['HTTP'],mode='HTTP')

    def test_whole_qualifier_refuses_closed_parent_before_runtime_construction(self):
        from . import qualification
        with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):qualification.runtime()

    def test_full_engine_is_recovered_with_only_parent_install_and_case_count_routes(self):
        raw=(engine.ROOT/engine.ORIGINAL).read_bytes();text,proof=engine.derive(raw)
        recovered=text.replace(engine.COUNTS_AFTER,engine.COUNTS_BEFORE,1).replace(engine.INSTALL_AFTER,engine.INSTALL_BEFORE,1)
        self.assertEqual(recovered.encode(),raw);self.assertEqual(proof['exact_reversible_changes'],2)
        self.assertTrue(proof['install_preuse_reinstall_used_backup_roles_all22_ALL_rows_ALL_sequences_CP6_advisors_Auth_package_checks_retained'])
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_WHOLE_PACKAGE_ENGINE_REQUIRED'):engine.derive(raw+b'\n')

    def test_case_gate_rejects_missing_duplicate_status_or_session_evidence(self):
        native=dict(status='PASS',counts={'PASS':1},planned_case_ids=['NATIVE'],complete_boundary_restored=True,
            cases={'NATIVE':dict(status='PASS',session_leaks=dict(advisory_locks=0,advisory_lock_keys=[],other_sessions=[]),
                full_boundary_restored=True,public_schema_unchanged=True,actual_full22_case_boundary={'verification':dict(
                    all22_catalog_exact=True,all_table_rows_restored=True,all_other_sequences_unchanged=True,
                    observed_sequences_unchanged_by_rollback=True,case_sequence_reset_performed=False,
                    complete_outer_backup_ALL_sequence_restore_required=True)})})
        self.assertEqual(gate.native(native,['NATIVE'])['actual_Native_cases'],1)
        for mode in('missing','count','session','reset'):
            bad=deepcopy(native)
            if mode=='missing':bad['cases']={}
            elif mode=='count':bad['counts']={'PASS':2}
            elif mode=='session':bad['cases']['NATIVE']['session_leaks']['other_sessions']=[999]
            else:bad['cases']['NATIVE']['actual_full22_case_boundary']['verification']['case_sequence_reset_performed']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.native(bad,['NATIVE'])

    def test_real_auth_copy_gate_rejects_fabricated_token_unrestored_auth_or_retained_db(self):
        report=dict(status='RUN_COMPLETE',counts={'PASS':1},planned_case_ids=['HTTP'],database_remaining=0,real_auth=True,
            jwt_signed_by_runtime=False,test_only_usage_grant=False,auth_counts=dict(before=[1,1,0,0],after=[1,1,0,0],restored=True),
            cleanup=dict(cleanup_failures=[],rest_remaining=False),cases={'HTTP':dict(status='PASS',session_leaks=[],real_Auth_HTTP=True)})
        self.assertEqual(gate.copies(report,['HTTP'],mode='HTTP')['actual_cases'],1)
        for mode in('token','auth','database'):
            bad=deepcopy(report)
            if mode=='token':bad['jwt_signed_by_runtime']=True
            elif mode=='auth':bad['auth_counts']['after']=[2,1,0,0]
            else:bad['database_remaining']=1
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.copies(bad,['HTTP'],mode='HTTP')

if __name__=='__main__':unittest.main()
