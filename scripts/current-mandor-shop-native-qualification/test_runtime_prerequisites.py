"""New caller protocol controls; the model below is not an ERP database.

Exercise combined missing prerequisites, SQL abort recovery, ordinary identity,
and unprojected census readers without granting any business-case credit.
"""
from copy import deepcopy
from datetime import date,timedelta
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,tempfile,unittest
from unittest.mock import patch
import runtime_prerequisites as prerequisites
import native_fixture,final_gate

HERE=Path(__file__).resolve().parent
TODAY=date(2026,11,4)  # Protocol-model input, never a runtime business date.


class Protocol:
    def __init__(self,directory):
        self.calls=[];self.abort=False;self.actor_error=None;self.after_change=None;self.boundaries=0
        self.day=TODAY;self.identity=['authenticated','authenticated','OWNER']
        self.functions={key:True for key in prerequisites.FUNCTIONS}
        self.permissions={key:True for key in prerequisites.PERMISSIONS}
        self.capabilities=dict(self.functions)
        self.mappings={key:[(True,True)]for key in prerequisites.MAPPINGS}
        self.location=(True,'FG_WAREHOUSE');self.pcs=[('PCS',)];self.period=[(TODAY-timedelta(days=1),)]
        self.census={'actual_all22':{str(i):[]for i in range(22)},
            'full_data_and_sequences':{'MODEL_ONLY_rows':[[9007199254740993,'asal → utuh']],
                'MODEL_ONLY_sequences':[['sample',18,True]]}}
        self.native=native_fixture.Native.__new__(native_fixture.Native)
        self.native.scope='NATIVE9';self.native.observation=0
        self.native.modules=SimpleNamespace(bd=SimpleNamespace(chain=SimpleNamespace(base=SimpleNamespace(LOCATION='model-location'))))
        self.native.admin=self.admin;self.native.boundary=self.boundary
        self.native.sales=SimpleNamespace(auth=SimpleNamespace(actor=self.actor))
        self.directory=directory

    def admin(self,cur):
        if self.abort:raise AssertionError('Aborted actor query must be rolled back before admin')
        self.calls.append('admin')

    def boundary(self,cur):
        self.boundaries+=1;value=deepcopy(self.census)
        if self.boundaries==2 and self.after_change:self.after_change(value)
        return value

    def actor(self,cur,subject):
        assert subject is None,'Must inspect the unchanged original seeded actor'
        self.calls.append('original_actor')
        if self.actor_error:self.abort=True;raise self.actor_error

    def execute(self,query,args=None):
        self.calls.append(query)
        if query.startswith('rollback to savepoint'):self.abort=False;rows=[]
        elif self.abort:raise AssertionError('SQL after aborted actor without rollback')
        elif query.startswith(('savepoint ','release savepoint ')):rows=[]
        elif "statement_timestamp()"in query:rows=[(self.day,)]
        elif 'to_regprocedure' in query:rows=[(self.functions[args[0]],)]
        elif 'accounting_account_mappings' in query:rows=self.mappings[args[0]]
        elif 'from erp.locations' in query:rows=[]if self.location is None else[self.location]
        elif 'from erp.uom_definitions' in query:rows=self.pcs
        elif 'from erp.accounting_period_control' in query:rows=self.period
        elif 'session_user' in query:rows=[tuple(self.identity)]
        elif 'erp.has_permission' in query:rows=[(self.permissions[args[0]],)]
        elif 'has_function_privilege' in query:rows=[(self.capabilities[args[0]],)]
        else:raise AssertionError('Unexpected protocol SQL: '+query)
        return SimpleNamespace(fetchone=lambda:rows[0]if rows else None,fetchall=lambda:rows)

    def check(self):
        with patch.object(native_fixture,'ROOT',self.directory):
            return prerequisites.check(self,TODAY,self.native)


