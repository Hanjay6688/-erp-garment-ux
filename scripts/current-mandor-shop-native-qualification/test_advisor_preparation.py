"""Source and explicit authority models, not ERP or security acceptance."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import ast,importlib.util,json,unittest
import advisor_review as current


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


AFUI=load('modeled_frozen_Afui_advisor',current.ROOT/current.PARENT_PATH)
LEGACY=AFUI.parent()
nodes=[n for n in ast.parse((current.ROOT/'scripts/cp7_ow04_probe.py').read_bytes()).body
    if isinstance(n,ast.FunctionDef)and n.name=='advisor_disposition']
assert len(nodes)==1
namespace={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'exact_inert_legacy_advisor_function','exec'),namespace)
PREDECESSOR=namespace['advisor_disposition']


def modeled_authority():
    original=dict(object=[LEGACY.SCHEMA,LEGACY.TABLE],owner='cp7_capture',rls=True,policies=[],
        public_schema_acl_empty=True,public_table_acl_empty=True,
        schema_usage={role:False for role in LEGACY.ROLES},
        table_privileges={role:{priv:False for priv in LEGACY.PRIVILEGES}for role in LEGACY.ROLES})
    afui=dict(predecessor=original,Afui={name:dict(object=[AFUI.SCHEMA,name],owner='postgres',rls=True,
        force_rls=False,policies=[],public_schema_acl_empty=True,public_table_acl_empty=True,
        schema_usage={role:False for role in AFUI.ROLES},
        table_privileges={role:{priv:False for priv in AFUI.PRIVILEGES}for role in AFUI.ROLES})for name in AFUI.TABLES})
    child={name:dict(object=[current.SCHEMA,name],owner='postgres',rls=True,force_rls=False,policies=[],
        schema_owner='postgres',nonowner_schema_acl=[[role,'USAGE',False]for role in current.SCHEMA_ROLES],
        nonowner_table_acl=[],nonowner_column_acl=[],
        schema_usage={role:role in current.SCHEMA_ROLES for role in current.ROLES},
        table_privileges={role:{priv:False for priv in current.PRIVILEGES}for role in current.ROLES})for name in current.TABLES}
    return dict(Afui=afui,Mandor=child)


def finding(schema,name):
    return dict(name='rls_enabled_no_policy',level='INFO',metadata=dict(type='table',schema=schema,name=name))


def modeled_delta():
    return dict(status='REVIEW_REQUIRED',before=0,after=19,removed=[],
        added=[finding(LEGACY.SCHEMA,LEGACY.TABLE)]+[finding(AFUI.SCHEMA,n)for n in AFUI.TABLES]
            +[finding(current.SCHEMA,n)for n in current.TABLES])


class AdvisorPreparation(unittest.TestCase):
    def setUp(self):
        self.scope=patch.object(current,'parent',return_value=AFUI);self.scope.start();self.addCleanup(self.scope.stop)
        self.proof=modeled_authority();self.delta=modeled_delta()

    def test_original_default_refuses_three_Afui_and_fifteen_Mandor_infos(self):
        old=LEGACY.review(self.delta,[],self.proof['Afui']['predecessor'],PREDECESSOR)
        self.assertFalse(old['gate']);self.assertEqual(len(old['unexplained']),18)
        self.assertEqual(len(old['reviewed_new_private_info']),1)

    def test_composed_live_authority_model_and_both_original_reviewers(self):
        result=current.review(self.delta,[],self.proof,PREDECESSOR)
        self.assertTrue(result['gate']);self.assertEqual(len(result['reviewed_Mandor_private_info']),15)
        self.assertEqual(len(result['predecessor_disposition']['reviewed_Afui_private_info']),3)
        self.assertTrue(result['unchanged_parent_remainder_disposition']['gate'])

    def test_original_delta_proof_and_predecessor_manifest_are_not_mutated(self):
        before=deepcopy((self.delta,self.proof));manifest=[]
        result=current.review(self.delta,manifest,self.proof,PREDECESSOR)
        self.assertEqual((self.delta,self.proof),before);self.assertEqual(manifest,[])
        self.assertEqual(result['complete_original_delta'],self.delta)
        for state in ['FAILED','MISSING_RESULT','NOT_COMPARABLE',None]:
            self.assertFalse(current.review(dict(self.delta,status=state),[],self.proof,PREDECESSOR)['gate'])

    def test_warnings_unknown_objects_and_other_conditions_stay_unexplained(self):
        base=finding(current.SCHEMA,current.TABLES[0])
        changes=[dict(base,level='WARN'),dict(base,name='rls_disabled_in_public'),
            dict(base,metadata=dict(base['metadata'],type='view')),
            dict(base,metadata=dict(base['metadata'],schema='public')),
            dict(base,metadata=dict(base['metadata'],name='unreviewed_table'))]
        for row in changes:
            with self.subTest(row=row):
                result=current.review(dict(self.delta,added=self.delta['added']+[row]),[],self.proof,PREDECESSOR)
                self.assertFalse(result['gate']);self.assertIn(row,result['unexplained'])

    def test_duplicate_child_Afui_and_original_work_infos_are_refused(self):
        for index in [0,1,-1]:
            row=deepcopy(self.delta['added'][index]);row['detail']='same object with another diagnostic detail'
            self.assertFalse(current.review(dict(self.delta,added=self.delta['added']+[row]),[],self.proof,PREDECESSOR)['gate'])

    def test_every_table_requires_exact_owner_rls_schema_and_all_nonowner_acls(self):
        for name in current.TABLES:
            for key,value in [('owner','other_owner'),('rls',False),('force_rls',True),('policies',[['permissive']]),
                ('schema_owner','other_owner'),('nonowner_schema_acl',[]),
                ('nonowner_table_acl',[['rogue','SELECT',False]]),
                ('nonowner_column_acl',[['id','rogue','SELECT',False]])]:
                proof=deepcopy(self.proof);proof['Mandor'][name][key]=value
                with self.subTest(name=name,key=key),self.assertRaisesRegex(ValueError,'PRIVATE_LIVE_AUTHORITY_CHANGED'):
                    current.require_closed(proof)
            proof=deepcopy(self.proof);proof['Mandor'][name]['table_privileges']['authenticated']['SELECT']=True
            with self.assertRaisesRegex(ValueError,'PRIVATE_LIVE_AUTHORITY_CHANGED'):current.require_closed(proof)
            proof=deepcopy(self.proof);proof['Mandor'].pop(name)
            with self.assertRaisesRegex(ValueError,'EXACT_FIFTEEN_LIVE_AUTHORITIES'):current.require_closed(proof)
        proof=deepcopy(self.proof);proof['Afui']['Afui'][AFUI.TABLES[0]]['rls']=False
        with self.assertRaisesRegex(ValueError,'NONPAYABLE_ADVISOR_PRIVATE'):current.require_closed(proof)

    def test_false_parent_gate_cannot_be_promoted_even_without_unexplained_items(self):
        refused=SimpleNamespace(require_closed=lambda proof:proof,
            review=lambda *args:dict(gate=False,status='PARENT_REFUSED',unexplained=[]))
        with patch.object(current,'parent',return_value=refused):
            self.assertFalse(current.review(self.delta,[],self.proof,PREDECESSOR)['gate'])

    def test_exact_plan_and_read_only_metadata_queries(self):
        proof=current.source();self.assertEqual(proof['private_tables'],15)
        tree=ast.parse((current.HERE/'advisor_review.py').read_bytes())
        capture=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='capture')
        queries=[n.args[0].value for n in ast.walk(capture)if isinstance(n,ast.Call)
            and isinstance(n.func,ast.Attribute)and n.func.attr=='execute']
        self.assertEqual(len(queries),8)
        self.assertTrue(all(q.lower().startswith('select ')and';'not in q for q in queries))
        self.assertIn('aclexplode(t.attacl)',queries[5])

    def test_owning_engine_selects_this_reviewer_and_records_its_source(self):
        tree=ast.parse((current.HERE/'qualification.py').read_bytes())
        runtime=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='runtime_inherited')
        assignments=[n for n in ast.walk(runtime)if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Attribute)and isinstance(t.value,ast.Name)and t.value.id=='engine'
                and t.attr=='current_advisor'for t in n.targets)]
        self.assertEqual(len(assignments),1);self.assertEqual(ast.dump(assignments[0].value),"Name(id='advisor_review', ctx=Load())")
        self.assertIn('owning_advisor_source=advisor_review.source()',ast.unparse(runtime))

    def test_missing_frozen_parent_refuses_without_importing_local_reference_as_parent(self):
        self.scope.stop()
        with TemporaryDirectory()as directory,patch.object(current,'FROZEN',Path(directory)):
            with self.assertRaisesRegex(ValueError,'EXACT_ACCEPTED_FROZEN_AFUI_REVIEWER'):current.parent()


if __name__=='__main__':unittest.main()
