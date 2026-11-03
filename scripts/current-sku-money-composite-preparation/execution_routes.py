"""Derive only owning routes from the immutable complete current-parent path.

The generator and checker never fetch, connect, install or dispatch. Every
route is reversed and compared with its complete original bytes before use.
"""
from hashlib import sha256
from pathlib import Path
import ast
import json
import os
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE_TREE='8e48277b86c0325ae15793cd4d6b5094033c8c0e'
OLD='scripts/current-sku-composite-preparation/'
KINDS=('runtime','materialize','fetch','artifacts','receipts','supervisor','workflow','final_gate')


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def original(kind):
    return subprocess.check_output(['git','-C',str(ROOT),'show',BASE_TREE+':'+OLD+'sku_current_parent_'+kind+'.py'],
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))


def derive(kind):
    if kind not in KINDS:raise ValueError('CURRENT_MONEY_EXACT_EXECUTION_KIND_REQUIRED')
    raw=original(kind);text=raw.decode();routes=[]
    def route(before,after,count=1):
        nonlocal text
        found=text.count(before)
        if count is None:count=found
        if not count or found!=count or after in text:
            raise ValueError('CURRENT_MONEY_EXACT_EXECUTION_ROUTE:'+kind+':'+before)
        text=text.replace(before,after)
        routes.append(dict(before=before,after=after,occurrences=count))
    for before,after in(
        ('current-sku-composite-preparation','current-sku-money-composite-preparation'),
        ('sku_current_parent_','money_current_parent_'),
        ('SKU_CURRENT_PARENT','SKU_CURRENT_PARENT_MONEY'),
        ('qualified-sku-moving-average','qualified-sku-money'),
        ('sku-current-parent-native6-20261103','sku-current-parent-money-native19-20261104'),
        ('cp7-sku-current-parent-native6','cp7-sku-current-parent-money-native19'),
        ('sku-current-parent-native6.workflow.yml.txt','sku-current-parent-money-native19.workflow.yml.txt'),
        ('cp7-current-parent-sku6-single-owning-qualification','cp7-current-parent-money19-single-owning-qualification'),
        ('SKU6_CHILD_ROOT_ACTUAL_INTAKE.json','SKU_MONEY19_CHILD_ROOT_ACTUAL_INTAKE.json'),
        ('SKU_CURRENT_SKU6','SKU_CURRENT_MONEY19'),
        ('sku-current-sku6','sku-current-money19'),
        ('QUALIFIED_SKU6.zip','QUALIFIED_MONEY19.zip'),
        ('qualified_SKU_moving_average_sources','qualified_SKU_cost_money_sources'),
        ('CP7_SKU_MOVING_AVERAGE_QUALIFICATION.json','CP7_SKU_COST_MONEY_QUALIFICATION.json'),
        ('_NATIVE6','_NATIVE19'),
        ('Native6','money Native19'),
        ('ACTUAL_MANDOR17_SKU6_SOURCES','ACTUAL_MANDOR17_MONEY19_SOURCES'),
        ('Mandor17 and SKU6 canonical','Mandor17 and money Native19 canonical'),
    ):
        if before in text:route(before,after,None)
    if kind=='runtime':
        route('import money_current_parent_admission as admission\nimport money_current_parent_assembly as assembly\n'
              'import money_current_parent_package as package_derivation\nimport money_current_parent_component as component',
              'from money_execution_bindings import admission,assembly,package_derivation,component,retained_arguments')
        route('receipt=admission.admitted(parent_raw,sku_raw)',
              "receipt=admission.admitted(parent_raw,sku_raw,assembly.prepared_sources()[0]['native_case_ids'])")
        route('def runtime():','@retained_arguments()\ndef runtime():')
        route("existing=sys.modules.get('cp7_sku_moving_average')","existing=sys.modules.get('cp7_sku_cost_components')")
        route("FROZEN_SKU/'scripts/cp7_sku_moving_average/__init__.py'","FROZEN_SKU/'scripts/cp7_sku_cost_components/__init__.py'")
        route('from cp7_sku_moving_average import composition as accepted_child','from cp7_sku_cost_components import composition as accepted_child')
        route('component.load_prepared(product,parent_raw,sku_raw,','component.load_prepared(assembly,product,parent_raw,sku_raw,')
        route("'/tmp/current_parent_sku_native6_pre.dump'","'/tmp/current_parent_sku_money_native19_pre.dump'")
        route("HERE/'check_source.py').source()","HERE/'check_source.py').check()")
    else:
        if 'import money_current_parent_admission as admission' in text:
            route('import money_current_parent_admission as admission','from money_execution_bindings import admission')
    if kind=='fetch':
        route("else'6'","else'19'")
    if kind=='receipts':
        route("'CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19.json',",
              "'CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19.json','CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19_PREFLIGHT.json',")
    if kind=='final_gate':
        route('six actual current-parent cases','nineteen actual current-parent money cases')
        route('SIX','NINETEEN',None)
        route('import money_current_parent_component as component','from money_execution_bindings import component\nimport money_gate_support as money_gate')
        route("NATIVE=component.LABEL+'.json'","NATIVE=component.LABEL+'.json'\nPREFLIGHT=component.LABEL+'_PREFLIGHT.json'")
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='case_ids')
        route(ast.get_source_segment(text,node),'def case_ids():return money_gate.case_ids(runtime,admission)')
        for before,after in(('actual_Native_cases=6','actual_Native_cases=19'),
            ('actual_business_cases=6','actual_business_cases=19'),("counts={'PASS':6}","counts={'PASS':19}"),
            ("'SKU_LOCATION_GRADE_MOVING_AVERAGE'","'SKU_LOCATION_GRADE_MOVING_AVERAGE_WITH_SOURCE_CENTS'"),
            ('CURRENT_PARENT_SKU_NATIVE19_ONLY','CURRENT_PARENT_SKU_MONEY_NATIVE19_ONLY')):
            if before in text:route(before,after,None)
        route('CURRENT_MANDOR_PARENT_SKU_NATIVE19','CURRENT_MANDOR_PARENT_SKU_MONEY_NATIVE19',None)
        route("part=main['committed'][component.CASE]",
              "part=main['committed'][component.CASE]\n    money_gate.validate_preflight(p,part,docs[PREFLIGHT])")
        route("names=(MAIN,NATIVE,'T3_PACKAGE_INSTALL.json'","names=(MAIN,NATIVE,PREFLIGHT,'T3_PACKAGE_INSTALL.json'")
    compile(text,'current-money-derived-'+kind,'exec')
    restored=text
    for item in reversed(routes):
        if restored.count(item['after'])!=item['occurrences']:
            raise ValueError('CURRENT_MONEY_EXACT_EXECUTION_INVERSE:'+kind)
        restored=restored.replace(item['after'],item['before'])
    if restored.encode()!=raw:raise ValueError('CURRENT_MONEY_EXECUTION_ORIGINAL_NOT_RECOVERED:'+kind)
    return text,dict(original_tree=BASE_TREE,original=pin(raw),derived=pin(text.encode()),
        route_groups=len(routes),route_occurrences=sum(r['occurrences']for r in routes),
        complete_original_recovered=True,actual_ERP_cases=0,production_go=False)


