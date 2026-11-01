"""Root source/AST/canonical-original controls, zero ERP qualification credit."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from hashlib import sha256
import argparse,copy,gzip,json,sys,unittest
import intake_afui15 as target
from intake_common import GitBytes

ROOT=None
PROOFS={}

class Afui15RootPreparationControls(unittest.TestCase):
    def test_closed_intake_refuses_before_git_archive_or_metadata(self):
        for name in('HEAD','TREE','RUN','JOB','PARENT_HEAD','PARENT_TREE','PARENT_RUN','PARENT_JOB'):
            self.assertIsNone(getattr(target,name))
        with patch.object(target,'GitBytes',side_effect=AssertionError('GIT_BEFORE_ACTUAL_IDENTITY')):
            with self.assertRaisesRegex(ValueError,'ACTUAL_PARENT_AND_OWNING_RUN_NOT_YET_PINNED'):
                target.intake(None,None,None)

    def test_pure_selector_rejects_runtime_import_calls_decorators_and_magic_attributes(self):
        snippets=["def validate():\n import psycopg\n return 1\n",
            "def validate():\n from os import system\n return 1\n",
            "def validate():\n return open('/not-an-original')\n",
            "def validate():\n return object.__subclasses__()\n",
            "@open('/not-an-original')\ndef validate():\n return 1\n",
            "def validate(x=open('/not-an-original')):\n return x\n"]
        for snippet in snippets:
            with self.subTest(snippet=snippet),self.assertRaises(ValueError):
                target.pure_functions(snippet.encode(),'LABELLED_SYNTHETIC_SELECTOR_CONTROL',('validate',),{})
        module,_=target.pure_functions(b'def validate():\n return dict(actual_ERP_cases=0)\n',
            'LABELLED_SYNTHETIC_SELECTOR_CONTROL',('validate',),{})
        self.assertEqual(module.validate(),dict(actual_ERP_cases=0))

    def test_exact_public_afui56_tree_and_all_pure_functions_import_no_erp_runtime(self):
        before={n for n in sys.modules if n.startswith(('cp6_','cp7_','psycopg'))}
        with GitBytes(ROOT,target.PREPARED_HEAD,target.PREPARED_TREE)as g:
            value=target.source(g)
        self.assertEqual(value['source_pins'],56);self.assertEqual(value['own_paths'],88)
        self.assertEqual(sum(len(v['functions'])for v in value['pure_report_functions']['exact_pure_sources'].values()),16)
        self.assertEqual({n for n in sys.modules if n.startswith(('cp6_','cp7_','psycopg'))},before)
        self.assertEqual(value['actual_case_credit'],0);PROOFS['source']=value

    def test_root_selected_artifact_validator_reads_only_pinned_original_bytes(self):
        with GitBytes(ROOT,target.PREPARED_HEAD,target.PREPARED_TREE)as g:
            gate,proof=target.report_validator(g,None)
        raw=b'{"labelled_synthetic_raw_original":true}\n';packed=gzip.compress(raw,mtime=0)
        reference=dict(name='AFUI_LABELLED_MODEL.json.gz',bytes=len(raw),sha256=sha256(raw).hexdigest(),
            gzip_bytes=len(packed),gzip_sha256=sha256(packed).hexdigest())
        with TemporaryDirectory(prefix='root-afui15-pure-original-control-')as directory:
            directory=Path(directory);(directory/reference['name']).write_bytes(packed)
            self.assertEqual(gate.artifact(directory,reference),raw)
            bad=copy.deepcopy(reference);bad['sha256']='0'*64
            with self.assertRaises(ValueError):gate.artifact(directory,bad)
            bad=copy.deepcopy(reference);bad['name']='../AFUI_LABELLED_MODEL.json.gz'
            with self.assertRaises(ValueError):gate.artifact(directory,bad)
        self.assertEqual(proof['actual_ERP_imports'],0)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--tests',nargs='+')
    args=parser.parse_args();ROOT=args.source
    names=args.tests or unittest.defaultTestLoader.getTestCaseNames(Afui15RootPreparationControls)
    if not names or any(n not in unittest.defaultTestLoader.getTestCaseNames(Afui15RootPreparationControls)for n in names):
        raise ValueError('ROOT_AFUI15_EXACT_PREPARATION_CONTROL_NAMES_REQUIRED')
    suite=unittest.TestSuite(Afui15RootPreparationControls(n)for n in names)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    value=dict(status='ROOT_AFUI15_SOURCE_PURE_SELECTION_AND_ORIGINAL_CONTROLS_PASS'if result.wasSuccessful()else'INCOMPLETE',
        unique_new_controls=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        source=PROOFS.get('source'),all_actual_bindings_None=True,actual_ERP_imports=0,actual_SQL_executed=0,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_cases=0,actual_browser_cases=0,
        production_go=False,independent_acceptance=False)
    args.output.write_text(json.dumps(value,indent=2)+'\n')
    if not result.wasSuccessful():raise SystemExit(1)
