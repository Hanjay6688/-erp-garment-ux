"""Cold-copy prerequisites only; no ERP connection or financial case credit."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import ast,importlib.util,unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mandor_inert_native_fixture',HERE/'native_fixture.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


class CommittedFoundationControls(unittest.TestCase):
    def context(self,count,rows,after_seed=None):
        state={'rows':rows};seen=[]
        class Cursor:
            def execute(cursor,query,args=None):
                seen.append((query,args))
                if query=='select count(*) from erp.app_users':
                    return SimpleNamespace(fetchone=lambda:(count,))
                if query.startswith('select u.is_active,r.role_code,r.is_active'):
                    self.assertEqual(args,('original-owner',))
                    return SimpleNamespace(fetchall=lambda:state['rows'])
                raise AssertionError('Unexpected prerequisite SQL: '+query)
        def seed(cur):state['rows']=after_seed if after_seed is not None else[(True,'OWNER',True)]
        api=SimpleNamespace(seed=Mock(side_effect=seed),base=SimpleNamespace(OPERATOR_AUTH='original-owner'))
        native=fixture.Native.__new__(fixture.Native)
        native.admin=Mock();native.modules=SimpleNamespace(bc=SimpleNamespace(api=api))
        return native,Cursor(),api,seen

    def test_new_connection_receives_original_rolled_back_foundation(self):
        native,cur,api,seen=self.context(0,[])
        result=native.committed_foundation(cur)
        api.seed.assert_called_once_with(cur)
        self.assertEqual(native.admin.call_count,2)
        self.assertTrue(result['unchanged_original_foundation_loaded'])
        self.assertFalse(result['existing_actor_or_role_promoted'])
        self.assertFalse(result['product_permission_grants_added'])
        self.assertEqual(result['actual_case_credit'],0)
        self.assertEqual(len(seen),2)

    def test_existing_owner_is_reused_without_seed(self):
        native,cur,api,_=self.context(2,[(True,'OWNER',True)])
        self.assertFalse(native.committed_foundation(cur)['unchanged_original_foundation_loaded'])
        api.seed.assert_not_called()

    def test_missing_inactive_wrong_or_duplicate_existing_actor_never_promoted(self):
        for rows in([],[(False,'OWNER',True)],[(True,'OWNER',False)],
                [(True,'ADMIN',True)],[(True,'OWNER',True),(True,'OWNER',True)]):
            with self.subTest(rows=rows):
                native,cur,api,_=self.context(1,rows)
                with self.assertRaisesRegex(ValueError,'ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION'):
                    native.committed_foundation(cur)
                api.seed.assert_not_called()

    def test_bad_empty_copy_seed_is_refused(self):
        native,cur,api,_=self.context(0,[],after_seed=[])
        with self.assertRaisesRegex(ValueError,'ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION'):
            native.committed_foundation(cur)
        api.seed.assert_called_once_with(cur)

    def test_invalid_count_is_refused_before_seed(self):
        for count in(-1,False,'0',None):
            with self.subTest(count=count):
                native,cur,api,_=self.context(count,[])
                with self.assertRaisesRegex(ValueError,'EXACT_FIXTURE_USER_COUNT_REQUIRED'):
                    native.committed_foundation(cur)
                api.seed.assert_not_called()

    def test_owning_connection_prepares_before_business_and_keeps_zero_credit(self):
        tree=ast.parse((HERE/'component.py').read_bytes())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        calls=[n for n in ast.walk(function)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)]
        prepare=[n for n in calls if n.func.attr=='committed_foundation']
        business=[n for n in calls if n.func.attr=='selected_week']
        self.assertEqual(len(prepare),1);self.assertEqual(len(business),1)
        self.assertLess(prepare[0].lineno,business[0].lineno)
        self.assertIn('native_case_credit=0,original_foundation=foundation',
            (HERE/'component.py').read_text())
        text=(HERE/'component.py').read_text()
        self.assertLess(text.index("cursor.execute('grant usage on schema erp to authenticated')"),
            text.index('witness=cases.selected_week'))
        self.assertLess(text.index('access_fixture=access_cases.prepare'),
            text.index("cursor.execute('revoke usage on schema erp from authenticated')"))
        self.assertLess(text.index("cursor.execute('revoke usage on schema erp from authenticated')"),
            text.index('product.verify(cursor,state);used.commit()'))


if __name__=='__main__':unittest.main()
