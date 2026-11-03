"""Adversarial checks against a complete real empty-PG17 DDL capture.

Generate the report with prepare_catalog.py and profile_catalog.mjs first.
These controls prove catalogue admission, never ERP financial acceptance.
"""
from copy import deepcopy
from pathlib import Path
import json,os,sys,unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from cp7_sku_cost_components.catalog_additions import transition


class CatalogueTransition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads(Path(os.environ['CP7_COST_CATALOG_REPORT']).read_bytes())
        cls.profile=json.loads((HERE/'CATALOG_ADDITIONS.json').read_bytes())
        if cls.report['status']!='POSTGRES17_COST_MONEY_DDL_ALL22_ACL_UNUSED_INVERSE_PASS_NOT_NATIVE':
            raise ValueError('COMPLETE_REAL_DDL_CAPTURE_REQUIRED')
        if cls.report['before']!=cls.report['restored']:raise ValueError('EXPLICIT_INVERSE_MUST_BE_EXACT')

    def refuse(self,mutate):
        before=deepcopy(self.report['before']);after=deepcopy(self.report['after'])
        mutate(before,after)
        with self.assertRaises(ValueError):transition(before,after,self.profile)

    def test_exact_real_transition(self):transition(self.report['before'],self.report['after'],self.profile)

    def test_hidden_privilege_and_metadata_changes(self):
        new='cp7_sku_conversion.base_current_unit_v4(uuid,uuid)'
        old='erp.post_opening_hpp_correction(uuid,numeric,text,date)'
        table='cp7_sku_conversion.base_money_events_v4'
        index='cp7_sku_conversion.base_money_events_root_product_v4'
        def privilege(b,a):a['functions'][new][18].append(['authenticated','postgres','EXECUTE',False])
        def old_privilege(b,a):a['functions'][old][18].append(['service_role','postgres','EXECUTE',False])
        def body(b,a):a['functions'][new][0]=a['functions'][new][0].replace('return c.amount/c.units;','return 0;')
        def predecessor(b,a):b['functions'][old][0]+='\n-- alternate predecessor'
        def bypass_name(b,a):a['functions']['cp7_sku_conversion.cost_unapproved_v3()']=a['functions'][new]
        def search_path(b,a):a['functions'][new][12]=['search_path=public']
        def rls(b,a):a['relations'][table][3]=False
        def columns(b,a):a['columns'].pop(table+':amount_delta')
        def index_invalid(b,a):a['indexes'][index][1]=False
        def extra_policy(b,a):a['policies'][table+':allow_all']=['*',True,['PUBLIC'],'true','true']
        def membership(b,a):a['memberships']['postgres:authenticated:postgres']=[False,True,True]
        def old_role(b,a):a['roles']['authenticated'][0]=True
        def schema_acl(b,a):a['schemas']['cp7_sku_conversion'][1].append(['authenticated','postgres','CREATE',False])
        def untouched_function(b,a):a['functions']['cp7_sku_conversion.immutable_v1()'][0]+='\n-- changed guard'
        def missing_group(b,a):a.pop('database_authority')
        def new_extension(b,a):a['extensions']['unapproved']=['1','public','postgres',False,None,None]
        for mutate in(privilege,old_privilege,body,predecessor,bypass_name,search_path,rls,columns,index_invalid,extra_policy,
                      membership,old_role,schema_acl,untouched_function,missing_group,new_extension):
            with self.subTest(counter=mutate.__name__):self.refuse(mutate)


if __name__=='__main__':unittest.main()
