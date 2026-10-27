from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import io,json,unittest
import disposable_start as startup


class RetainedDisposableStartup(unittest.TestCase):
    def exercise(self,failures):
        calls=[];delays=[]
        def run(command,*,env,stdout,stderr,check):
            self.assertFalse(check)
            if command==startup.STOP:
                stdout.write(b'disposable stop\n');return SimpleNamespace(returncode=0)
            self.assertEqual(command,startup.START)
            calls.append(env.get('SUPABASE_INTERNAL_IMAGE_REGISTRY'))
            at=len(calls)
            message=failures[at-1]if at<=len(failures)else b'started\n'
            stdout.write(message)
            return SimpleNamespace(returncode=1 if at<=len(failures)else 0)
        with TemporaryDirectory()as folder,redirect_stdout(io.StringIO()):
            directory=Path(folder)/'proof'
            try:result=startup.start(directory,run=run,pause=delays.append,
                environment={'SUPABASE_INTERNAL_IMAGE_REGISTRY':'old-registry'})
            except RuntimeError as error:
                self.assertEqual(str(error),'DISPOSABLE_STARTUP_EXHAUSTED_FOUR_RETAINED_ATTEMPTS')
                result=json.loads((directory/'STARTUP_ATTEMPTS.json').read_bytes())
            self.assertEqual(result,json.loads((directory/'STARTUP_ATTEMPTS.json').read_bytes()))
            for at,message in enumerate(failures[:len(calls)],1):
                self.assertEqual((directory/f'attempt-{at}-start.log').read_bytes(),message)
            return result,calls,delays

    def test_successful_start_does_not_repeat(self):
        result,calls,delays=self.exercise([])
        self.assertEqual((result['status'],calls,delays),('PASS',[None],[]))

    def test_transient_ghcr_then_ecr_quota_returns_to_ghcr_with_first_logs(self):
        result,calls,delays=self.exercise([b'toomanyrequests\n',b'Data limit exceeded\n'])
        self.assertEqual((result['status'],calls,delays),('PASS',[None,'public.ecr.aws',None],[60,120]))

    def test_four_failures_are_bounded_and_all_retained(self):
        result,calls,delays=self.exercise([b'first\n',b'second\n',b'third\n',b'fourth\n'])
        self.assertEqual(result['status'],'INCOMPLETE')
        self.assertEqual(calls,[None,'public.ecr.aws',None,None])
        self.assertEqual(delays,[60,120,180])
        self.assertEqual(len(result['attempts']),4)


if __name__=='__main__':unittest.main()
