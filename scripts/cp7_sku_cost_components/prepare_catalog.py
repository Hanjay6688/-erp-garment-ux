"""Prepare complete original catalogue queries and DDL-only profile inputs."""
from pathlib import Path
from hashlib import sha256
import ast,json,os,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cp7_sku_cost_components import prepared_product,financial_delta


def prepare(destination):
    raw=(Path(os.environ['CP7_SKU_PARENT_ORIGINALS'])/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json').read_bytes()
    if sha256(raw).hexdigest()!='5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f':raise ValueError('SKU_MONEY_ORIGINAL_CHANGED')
    catalog=json.loads(raw)['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4']['Native_to_copy_handoff']['raw_current_catalog']
    originals={sig:catalog['functions'][sig][0]for sig in prepared_product.parent_original_signatures()}
    product=prepared_product.derive(catalog,originals)
    baseline={sig:catalog['functions'][sig].copy()for sig in (*originals,'erp.be_reconcile_cost_document_v1(uuid,date)')}
    for name in('consumer_delta.py','credit_delta.py','private_delta.py'):
        module=financial_delta.parent(name)
        for sig,definition in module.patched({s:originals[s]for s in module.SIGNATURES}).items():baseline[sig][0]=definition
    parent=json.loads((HERE.parent/'cp7_sku_moving_average/CATALOG_ADDITIONS.json').read_bytes())
    baseline.update(parent['groups']['functions'])
    source=ROOT/'scripts/cp7_ow04_restore_bundle.py';code=source.read_bytes()
    if sha256(code).hexdigest()!='a1605193347cf5b3321a7bdbf8ff6c634df4f4c0a5113eb295e8c3ce44428e00':raise ValueError('SKU_MONEY_CATALOG_QUERIES_CHANGED')
    nodes=[n for n in ast.parse(code).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in('NAMESPACE','QUERIES')for t in n.targets)
        or isinstance(n,ast.FunctionDef)and n.name=='_acl']
    namespace={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),namespace)
    if len(namespace['QUERIES'])!=22:raise ValueError('SKU_MONEY_ALL22_REQUIRED')
    out=dict(classification='ISOLATED_DDL_PROFILE_INPUT_NOT_ERP',product=product,baseline_functions=baseline,
        parent_valuation_sql=(HERE.parent/'cp7_sku_moving_average/valuation.sql').read_text(),
        queries=namespace['QUERIES'],catalog_source_sha256=sha256(code).hexdigest(),
        original_sha256=sha256(raw).hexdigest(),financial_functions_executed=0,production_go=False)
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    path=destination/'CATALOG_INPUT.json';path.write_text(json.dumps(out,sort_keys=True)+'\n')
    print(json.dumps(dict(status='EXACT_ALL22_DDL_INPUT_PREPARED',baseline_functions=len(baseline),candidate_replacements=len(product['definitions']),
        bytes=path.stat().st_size,sha256=sha256(path.read_bytes()).hexdigest(),actual_ERP_cases=0)))


if __name__=='__main__':prepare(sys.argv[1])