def reader():
    path=HERE.parents[1]/'scripts/current-s03-sku-s05-composite-qualification/parents.py'
    spec=importlib.util.spec_from_file_location('mandor_original_typed_reader',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class RuntimePrerequisiteControls(unittest.TestCase):
    def test_complete_read_only_originals_roundtrip_and_first_bytes_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory()as name:
            root=Path(name);model=Protocol(root);value=model.check()
            prerequisites.validate(value)
            path=root/'cp6-proof/t3/prerequisites.json';prerequisites.save(path,value)
            packet=reader().strict(path.read_bytes());prerequisites.validate(packet)
            pairs,assets=final_gate.observations(reader(),path.parent,packet)
            self.assertEqual(pairs,1);self.assertEqual(len(assets),2)
            self.assertEqual(model.calls.count('original_actor'),1)
            self.assertEqual(model.boundaries,2)
            self.assertEqual(packet['actual_Native_cases'],0)
            with self.assertRaises(FileExistsError):prerequisites.save(path,{'replacement':True})

    def test_all_missing_categories_are_reported_in_one_pass_before_business(self):
        with tempfile.TemporaryDirectory()as name:
            model=Protocol(Path(name));model.day=TODAY-timedelta(days=1)
            model.functions[prerequisites.FUNCTIONS[0]]=False
            model.permissions[prerequisites.PERMISSIONS[0]]=False
            model.capabilities[prerequisites.FUNCTIONS[1]]=False
            model.mappings[prerequisites.MAPPINGS[0]]=[]
            model.location=None;model.pcs=[];model.period=[(TODAY,)]
            value=model.check()
            for prefix in('GENUINE_WIB_DAY_CHANGED','MISSING_DIRECT_CALL:','OWNER_PERMISSION:',
                    'OWNER_DIRECT_CALL:','ACTIVE_POSTABLE_ACCOUNT_MAPPING:',
                    'ACTIVE_FG_WAREHOUSE_REQUIRED','ONE_ACTIVE_COUNT_PCS_REQUIRED','CURRENT_POSTING_DAY_NOT_OPEN'):
                self.assertTrue(any(e.startswith(prefix)for e in value['errors']),prefix)
            self.assertEqual(set(value['owner_actor']['permissions']),set(prerequisites.PERMISSIONS))
            self.assertEqual(set(value['owner_actor']['direct_call_capabilities']),set(prerequisites.FUNCTIONS))
            with self.assertRaises(ValueError):prerequisites.validate(value)
            self.assertFalse(any(q.lower().startswith(('insert ','update ','delete ','grant ','alter '))for q in model.calls))

    def test_owner_claim_never_masks_privileged_database_identity(self):
        with tempfile.TemporaryDirectory()as name:
            for index,identity in enumerate((['postgres','postgres','OWNER'],
                    ['service_role','service_role','OWNER'],['authenticated','postgres','OWNER'],
                    ['authenticated','authenticated','ADMIN'])):
                with self.subTest(identity=identity):
                    model=Protocol(Path(name)/str(index));model.identity=identity
                    value=model.check()
                    self.assertIn('ORDINARY_AUTHENTICATED_OWNER_REQUIRED',value['errors'])
                    with self.assertRaises(ValueError):prerequisites.validate(value)

    def test_original_actor_sql_failure_rolls_back_then_retains_full_observations(self):
        with tempfile.TemporaryDirectory()as name:
            model=Protocol(Path(name));model.actor_error=RuntimeError('modeled current actor unavailable')
            value=model.check()
            self.assertEqual(value['status'],'REFUSED');self.assertFalse(model.abort)
            self.assertEqual(model.boundaries,2)
            pairs,_=final_gate.observations(reader(),Path(name)/'cp6-proof/t3',value)
            self.assertEqual(pairs,1)
            self.assertIn('ORIGINAL_OWNER_HELPER_OR_PERMISSION_QUERY_REFUSED',value['errors'])

    def test_catalogue_data_or_sequence_drift_cannot_hide_behind_healthy_capabilities(self):
        changes=(lambda c:c['actual_all22']['0'].append('changed'),
            lambda c:c['full_data_and_sequences']['MODEL_ONLY_rows'].append(['changed']),
            lambda c:c['full_data_and_sequences']['MODEL_ONLY_sequences'][0].__setitem__(1,19))
        with tempfile.TemporaryDirectory()as name:
            for index,change in enumerate(changes):
                with self.subTest(kind=index):
                    model=Protocol(Path(name)/str(index));model.after_change=change;value=model.check()
                    self.assertIn('READ_ONLY_PREREQUISITES_CHANGED_CATALOGUE_ROWS_OR_SEQUENCES',value['errors'])
                    with self.assertRaises(ValueError):prerequisites.validate(value)
                    with self.assertRaises(ValueError):
                        final_gate.observations(reader(),model.directory/'cp6-proof/t3',value)

    def test_pass_label_does_not_cover_missing_false_or_forged_packet_prerequisites(self):
        with tempfile.TemporaryDirectory()as name:
            value=json.loads(json.dumps(Protocol(Path(name)).check(),default=str))
            changes=(lambda v:v['functions'].pop(prerequisites.FUNCTIONS[0]),
                lambda v:v['owner_actor']['permissions'].__setitem__(prerequisites.PERMISSIONS[0],1),
                lambda v:v['owner_actor']['direct_call_capabilities'].__setitem__(prerequisites.FUNCTIONS[0],False),
                lambda v:v['owner_actor'].__setitem__('identity',['authenticated','postgres','OWNER']),
                lambda v:v['account_mappings'].__setitem__(prerequisites.MAPPINGS[0],[[1,True]]),
                lambda v:v.__setitem__('location',[1,'FG_WAREHOUSE']),
                lambda v:v.__setitem__('active_PCS',[['KG']]),
                lambda v:v.__setitem__('business_day','20261104'),
                lambda v:v.__setitem__('observed_WIB_day','2026-11-05'),
                lambda v:v.__setitem__('open_period',[['2026-11-04']]),
                lambda v:v.__setitem__('actual_Native_cases',False),
                lambda v:v.__setitem__('production_go',True),
                lambda v:v['read_only_originals'].pop('after_original'))
            for index,change in enumerate(changes):
                with self.subTest(mutation=index):
                    modified=deepcopy(value);change(modified)
                    with self.assertRaises(ValueError):prerequisites.validate(modified)


if __name__=='__main__':unittest.main()
