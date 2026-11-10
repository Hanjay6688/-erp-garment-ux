"""Cold-process observer regression; zero ERP/Native/browser case credit."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock
import ast,unittest
from cp7_accessory_nonpayable import access_cases, browser_fixture, complete_original_io

ROOT=Path(__file__).resolve().parents[2]


class BrowserObserverControls(unittest.TestCase):
    def observer_inputs(self, directory):
        _, _, state, _, _, _ = self.fixtures()
        originals, environ = {}, {}
        for key, name, variable in (
                ('original', 'AFUI_BROWSER_SETTINGS_STATE.json', 'AFUI_BROWSER_STATE_SHA256'),
                ('cache', 'AFUI_BROWSER_SETTINGS_STATE_CACHE.json', 'AFUI_BROWSER_STATE_CACHE_SHA256')):
            path = directory / name
            path.write_bytes(key.encode())
            originals[key] = dict(name=name, **complete_original_io.pin(path))
            environ[variable] = originals[key]['sha256']
        return dict(observer_catalogue=dict(**state, **originals)), environ

    def test_observer_uses_complete_catalogue_and_verifies_both_state_originals(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            prepared, environ = self.observer_inputs(directory)
            catalogue = prepared['observer_catalogue']['after']
            self.assertEqual(browser_fixture.observer_state(prepared, directory, environ), dict(after=catalogue))
            for key in ('original', 'cache'):
                with self.subTest(key=key):
                    path = directory / prepared['observer_catalogue'][key]['name']
                    path.write_bytes(b'changed')
                    with self.assertRaisesRegex(ValueError, 'EXACT_BOUND_STATE_ORIGINAL_REQUIRED:' + key):
                        browser_fixture.observer_state(prepared, directory, environ)
                    path.write_bytes(key.encode())

    def test_observer_refuses_partial_catalogue_and_wrong_origin_binding(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            prepared, environ = self.observer_inputs(directory)
            partial = deepcopy(prepared)
            del partial['observer_catalogue']['after']['database_authority']
            with self.assertRaisesRegex(ValueError, 'COMPLETE_OBSERVER_CATALOGUE_REQUIRED'):
                browser_fixture.observer_state(partial, directory, environ)
            environ['AFUI_BROWSER_STATE_SHA256'] = 'wrong source'
            with self.assertRaisesRegex(ValueError, 'EXACT_BOUND_STATE_ORIGINAL_REQUIRED:original'):
                browser_fixture.observer_state(prepared, directory, environ)

    def fixtures(self):
        groups={name:{}for name in('schemas','relations','columns','constraints','indexes','triggers','functions',
            'aggregates','types','enums','sequences','policies','extensions','roles','memberships','event_triggers',
            'rules','inheritance','default_privileges','database_authority','type_implementation','sequence_ownership')}
        groups['schemas']={'erp':['postgres',[]]}
        data={'erp.observer_control':['complete-fingerprint',1],'sequence:erp.observer_control_seq':[3,True]}
        catalog=SimpleNamespace(_catalog_rows=Mock(return_value=groups),_data=Mock(return_value=data))
        modules=SimpleNamespace(bc=SimpleNamespace(api=SimpleNamespace(admin=Mock())),
            product=SimpleNamespace(runtime=lambda:(catalog,)),
            control=SimpleNamespace(STATE=None,product_catalog=Mock(side_effect=AssertionError('Legacy process state cannot be inherited'))))
        calls=[]
        class Cursor:
            def execute(self,query):
                calls.append(query)
                if query=="set local timezone='UTC'":return None
                if query.startswith('select to_jsonb(v)from cp7_accessory_nonpayable.category_versions_v1'):
                    return SimpleNamespace(fetchall=lambda:[({'id':'date-original'},)])
                if query.startswith('select to_jsonb(r)from cp7_accessory_nonpayable.date_requests_v1'):
                    return SimpleNamespace(fetchall=lambda:[({'request_id':'request-original'},)])
                raise AssertionError('Unreviewed observer query: '+query)
        return Cursor(),modules,dict(after=deepcopy(groups)),groups,data,calls

    def test_legacy_observer_fails_with_genuine_uninitialized_module_state(self):
        source=(ROOT/'scripts/ow04-payment-source-qualification/source_probe.py').read_bytes()
        tree=ast.parse(source);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='product_catalog')
        state=next(n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='STATE'for t in n.targets))
        self.assertIsNone(ast.literal_eval(state.value))
        @contextmanager
        def catalog(cur):yield
        api=SimpleNamespace(admin=Mock())
        namespace=dict(contextmanager=contextmanager,STATE=None,business=SimpleNamespace(native=SimpleNamespace(b=SimpleNamespace(api=api))),
            product=SimpleNamespace(catalog=SimpleNamespace(_catalog=catalog,QUERIES={'schemas':'exact-original-schema-query'})))
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<exact-original-Native-catalog-context>','exec'),namespace)
        cur=SimpleNamespace(execute=lambda query:SimpleNamespace(fetchall=lambda:[('erp',['postgres',[]])]))
        with self.assertRaisesRegex(TypeError,'NoneType'):
            with namespace['product_catalog'](cur):pass

    def test_cold_browser_reader_keeps_complete_catalog_rows_sequences_without_overlay(self):
        cur,modules,state,groups,data,calls=self.fixtures()
        result=access_cases.capture_browser_observed(cur,modules,state)
        self.assertEqual(result['catalog'],groups);self.assertEqual(result['data_and_all_sequences'],data)
        self.assertEqual(len(result['catalog']),22)
        self.assertEqual(result['date_versions'],[{'id':'date-original'}])
        self.assertEqual(result['date_requests'],[{'request_id':'request-original'}])
        modules.control.product_catalog.assert_not_called();self.assertIsNone(modules.control.STATE)
        self.assertFalse(any('grant'in q.lower()or'revoke'in q.lower()for q in calls))

    def test_unexpected_native_schema_grant_refuses_before_data_read(self):
        cur,modules,state,groups,data,calls=self.fixtures()
        groups['schemas']['erp'][1].append(['authenticated','postgres','USAGE',False])
        with self.assertRaisesRegex(ValueError,'EXACT_INSTALLED_ALL22_REQUIRED'):
            access_cases.capture_browser_observed(cur,modules,state)
        modules.product.runtime()[0]._data.assert_not_called()

    def test_missing_or_changed_catalog_member_is_not_projected_away(self):
        for missing in(True,False):
            cur,modules,state,groups,data,calls=self.fixtures()
            if missing:groups.pop('database_authority')
            else:groups['functions']['unexpected-private-writer']=['changed']
            with self.assertRaisesRegex(ValueError,'EXACT_INSTALLED_ALL22_REQUIRED'):
                access_cases.capture_browser_observed(cur,modules,state)
            modules.product.runtime()[0]._data.assert_not_called()


if __name__=='__main__':unittest.main()
