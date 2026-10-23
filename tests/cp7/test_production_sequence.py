"""Reproduce clone deletion between suites without Docker or Native claims."""
from pathlib import Path
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
import io
from contextlib import redirect_stdout

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts'))
spec=importlib.util.spec_from_file_location('production_sequence',REPO/'scripts/cp7_production_stage/probe_sequence.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
import cp7_production_stage as stage
import cp7_payment_source_owning_install as predecessor
CLONE=subprocess.check_output(['git','-C',str(REPO),'show',runner.WRITER_HEAD+':scripts/clone-cp6-disposable-database.sh'])


class SequenceTests(unittest.TestCase):
    def exercise(self,fail_clone=False):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp)/'auditor';out=root/'cp6-proof/t3/CP7_PRODUCTION_STAGE.json'
            pins=root/'scripts/ow04-consumer-closure-qualification/SOURCE.json';pins.parent.mkdir(parents=True)
            pins.write_text('{"product_sources":{}}')
            writer=Path(tmp)/'writer';(writer/'scripts').mkdir(parents=True)
            (writer/'scripts/clone-cp6-disposable-database.sh').write_bytes(CLONE)
            exists=True;started=[];clones=[]
            def run(args,**kwargs):
                nonlocal exists
                if args[0]=='bash':
                    self.assertFalse(exists)
                    self.assertEqual(args[2:7],[
                        'postgresql://postgres:postgres@127.0.0.1:54322/postgres',
                        'postgresql://postgres:postgres@127.0.0.1:54322/template1',
                        'postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback',
                        'cp6_rollback','supabase_db_cp5-local'])
                    self.assertTrue(kwargs['check']);clones.append(args)
                    if fail_clone:raise subprocess.CalledProcessError(1,args)
                    exists=True
                else:
                    self.assertTrue(exists,'the preceding retained package dropped the database')
                    probe=Path(args[1]).name;started.append(probe)
                    filename,count=next((f,n)for p,f,n in runner.SUITES if p==probe)
                    out.with_name(filename).write_text(json.dumps(dict(status='PASS',observed_case_count=count,
                        cp6_restored=True,advisor_gate=True,production_stage=dict(preuse_22_groups_exactly_restored=True))))
                    out.with_name('T3_PACKAGE_INSTALL.json').write_text(json.dumps({'suite':probe,'controlled_fixture':True}))
                    exists=False
                return subprocess.CompletedProcess(args,0)
            def head(args,**kwargs):return runner.WRITER_HEAD+'\n'if Path(args[2])==writer else'a'*40+'\n'
            with patch.object(runner,'ROOT',root),patch.object(runner,'OUT',out),patch.object(stage,'verify_sources',return_value={}),patch.object(predecessor,'sources',return_value={}),patch.object(runner.subprocess,'run',side_effect=run),patch.object(runner.subprocess,'check_output',side_effect=head),redirect_stdout(io.StringIO()):
                code=runner.main()
            report=json.loads(out.read_text())
            for entry in report['suites']:
                package=json.loads((out.parent/entry['package_Originals']/'T3_PACKAGE_INSTALL.json').read_text())
                self.assertEqual(package['suite'],entry['probe'])
            self.assertFalse(out.with_name('T3_PACKAGE_INSTALL.json').exists())
            return code,report,started,clones

    def test_each_restored_package_is_followed_by_a_fresh_clone_and_its_original_is_kept(self):
        code,r,started,clones=self.exercise()
        self.assertEqual(code,0);self.assertEqual(r['observed_case_count'],286)
        self.assertEqual(len(started),6);self.assertEqual(len(clones),5)
        self.assertEqual([s['fresh_aligned_AB_clone']for s in r['suites']],[False,True,True,True,True,True])

    def test_a_clone_failure_keeps_the_first_original_and_never_starts_the_next_suite(self):
        code,r,started,clones=self.exercise(fail_clone=True)
        self.assertEqual(code,1);self.assertEqual(r['status'],'INCOMPLETE')
        self.assertEqual(len(started),1);self.assertEqual(len(clones),1)
        self.assertEqual(r['suites'][0]['observed_case_count'],113)

    def test_unpinned_writer_is_refused_before_clone(self):
        with patch.object(runner.subprocess,'check_output',return_value='0'*40),patch.object(runner.subprocess,'run')as run:
            with self.assertRaisesRegex(ValueError,'CP7_PRODUCTION_CLONE_WRITER_CHANGED'):
                runner.prepare_next(2)
            run.assert_not_called()


if __name__=='__main__':unittest.main()
