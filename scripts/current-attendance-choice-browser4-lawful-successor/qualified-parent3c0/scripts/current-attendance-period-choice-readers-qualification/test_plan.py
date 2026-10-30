"""Local source/API preparation controls only; no DB/Native/Auth execution."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from unittest.mock import patch
import importlib.util
import json
import unittest

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


a=load('s03_reader_preparation_admission',HERE/'admission.py')
m=load('s03_reader_callbacks_declaration_only',HERE/'cases.py')


def group():
    original=a.ids(a.ROOT/'scripts/current-attendance-period-choice-qualification/cases.py')
    return dict(status='PASS',counts=dict(PASS=11,FAIL=0,INCOMPLETE=0),planned_case_ids=list(original),
                complete_boundary_restored=True,cases={key:dict(status='PASS')for key in original})


class Preparation(unittest.TestCase):
    def test_source_counts_are15_captures_but11_plus3_equals14_cases(self):
        data=a.sources();self.assertEqual(data['counts']['existing_captures'],15)
        self.assertEqual(data['counts']['total_prepared_Native_cases'],14)
        self.assertEqual(data['counts']['actual_Native_credit'],0)
        self.assertEqual(a.admit(group())['additional_Native_credit_before_execution'],0)
    def test_fresh_original11_partial_missing_changed_ids_bool_and_boundary_refuse(self):
        for kind in('missing','count','bool','failed','plan','boundary'):
            model=group();key=model['planned_case_ids'][0]
            if kind=='missing':model['cases'].pop(key)
            if kind=='count':model['counts']['PASS']=10
            if kind=='bool':model['counts']['FAIL']=False
            if kind=='failed':model['cases'][key]['status']='INCOMPLETE'
            if kind=='plan':model['planned_case_ids']=model['planned_case_ids'][:-1]
            if kind=='boundary':model['complete_boundary_restored']=False
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'FRESH_UNCHANGED_FINANCIAL11'):a.admit(model)
    def test_product_and_own_source_mutations_refuse_without_arbitrary_rehash(self):
        source=a.sources()
        with TemporaryDirectory()as directory:
            root=Path(directory);own=root/'prepared';own.mkdir()
            for name in a.OWN_FILES:(own/name).write_bytes((HERE/name).read_bytes())
            for name in a.PRODUCT_FILES:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((a.ROOT/name).read_bytes())
            path=own/'SOURCE.json';path.write_text(json.dumps(source));a.sources(root,path)
            target=root/'scripts/cp7_attendance_period_choice/readers.sql';target.write_text(target.read_text()+'\n-- changed control\n')
            with self.assertRaisesRegex(ValueError,'PRODUCT_SOURCE_CHANGED'):a.sources(root,path)
            target.write_bytes((a.ROOT/'scripts/cp7_attendance_period_choice/readers.sql').read_bytes())
            (own/'cases.py').write_text((own/'cases.py').read_text()+'\n# changed control\n')
            with self.assertRaisesRegex(ValueError,'OWN_SOURCE_CHANGED'):a.sources(root,path)
    def test_callback_factory_declares3_without_fixture_and_validates_parent_install(self):
        class NoCursor:
            def __getattr__(self,key):raise AssertionError('PREPARATION_MUST_NOT_QUERY:'+key)
        calls=[]
        composition=NS(predecessor=NS(sources=lambda:{'model_parent':True}),verify=lambda *args:calls.append('actual_install_verifier')or{'LOCAL_MODEL':True})
        core=NS(admission=NS(admit=lambda *args:calls.append('retained_vendor_gate')or{'LOCAL_MODEL':True}),composition=composition,f=NS())
        with patch.object(m,'original',return_value=core):
            callbacks=m.cases(NoCursor(),None,state={},evidence={},fresh_original11=group())
        self.assertEqual(tuple(key for key,_ in callbacks),m.IDS);self.assertTrue(all(callable(fn)for _,fn in callbacks))
        self.assertEqual(calls,['retained_vendor_gate','actual_install_verifier'])
        with patch.object(m,'original',side_effect=AssertionError('MUST_NOT_IMPORT_FIXTURE')):
            with self.assertRaisesRegex(ValueError,'FRESH_UNCHANGED_FINANCIAL11'):
                m.cases(NoCursor(),None,state={},evidence={},fresh_original11=dict(group(),status='FAIL'))
    def test_closed_owned8_and_hold4_shapes_lifetime_ids_and_cutoffs(self):
        source=dict(day='2026-10-20');decision=dict(decision_id='OLD_DECISION');made=dict(event_id='OLD_ALLOCATION')
        row=dict(status='CANCELLED',actions=[],period_start=source['day'],period_end=source['day'],attendance_choice=dict(
            domain='ATTENDANCE_PERIOD_CHOICE',decision_id='OLD_DECISION',allocation_id='OLD_ALLOCATION',
            source_period_start=source['day'],source_period_end=source['day'],output_period_start='2026-10-21',
            output_period_end='2026-10-21',output_period_closed=False))
        m.owned(row,source,made,decision,'2026-10-21',False)
        for kind in('actions','lifetime','dual','cutoff'):
            bad=deepcopy(row)
            if kind=='actions':bad['actions']=['REPLACE']
            if kind=='lifetime':bad['attendance_choice']['decision_id']='NEW_CURRENT_DECISION'
            if kind=='dual':bad['period_hold']={}
            if kind=='cutoff':bad['attendance_choice']['output_period_closed']=True
            with self.subTest(kind=kind),self.assertRaises(AssertionError):m.owned(bad,source,made,decision,'2026-10-21',False)
        blocked=dict(status='BLOCKED',can_create=False,blocker=dict(code='CP7_S03_PERIOD_HELD',message='Owner choice'),
            period_hold=dict(domain='ATTENDANCE_PERIOD_CHOICE',decision_id='OLD_DECISION',source_period_start=source['day'],source_period_end=source['day']),pos=[],
            **{key:None for key in('numerator_amount','denominator_qty','unit_cost_per_sewn_pcs','source_count','destination_count','po_count','manifest_sha256','review_token')})
        m.held_preview(blocked,source,decision)
        for kind in('can_create','token','figures','owned'):
            bad=deepcopy(blocked)
            if kind=='can_create':bad['can_create']=True
            if kind=='token':bad['review_token']='a'*32
            if kind=='figures':bad['numerator_amount']='0.00'
            if kind=='owned':bad['attendance_choice']={}
            with self.subTest(kind=kind),self.assertRaises(AssertionError):m.held_preview(bad,source,decision)
    def test_fixture_uses_real_inverse_writers_not_posted_seeds_or_bypass(self):
        source=(HERE/'cases.py').read_text()
        for forbidden in('session_replication_role','setval(','insert into erp.','update erp.','delete from erp.'):
            self.assertNotIn(forbidden,source.lower())
        for writer in('erp.create_attendance_hpp_pool_v1','erp.activate_attendance_hpp_pool_v1','erp.cancel_attendance_hpp_pool_v1','erp.reverse_sewing_terminal_v1'):
            self.assertIn(writer,source)
        self.assertIn("f.hp.set_closed(cur,s['day']-timedelta(days=1))",source)
        self.assertEqual(len(set(m.IDS)),3)


if __name__=='__main__':unittest.main()
