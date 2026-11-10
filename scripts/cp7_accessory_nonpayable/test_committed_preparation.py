"""Cold-copy actor prerequisite controls, never actual ERP case evidence."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import ast,unittest
from cp7_accessory_nonpayable import qualification_component as component


class CommittedPreparationControls(unittest.TestCase):
    def exercise(self,count,actors,*,after_seed=None):
        seen=[];state={'actors':actors};identity='ordinary-existing-fixture-owner'
        class Cursor:
            def execute(cursor,query,args=None):
                seen.append((query,args))
                if query=='select count(*) from erp.app_users':
                    return SimpleNamespace(fetchone=lambda:(count,))
                if query.startswith('select u.is_active,r.role_code,r.is_active'):
                    self.assertEqual(args,(identity,))
                    return SimpleNamespace(fetchall=lambda:state['actors'])
                raise AssertionError('Unexpected prerequisite SQL: '+query)
        def seed(cur):state['actors']=after_seed if after_seed is not None else[(True,'OWNER',True)]
        bc=SimpleNamespace(api=SimpleNamespace(admin=Mock(),seed=Mock(side_effect=seed),
            base=SimpleNamespace(OPERATOR_AUTH=identity)))
        return Cursor(),bc,seen

    def test_fresh_connection_cannot_inherit_rolled_back_strict_group_owner(self):
        cursor,bc,seen=self.exercise(0,[])
        value=component.committed_identity(cursor,bc)
        bc.api.seed.assert_called_once_with(cursor)
        self.assertTrue(value['unchanged_original_foundation_loaded'])
        self.assertFalse(value['existing_actor_or_role_promoted'])
        self.assertFalse(value['product_permission_grants_added'])
        self.assertEqual(value['actual_case_credit'],0)
        self.assertEqual(len(seen),2)

    def test_existing_valid_owner_reuses_rows_without_any_seed(self):
        cursor,bc,_=self.exercise(3,[(True,'OWNER',True)])
        value=component.committed_identity(cursor,bc)
        bc.api.seed.assert_not_called()
        self.assertFalse(value['unchanged_original_foundation_loaded'])

    def test_missing_inactive_admin_or_duplicate_actor_never_promotes_existing_rows(self):
        for actors in ([],[(False,'OWNER',True)],[(True,'OWNER',False)],
                [(True,'ADMIN',True)],[(True,'OWNER',True),(True,'OWNER',True)]):
            with self.subTest(actors=actors):
                cursor,bc,_=self.exercise(1,actors)
                with self.assertRaisesRegex(ValueError,'ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION'):
                    component.committed_identity(cursor,bc)
                bc.api.seed.assert_not_called()

    def test_bad_foundation_is_not_silently_admitted(self):
        cursor,bc,_=self.exercise(0,[],after_seed=[])
        with self.assertRaisesRegex(ValueError,'ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION'):
            component.committed_identity(cursor,bc)
        bc.api.seed.assert_called_once_with(cursor)

    def test_owning_committed_path_establishes_identity_before_domain_fixture(self):
        tree=ast.parse(Path(component.__file__).read_bytes())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='committed_prerequisite')
        calls=[n for n in ast.walk(function)if isinstance(n,ast.Call)]
        setup=[n for n in calls if isinstance(n.func,ast.Name)and n.func.id=='committed_identity']
        physical=[n for n in calls if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)
            and n.func.value.id=='browser_prepare'and n.func.attr=='prepare']
        self.assertEqual(len(setup),1);self.assertEqual(len(physical),1)
        self.assertLess(setup[0].lineno,physical[0].lineno)


if __name__=='__main__':unittest.main()
