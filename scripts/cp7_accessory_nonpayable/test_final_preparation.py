"""Canonical byte/supervision and closed-parent controls, zero ERP credit."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import gzip,sys,unittest
from . import final_gate as gate,fetch_parent

class FinalPreparationControls(unittest.TestCase):
    def test_raw_census_requires_all_original_rows_and_rejects_money_change_or_masked_history(self):
        catalog={str(i):{}for i in range(22)}
        before=dict(catalog=catalog,data_and_all_sequences={'erp.journal_lines':[1,'money'],
            'cp7_accessory_nonpayable.date_requests_v1':[1,'old']},date_versions=[],date_requests=[dict(request_id='old',intent='kept')])
        after=deepcopy(before);self.assertEqual(gate.compare_census(before,after,[],catalog),[])
        for mode in('money','hidden_history','catalog'):
            bad=deepcopy(after)
            if mode=='money':bad['data_and_all_sequences']['erp.journal_lines']=[1,'wrong']
            elif mode=='hidden_history':bad['date_requests'][0]['intent']='edited'
            else:bad['catalog']['0']={'missing':'field'}
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.compare_census(before,bad,[],catalog)

    def test_race_facts_require_two_actual_pids_exact_reply_and_same_single_date_request(self):
        response=dict(status='SAVED',id='date',request_id='request')
        row=dict(results=[dict(ok=True,backend_pid=101,request_id='request',result=response),
            dict(ok=True,backend_pid=102,request_id='request',result=deepcopy(response))],
            actual_versions=[dict(id='date',request_id='request')],actual_requests=[dict(request_id='request',response=response)])
        gate.race_facts(row,same=True)
        for mode in('same_pid','other_request','other_date'):
            bad=deepcopy(row)
            if mode=='same_pid':bad['results'][1]['backend_pid']=101
            elif mode=='other_request':bad['results'][1]['request_id']='other'
            else:bad['actual_versions'][0]['id']='other'
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.race_facts(bad,same=True)

    def test_full_gate_refuses_before_reading_any_artifact_when_parent_is_missing(self):
        with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
            gate.gate(Path('/missing-canonical-directory'),'a'*40)

    def test_fetcher_refuses_parent_before_derivation_or_any_GitHub_GET(self):
        with patch.object(fetch_parent,'derive',side_effect=AssertionError('DERIVE_BEFORE_ACTUAL_PARENT')):
            with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):fetch_parent.main()

    def test_full_gzip_original_requires_both_checksums_and_safe_non_symlink_path(self):
        raw=b'{"synthetic_complete_census":true}\n';packed=gzip.compress(raw,mtime=0)
        reference=dict(name='MODEL_FULL_CENSUS.json.gz',bytes=len(raw),sha256=sha256(raw).hexdigest(),
            gzip_bytes=len(packed),gzip_sha256=sha256(packed).hexdigest())
        with TemporaryDirectory(prefix='afui-final-raw-control-')as directory:
            directory=Path(directory);(directory/reference['name']).write_bytes(packed)
            self.assertEqual(gate.artifact(directory,reference),raw)
            for mode in('raw_sha','gzip_sha','path','symlink'):
                bad=deepcopy(reference)
                if mode=='raw_sha':bad['sha256']='0'*64
                elif mode=='gzip_sha':bad['gzip_sha256']='0'*64
                elif mode=='path':bad['name']='../MODEL_FULL_CENSUS.json.gz'
                else:
                    (directory/'link.json.gz').symlink_to(directory/reference['name']);bad['name']='link.json.gz'
                with self.subTest(mode=mode),self.assertRaises(ValueError):gate.artifact(directory,bad)

    def test_supervision_requires_actual_identity_complete_reap_and_exact_full_budgets(self):
        p=gate.load('afui_final_model_original_typed_fields',gate.ROOT/'scripts/current-s03-sku-s05-composite-qualification/parents.py')
        value=dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit='a'*40,github_run_id='12345',
            github_run_attempt='1',worker_exit=0,deadline_reached=False,external_signal=None,orphaned_child=False,
            process_group_empty=True,process_tree_empty=True,signals=[],actual_case_credit=0,production_go=False,
            job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600)
        self.assertEqual(gate.supervisor(p,value,'a'*40,'12345')['actual_case_credit'],0)
        for key,wrong in(('worker_exit',False),('qualification_commit','b'*40),('process_tree_empty',False),('work_budget_seconds',5400)):
            bad=deepcopy(value);bad[key]=wrong
            with self.subTest(key=key),self.assertRaises(ValueError):gate.supervisor(p,bad,'a'*40,'12345')

if __name__=='__main__':unittest.main()
