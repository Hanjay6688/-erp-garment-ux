"""Source and actual disposable Git worktree checks; no ERP/GitHub access."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast,json,subprocess,unittest
import admission,fetch_parent,materialize_parent,qualification


class ParentPreparation(unittest.TestCase):
    def test_closed_parent_refuses_before_fetch_derivation_or_git(self):
        self.assertIsNone(admission.PARENT_ROOT_PIN);self.assertIsNone(admission.RUNTIME_ENTRY)
        with (patch.object(fetch_parent,'derive',side_effect=AssertionError('premature derivation')),
            patch.object(materialize_parent,'git',side_effect=AssertionError('premature Git'))):
            for fn in(fetch_parent.main,materialize_parent.materialize):
                with self.assertRaisesRegex(ValueError,'MANDOR_NATIVE_ACTUAL_AFUI15_ROOT_ACCEPTANCE_AND_OWNING_CALLER_PENDING'):fn()

    def test_fetch_source_preserves_original_API_and_hash_routines(self):
        text,proof=fetch_parent.derive()
        old=fetch_parent.load('exact_old_fetch_source',fetch_parent.ROOT/'scripts/cp7_accessory_nonpayable/fetch_parent.py').derive()[0]
        functions=lambda source:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
        a,b=functions(old),functions(text)
        for name in('load','api','digest'):self.assertEqual(a[name],b[name])
        self.assertTrue(proof['original_full_fetcher_recovered']);self.assertEqual(proof['actual_GitHub_GETs'],0)

    def test_worktree_exact_creation_reuse_and_changed_file_refusal(self):
        with TemporaryDirectory(prefix='mandor-parent-prerequisite-')as directory:
            root=Path(directory)/'candidate';root.mkdir();(root/'input.txt').write_text('accepted source\n')
            for args in [('init','--quiet'),('add','input.txt'),('-c','user.name=ERP prerequisite control',
                '-c','user.email=prerequisite@example.invalid','commit','--quiet','-m','Modeled accepted parent')]:
                subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True)
            head=materialize_parent.git(root,'rev-parse','HEAD').decode().strip()
            tree=materialize_parent.git(root,'rev-parse','HEAD^{tree}').decode().strip()
            frozen=root.parent/'qualified-afui-parent';receipt=dict(head=head,tree=tree)
            # Only Git behavior is under test; acceptance remains explicitly modeled.
            with patch.multiple(materialize_parent,ROOT=root,FROZEN=frozen),patch.multiple(admission,PARENT_HEAD=head,PARENT_TREE=tree),\
                    patch.object(qualification,'actual_parent',return_value=(b'MODELED_ACCEPTANCE_FOR_GIT_ONLY',receipt)):
                self.assertTrue(materialize_parent.materialize()['created'])
                self.assertFalse(materialize_parent.materialize()['created'])
                (frozen/'input.txt').write_text('unreviewed change\n')
                with self.assertRaisesRegex(ValueError,'MANDOR_PARENT_EXISTING_WORKTREE_CHANGED'):materialize_parent.materialize()
                self.assertEqual((frozen/'input.txt').read_text(),'unreviewed change\n')
                (frozen/'input.txt').write_text('accepted source\n')
                with patch.object(admission,'PARENT_TREE','0'*40):
                    with self.assertRaisesRegex(ValueError,'MANDOR_PARENT_EXACT_TREE_MISMATCH'):materialize_parent.materialize()


if __name__=='__main__':unittest.main()
