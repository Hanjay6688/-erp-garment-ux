"""Observe an installed and preserved synthetic Global on its local PostgreSQL socket."""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import os
import uuid
import psycopg

PARENT_PRODUCT = 'ffda5cfceb7ebc196656baa650dffd18dd425047'
PARENT_TREE = '760f38cc80ee9ca15e62a86ba358dfd8e858d895'
PARENT_SEAL = 'a3da0ecf21909731ab8474c54a7c91afb75bb58dd8b6042cc82314b20808dbd7'
CHILD_PRODUCT='475980f2d07a60ea9a2576fe0d8fe50e63653434'
CHILD_TREE='659a119964b84c8787e747594c5b309b547932c6'
CHILD_SEAL='da0b424f305f0b423808d445034ff8a166e32a8d9d13f811078daf2c864b012b'
PRODUCT=os.environ.get('ASTRA_AUDITED_CANDIDATE',PARENT_PRODUCT)
ORDER_PRODUCT='48858590a361343e73a7f16f6646363dc155c04e'
if PRODUCT==ORDER_PRODUCT:
    TREE,SEAL='21feb69a839e74773aa87bc587bbf91a2d301144','deb596acb49e10ac66e0a1616a582ff74889146c0b59ee0d81ac7c2818397821'
elif PRODUCT==CHILD_PRODUCT:
    TREE,SEAL=CHILD_TREE,CHILD_SEAL
elif PRODUCT==PARENT_PRODUCT:
    TREE,SEAL=PARENT_TREE,PARENT_SEAL
else:
    raise ValueError('Unrecognised audit candidate')
TODAY = datetime.now(ZoneInfo('Asia/Jakarta')).date()
OUT = Path(os.environ['AUDIT_RESULTS']).resolve()
OUT.mkdir(exist_ok=True, parents=True)
def db():
    return dict(host=os.environ['PGHOST'],user=os.environ.get('PGUSER','supabase_admin'),dbname='cp6_rollback',connect_timeout=12)
def first(q,statement,*args):
    return q.execute(statement,args or None).fetchone()[0]
def save(label,data):
    path=OUT/(label+'.json')
    val=dict(candidate=PRODUCT,tree=TREE,origin_run='44671146483',audit_run=os.environ.get('GITHUB_RUN_ID','local'),**data)
    tmp=path.with_suffix('.part')
    tmp.write_text(json.dumps(val,indent=2,ensure_ascii=False,default=str)+'\n')
    tmp.replace(path)
def read(label):
    return json.loads((OUT/(label+'.json')).read_bytes())
def admin(q):
    import cp6_bd_probe as boundary
    boundary.api.admin(q)
def actors(q):
    import cp7_master_cases as master
    return [master.role_actor(q,'OWNER') for _ in range(2)]
def measure_seal(q):
    value=first(q,'select cp7_global_nonpo_envelope.catalogue_fingerprint_v1()')
    record=json.loads((Path(os.environ['RUNNER_TEMP'])/'cp7-global-auditor'/'installed.json').read_bytes())
    assert record['product']==PARENT_PRODUCT and record['tree']==PARENT_TREE
    if PRODUCT==PARENT_PRODUCT:
        assert record['server_catalogue_fingerprint']==value
    elif PRODUCT==ORDER_PRODUCT:
        installed=read('installation')
        base=read('parent-installation')
        assert base['parent_seal']['sha256']==record['server_catalogue_fingerprint']['sha256']==PARENT_SEAL
        assert base['installed']['sha256']==installed['parent_seal']==CHILD_SEAL
        assert installed['run']==os.environ['GITHUB_RUN_ID'] and installed['candidate']==PRODUCT and installed['tree']==TREE
        assert installed['factory_matches_installed'] and installed['seal']==SEAL
    else:
        installation=read('candidate-install')
        assert installation['parent_seal']==record['server_catalogue_fingerprint']['sha256']==PARENT_SEAL
        assert installation['outcome']=='PASS' and installation['candidate']==PRODUCT and installation['tree']==TREE and installation['child_seal']==value['sha256']
    assert value['sha256']==SEAL and value['groups']==25 and len(value['counts'])==25
    return dict(groups=value['groups'],sha256=value['sha256'],matched_groups=value['counts'])
@contextmanager
def connection(params,report,label):
    with psycopg.connect(**params) as c,c.cursor() as q:
        report.setdefault('transactions',[]).append(dict(step=label,pid=first(q,'select pg_backend_pid()')))
        yield q
def effects(q):
    admin(q)
    names=['erp.fg_stock_movements','erp.material_stock_movements','erp.journal_entries','erp.journal_lines','erp.sales_items','cp7_plan_native.intents','cp7_plan_native.drafts','erp.cutting_groups']
    return {t:first(q,"select md5(coalesce(string_agg(row_hash,'' order by row_hash),'')) from (select md5(to_jsonb(v)::text) row_hash from "+t+" v) s") for t in names}
def record_failure(label,err):
    result=read(label) if (OUT/(label+'.json')).exists() else {}
    for k in ('candidate','tree','origin_run','audit_run'):result.pop(k,None)
    result.update(outcome='INCOMPLETE',error_type=type(err).__name__,error=str(err).split('CONTEXT:')[0][:700],sqlstate=getattr(err,'sqlstate',None))
    import traceback
    result['where']=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name}for f in traceback.extract_tb(err.__traceback__)[-9:]]
    save(label,result)
    print(label,result['outcome'],result['error_type'],str(result['error'])[:350],flush=True)
