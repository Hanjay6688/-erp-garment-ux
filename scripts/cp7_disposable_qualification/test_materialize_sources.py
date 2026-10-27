from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,unittest
import materialize_sources as sources


class ExactFrozenWorktrees(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.repo=Path(self.folder.name)/'auditor';self.repo.mkdir()
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.command('config','user.email','fixture@example.invalid')
        self.command('config','user.name','Source fixture')
        (self.repo/'source.txt').write_text('first\n');self.command('add','source.txt');self.command('commit','-qm','first')
        self.first=sources.git(self.repo,'rev-parse','HEAD')
        (self.repo/'source.txt').write_text('second\n');self.command('commit','-qam','second')
        self.second=sources.git(self.repo,'rev-parse','HEAD')

    def command(self,*args):return subprocess.run(['git','-C',str(self.repo),*args],check=True,capture_output=True)

    def test_two_distinct_exact_heads_share_history_without_altering_auditor(self):
        proof=sources.materialize(self.repo,{'writer':self.first,'frozen':self.second})
        self.assertEqual(proof['source_worktree_count'],2)
        self.assertEqual((self.repo.parent/'writer/source.txt').read_text(),'first\n')
        self.assertEqual((self.repo.parent/'frozen/source.txt').read_text(),'second\n')
        self.assertEqual(sources.git(self.repo,'rev-parse','HEAD'),self.second)
        common=Path(sources.git(self.repo,'rev-parse','--git-common-dir'))
        for name in ('writer','frozen'):
            path=self.repo.parent/name
            self.assertTrue((path/'.git').is_file())
            self.assertEqual(Path(sources.git(path,'rev-parse','--git-common-dir')).resolve(),(self.repo/common).resolve())

    def test_missing_later_commit_refuses_before_creating_any_source(self):
        with self.assertRaises(subprocess.CalledProcessError):
            sources.materialize(self.repo,{'writer':self.first,'frozen':'0'*40})
        self.assertFalse((self.repo.parent/'writer').exists())

    def test_mutable_refs_and_outside_directories_are_refused(self):
        for value in ({'writer':'HEAD'},{'../outside':self.first},{'auditor':self.first}):
            with self.subTest(value=value),self.assertRaises(ValueError):sources.materialize(self.repo,value)
        self.assertFalse((self.repo.parent/'writer').exists())


if __name__=='__main__':unittest.main()
