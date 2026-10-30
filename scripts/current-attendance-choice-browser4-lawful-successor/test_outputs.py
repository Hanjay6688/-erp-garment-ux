"""Whole source-caller controls and real build/old-metadata replay, never DB/Auth.

Temporary roots hardlink source bytes read-only. Git object reads are forwarded to
the exact real repository; only the observed untracked list is an explicit double.
Fake evidence remains in temporary roots and is never retained as actual proof.
"""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import base64
import gzip
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT/'scripts/current-attendance-choice-browser4-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


class GeneratedOutputControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # CI has npm ci already. Local preparation reuses its earlier actual build.
        if not (ROOT/'cp6-ui-build/index.html').is_file():
            if not (ROOT/'node_modules').is_dir():raise RuntimeError('LOCAL_BUILD_REPLAY_REQUIRES_EXISTING_LOCKED_DEPENDENCIES')
            part=lambda value:base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
            key=part({'alg':'none'})+'.'+part({'role':'anon','ref':'local','source_only_build_fixture':True})+'.BUILD_ONLY_NOT_AUTHENTICATION'
            env={name:value for name,value in os.environ.items()if not name.startswith(('VITE_','SUPABASE_','PG','CP6_','CP7_','AUDITOR_'))}
            env.update(VITE_ERP_RUNTIME_MODE='DISPOSABLE_TEST',VITE_DISPOSABLE_API_PORT='54399',
                VITE_SUPABASE_URL='http://127.0.0.1:54399',VITE_SUPABASE_ANON_KEY=key)
            result=subprocess.run(['npm','run','build:cp6-disposable'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            if result.returncode:raise RuntimeError('ACTUAL_COMPILER_REPLAY_FAILED_NOT_AUTH_OR_BROWSER:'+result.stdout.decode()[-2500:])
        cls.build_files={str(path.relative_to(ROOT)):path for path in(ROOT/'cp6-ui-build').rglob('*')if path.is_file()}
        if not cls.build_files:raise RuntimeError('ACTUAL_NORMAL_APP_COMPILER_REPLAY_REQUIRED')

    def setUp(self):
        directory=ROOT.parent/'evidence-private/s03-browser4-preparation';directory.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix='whole-caller-output-control-',dir=directory)
        self.root=Path(self.temporary.name);self.here=self.root/HERE.relative_to(ROOT)
        declaration=json.loads((HERE/'SOURCE.json').read_bytes())
        for name in [*(row['path']for row in declaration['files']),str((HERE/'SOURCE.json').relative_to(ROOT))]:
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True)
            os.link(ROOT/name,target)  # No EXDEV fallback, source copy, chmod or writes.
        self.output=load('s03_output_control_adapter',self.here/'output_admission.py')
        self.guard=load('s03_output_control_whole_guard',self.here/'source_guard.py')
        self.real_git=subprocess.check_output

    def tearDown(self):self.temporary.cleanup()

    def put(self,name,raw):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists()or path.is_symlink():path.unlink()
        path.write_bytes(raw);return path

    def whole(self,names):
        def observed_untracked_double(args,**kwargs):
            if Path(args[0]).name=='git' and args[1:3]==['-C',str(self.root)]:
                if args[-3:]==['ls-files','--others','--exclude-standard']:
                    return ''.join(name+'\n'for name in sorted(names))
                args=[args[0],args[1],str(ROOT),*args[3:]]
            return self.real_git(args,**kwargs)
        with patch.object(self.guard.subprocess,'check_output',side_effect=observed_untracked_double):
            return self.guard.check()

    def copy_build(self):
        for name,path in self.build_files.items():
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);os.link(path,target)
        return set(self.build_files)

    def test_exact_public_validators_and_only_declared_contract_changes(self):
        folder=HERE/'inherited-output-validation';receipt=json.loads((folder/'DERIVATION.json').read_bytes())
        old='.github/workflows/cp7-s03-choice-reader-native14.yml';new='.github/workflows/cp7-current-s03-browser4-lawful.yml'
        for name in('generated_receipts.py','generated_later.py'):
            raw=(folder/name).read_bytes();self.assertEqual(sha256(raw).hexdigest(),receipt['parent_files'][name]['sha256'])
        for name in('GENERATED_RECEIPTS.json','LATER_GENERATED_RECEIPTS.json'):
            parent=json.loads((folder/'parent'/name).read_bytes());current=json.loads((folder/name).read_bytes())
            self.assertEqual(len(parent['producer_files']),len(current['producer_files']))
            self.assertNotIn(old,current['producer_files']);self.assertIn(new,current['producer_files'])
            current['producer_files'][old]=parent['producer_files'][old];current['producer_files'].pop(new)
            if name=='LATER_GENERATED_RECEIPTS.json':current['package_workflow_name']=parent['package_workflow_name']
            self.assertEqual(current,parent)

    def test_whole_caller_replays_actual_old101_outputs_and_actual_normal_App_build(self):
        names=self.copy_build();index=json.loads((FROZEN/'retained-generated-source-replay/INDEX.json').read_bytes())
        self.assertEqual(len(index['files']),101)
        for row in index['files']:
            packed=(FROZEN/row['retained']).read_bytes();raw=gzip.decompress(packed)
            self.assertEqual(sha256(packed).hexdigest(),row['gzip_sha256']);self.assertEqual(sha256(raw).hexdigest(),row['raw_sha256'])
            self.put(row['output'],raw);names.add(row['output'])
        result=self.whole(names);proof=result['generated_output_provenance_only']
        self.assertEqual(result['status'],'SOURCE_PASS');self.assertEqual(proof['normal_App_build_files'],len(self.build_files))
        self.assertEqual(proof['P0']['files'],101);self.assertIs(proof['source_authority'],False)
        self.assertIsNone(result['config']['accepted_originals']) if result['config']['actual_execution_authorized']is False else None

    def test_whole_caller_rejects_unknown_code_unknown_JSON_and_bad_build_index(self):
        for name in('cp6-proof/t3/unknown.py','cp6-proof/t3/unknown.json','cp6-ui-build/assets/unknown.json'):
            self.put(name,b'{}')
            with self.subTest(name=name),self.assertRaises(ValueError):self.whole({name})
        names=self.copy_build();self.put('cp6-ui-build/index.html',b'<script type="module" src="https://unrelated.invalid/app.js"></script>')
        with self.assertRaisesRegex(ValueError,'NORMAL_APP_INDEX_CHANGED'):self.whole(names)

    def test_whole_caller_rejects_evidence_leaf_and_ancestor_symlinks(self):
        name='cp6-proof/t3/S03_B4_DESKTOP_'+'a'*32+'_FIRST_FAILURE.json'
        target=self.put('outside-data.json',b'{}');path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'GENERATED_SYMLINK'):self.whole({name})
        path.unlink();(self.root/'cp6-proof/t3').rmdir();(self.root/'cp6-proof').rmdir()
        external=self.root/'outside-directory';external.mkdir();(external/'t3').mkdir();(external/'t3'/Path(name).name).write_bytes(b'{}')
        (self.root/'cp6-proof').symlink_to(external,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'GENERATED_SYMLINK'):self.whole({name})

    def test_whole_caller_rejects_missing_or_changed_fixed_build_producer(self):
        names=self.copy_build();path=self.root/'scripts/scan-client-artifacts.mjs';path.unlink()
        with self.assertRaises(ValueError):self.whole(names)
        self.put('scripts/scan-client-artifacts.mjs',b'// explicit local changed producer double')
        with self.assertRaises(ValueError):self.whole(names)

    def test_whole_caller_rejects_hash_looking_extra_script_and_missing_actual_chunk(self):
        names=self.copy_build();extra='cp6-ui-build/assets/unknown-AAAAAAAA.js'
        self.put(extra,b'export const unauthorized=true;')
        with self.assertRaisesRegex(ValueError,'UNREFERENCED_BUILD_LEAF'):self.whole(names|{extra})
        entry=next(name for name in names if name.startswith('cp6-ui-build/assets/index-')and name.endswith('.js'))
        (self.root/entry).unlink()
        with self.assertRaisesRegex(ValueError,'BUILD_REFERENCE_CHANGED'):self.whole(names-{entry})

    def test_whole_caller_rejects_extra_module_tag_or_hidden_script_attribute(self):
        names=self.copy_build();original=(self.root/'cp6-ui-build/index.html').read_bytes()
        module=next(line for line in original.splitlines()if b'<script type="module"'in line)
        for raw in(original.replace(b'</head>',module+b'\n</head>'),original.replace(b'<script type="module"',b'<script onload="window.hidden=true" type="module"')):
            self.put('cp6-ui-build/index.html',raw)
            with self.assertRaises(ValueError):self.whole(names)

    def test_whole_caller_rejects_traversal_and_changed_inherited_producer(self):
        with self.assertRaises(ValueError):self.whole({'cp6-proof/t3/../unknown.json'})
        contract=json.loads((HERE/'inherited-output-validation/GENERATED_RECEIPTS.json').read_bytes())
        producer=next(name for name in contract['producer_files']if name.endswith('.py'))
        self.put(producer,b'# changed local producer double\n')
        with self.assertRaises(ValueError):self.whole(set())

    def test_whole_caller_accepts_closed_snapshot_double_but_never_adds_case_credit(self):
        name='cp6-proof/t3/S03_B4_DESKTOP_'+'A'*32+'_001_INITIAL_FULL_STATE.json.gz'
        value={'all22':{str(i):{}for i in range(22)},'all_rows':{'explicit_local_double':[]},'data_and_all_sequences':{'sequence:explicit_local_double':[1,True]}}
        self.put(name,gzip.compress(json.dumps(value).encode(),mtime=0));result=self.whole({name})
        self.assertEqual(result['generated_output_provenance_only']['own_evidence_files'],1)
        self.assertEqual(result['fresh_Native_Auth_HTTP_race_browser_cases'],0)
        value['unknown_source_authority']=True;self.put(name,gzip.compress(json.dumps(value).encode(),mtime=0))
        with self.assertRaisesRegex(ValueError,'FULL_CENSUS_SHAPE'):self.whole({name})


if __name__=='__main__':unittest.main(verbosity=2)
