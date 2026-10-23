"""Transport/authorization controls, not execution of database replay SQL."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock, patch
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import cp7_ow13a_clone_authority as module


class InitialCloneAuthority(TestCase):
    def setUp(self):
        module.RECEIPTS.clear()

    def test_primary_source_template_and_injected_names_never_call_copy(self):
        original=Mock()
        for name in ('postgres','template1','cp6_rollback','cp6_unknown','cp6_auditor_race;drop database postgres'):
            with self.assertRaisesRegex(ValueError,'OW13A_CLONE_NAME_REFUSED'):
                module.copied_with_authority(original,name,'unused.json')
        original.assert_not_called()

    def test_foreign_or_wrong_local_url_never_reads_or_mutates(self):
        for url in ('postgresql://postgres:fixture@example.com:54322/cp6_auditor_race',
                    'postgresql://postgres:fixture@127.0.0.1:5432/cp6_auditor_race',
                    'postgresql://postgres:fixture@127.0.0.1:54322/postgres',
                    'https://127.0.0.1:54322/cp6_auditor_race'):
            with patch.object(module.psycopg,'connect')as connect,patch.object(module.subprocess,'run')as execute:
                with self.assertRaisesRegex(ValueError,'OW13A_CLONE_LOCAL_URL_REFUSED'):
                    module.copied_with_authority(lambda name:url,'cp6_auditor_race','unused.json')
                connect.assert_not_called();execute.assert_not_called()

    def test_all_authority_members_must_match_and_receipt_keeps_both_hashes(self):
        expected={'CURRENT':['postgres', 'UTF8', 'C', 'C', -1, False, True, [['postgres','postgres','CONNECT',False]], None]}
        wrong={'CURRENT':['supabase_admin', 'UTF8', 'C', 'C', -1, False, True, [], None]}
        url='postgresql://postgres:fixture@127.0.0.1:54322/cp6_auditor_race'
        with TemporaryDirectory()as tmp,patch.object(module.psycopg,'connect'),\
             patch.object(module,'authority',side_effect=[expected,wrong,expected]),\
             patch.object(module.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr=''))as execute:
            path=Path(tmp)/'receipt.json'
            self.assertEqual(module.copied_with_authority(lambda name:url,'cp6_auditor_race',path),url)
            receipt=json.loads(path.read_text())['copies'][0]
            self.assertEqual(receipt['previous_owner'],'supabase_admin');self.assertEqual(receipt['current_owner'],'postgres')
            self.assertEqual(receipt['source_authority_sha256'],receipt['after_authority_sha256'])
            self.assertNotEqual(receipt['source_authority_sha256'],receipt['before_authority_sha256'])
            self.assertFalse(receipt['oracle_relaxed']);self.assertFalse(receipt['primary_modified'])
            args=execute.call_args.args[0]
            self.assertEqual(args[:8],['docker','exec','supabase_db_cp5-local','psql','-U','supabase_admin','-d','template1'])
            self.assertIn('owner to postgres',args[-1]);self.assertEqual(execute.call_args.kwargs['timeout'],60)

    def test_acl_or_guc_difference_after_replay_cannot_be_success(self):
        expected={'CURRENT':['postgres','C',{'acl_hash':'fixed','guc_hash':'fixed'}]}
        for member in ('acl_hash','guc_hash'):
            changed={'CURRENT':['postgres','C',{'acl_hash':'fixed','guc_hash':'fixed'}]};changed['CURRENT'][2][member]='changed'
            with patch.object(module.psycopg,'connect'),patch.object(module,'authority',side_effect=[expected,expected,changed]),\
                 patch.object(module.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='')):
                with self.assertRaisesRegex(ValueError,'OW13A_CLONE_AUTHORITY_NOT_EXACT'):
                    module.copied_with_authority(lambda name:'postgresql://postgres:fixture@127.0.0.1:54322/'+name,
                                                 'cp6_auditor_http','unused.json')
            self.assertEqual(module.RECEIPTS,[])


if __name__=='__main__':main()
