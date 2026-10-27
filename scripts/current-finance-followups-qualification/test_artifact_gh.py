from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import io,json,unittest
import artifact_gh

ARGS=['api','repos/Hanjay6688/-erp-garment-ux/actions/artifacts/12472787961/zip']


class ArtifactDownloadBoundary(unittest.TestCase):
    def exercise(self,responses):
        directory=TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name);calls=[];delays=[];out=io.BytesIO();err=io.BytesIO()
        def execute(command,stdout,stderr,check):
            code,data,error=responses[len(calls)];calls.append(command)
            self.assertFalse(check);stdout.write(data);stderr.write(error)
            return SimpleNamespace(returncode=code)
        code=artifact_gh.download(ARGS,'/real/gh',root,out,err,execute,delays.append)
        records=sorted((json.loads(p.read_bytes()) for p in root.glob('*.json')),key=lambda d:d['attempt'])
        return code,out.getvalue(),err.getvalue(),calls,delays,records,root

    def test_partial_failed_zip_never_reaches_exact_original_reader(self):
        code,out,_,calls,delays,records,root=self.exercise([
            (1,b'partial-first-zip',b'gh: HTTP 503\n'),(0,b'complete-exact-zip',b'')])
        self.assertEqual((code,out,len(calls),delays),(0,b'complete-exact-zip',2,[2]))
        self.assertEqual(len(list(root.glob('*.stdout.txt'))),1)
        self.assertEqual(next(root.glob('*.stdout.txt')).read_bytes(),b'partial-first-zip')
        self.assertEqual([r['retry'] for r in records],[True,False])

    def test_permission_and_not_found_failures_are_not_retried(self):
        for status in (401,403,404,429):
            with self.subTest(status=status):
                code,out,_,calls,delays,_,_=self.exercise([(1,b'',f'gh: HTTP {status}\n'.encode())])
                self.assertEqual((code,out,len(calls),delays),(1,b'',1,[]))

    def test_transport_errors_without_explicit_transient_http_status_stop(self):
        code,out,_,calls,delays,_,_=self.exercise([(1,b'',b'connection reset\n')])
        self.assertEqual((code,out,len(calls),delays),(1,b'',1,[]))

    def test_transient_failures_are_bounded_and_all_first_bytes_retained(self):
        responses=[(1,str(i).encode(),f'gh: HTTP {status}\n'.encode()) for i,status in enumerate((502,503,504))]
        code,out,_,calls,delays,records,root=self.exercise(responses)
        self.assertEqual((code,out,len(calls),delays),(1,b'',3,[2,5]))
        self.assertEqual([r['http_status']for r in records],[502,503,504])
        self.assertFalse(records[-1]['retry'])
        self.assertEqual(len(list(root.glob('*.stdout.txt'))),3)

    def test_first_success_forwards_exact_bytes_once(self):
        code,out,_,calls,delays,records,root=self.exercise([(0,b'PK\x00\xffexact',b'')])
        self.assertEqual((code,out,len(calls),delays),(0,b'PK\x00\xffexact',1,[]))
        self.assertEqual(len(records),1);self.assertEqual(list(root.glob('*.txt')),[])

    def test_only_exact_repository_artifact_get_can_retry(self):
        self.assertTrue(artifact_gh.eligible(ARGS))
        for args in (ARGS+['--method','DELETE'],['api','repos/other/repo/actions/artifacts/1/zip'],
                     ['api','repos/Hanjay6688/-erp-garment-ux/actions/runs/1'],['auth','status']):
            self.assertFalse(artifact_gh.eligible(args))
