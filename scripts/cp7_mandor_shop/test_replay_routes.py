"""Source derivation controls only; actual two-session evidence is pending."""
from pathlib import Path
import importlib.util,json,sys,unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from cp7_mandor_shop import native_dispatch,replay_routes


class ReplayPermissionRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allocation=(HERE/'allocation.sql').read_bytes()
        reference=json.loads((HERE/'NATIVE_SALES_COMMAND_REFERENCE.json').read_bytes())
        cls.facades,_=native_dispatch.derive(reference['functions'])

    def test_both_original_cached_paths_precede_their_fresh_permission_locks(self):
        # The original cached branches lack the guard; no old model result is
        # presented as acceptance of concurrent revocation on these branches.
        for source in(self.allocation.decode(),self.facades):
            branch=source.split(replay_routes.BEFORE)[1].split('return old_.response;',1)[0]
            self.assertNotIn(replay_routes.LOCK,branch)

    def test_exact_two_guards_preserve_complete_originals_and_private_identity(self):
        derived,proof=replay_routes.derive(self.allocation,self.facades)
        self.assertEqual(len(proof['routes']),2)
        for route in proof['routes']:
            text=derived[route['file']]
            branch=text.split(replay_routes.BEFORE)[1].split('return old_.response;',1)[0]
            self.assertIn(replay_routes.GUARDS[route['file']],branch)
            self.assertEqual(text.count(route['after']),1)
            self.assertEqual(replay_routes.pin(text.replace(route['after'],route['before'],1).encode()),route['original'])
            self.assertNotIn('grant ',replay_routes.GUARDS[route['file']])
        self.assertEqual(proof['new_function_identities'],0)
        self.assertEqual(proof['actual_two_session_races'],0)

    def test_unreviewed_allocation_source_refused(self):
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_SOURCE_REQUIRED:allocation.sql'):
            replay_routes.derive(self.allocation+b'\n-- changed',self.facades)

    def test_unreviewed_facade_composition_refused(self):
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_SOURCE_REQUIRED:composed_facades'):
            replay_routes.derive(self.allocation,self.facades+'\n-- changed')


if __name__=='__main__':unittest.main()