def prerequisites():
    reference=json.loads((HERE/'SOURCE_REFERENCE.json').read_bytes())
    name='scripts/current-sku-cost-money-qualification/native_preflight.py'
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',reference['candidate_tree']+':'+name],
        env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
    if pin(raw)!=reference['files'][name]:raise ValueError('CURRENT_MONEY_EXACT_NATIVE_PREFLIGHT_SOURCE')
    values={}
    for node in ast.parse(raw).body:
        if isinstance(node,ast.Assign)and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            key=node.targets[0].id
            if key in('FUNCTIONS','ACTOR_FUNCTIONS','ACCOUNT_MAPPINGS','PERMISSIONS'):
                values[key]=ast.literal_eval(node.value)
    required=sorted(set(values['FUNCTIONS']).union(*values['ACTOR_FUNCTIONS'].values()))
    if len(required)!=23 or sum(len(v)for v in values['ACTOR_FUNCTIONS'].values())!=19:
        raise ValueError('CURRENT_MONEY_COMPLETE_NINETEEN_PREREQUISITE_COVERAGE')
    return dict(classification='EXACT_NATIVE19_SOURCE_CONSTANTS_NOT_RUNTIME_ACCEPTANCE',source=pin(raw),
        required_functions=required,actor_functions=values['ACTOR_FUNCTIONS'],permissions=values['PERMISSIONS'],
        account_mappings=values['ACCOUNT_MAPPINGS'],actual_ERP_cases=0,production_go=False)


def check():
    proofs={}
    for kind in KINDS:
        text,proof=derive(kind);path=HERE/('money_current_parent_'+kind+'.py')
        if path.is_symlink()or path.read_bytes()!=text.encode():
            raise ValueError('CURRENT_MONEY_EXACT_DERIVED_EXECUTION_FILE:'+kind)
        proofs[kind]=proof
    expected=json.loads(json.dumps(prerequisites()))
    if json.loads((HERE/'EXECUTION_PREREQUISITES.json').read_bytes())!=expected:
        raise ValueError('CURRENT_MONEY_EXACT_PREREQUISITE_SOURCE_CONSTANTS')
    return dict(status='EXACT_CURRENT_MONEY_EXECUTION_ROUTES_ONLY_NOT_ERP',files=proofs,
        actual_ERP_cases=0,active_workflow_added=False,production_go=False)


if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
