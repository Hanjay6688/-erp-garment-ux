"""Separate Native2: 1200 synthetic commercial SKUs x three physical sizes.

Reuse every operational3600 parity assertion and unchanged eight-second calls.
The dimensional geometry is checked on BOTH actual captured references. This
component does not qualify official finance, production writes or factory SLA.
"""
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json
import cp7_ow11_model_target_v2_scale_cases as common
import cp7_ow12b_factory3600_fixture as fixture

CONTRACT='cp7.ow11.model-target-factory1200x3-native.v1'
IDS=dict(native=[common.IDS['native'][0],
 'OW11_MODEL_TARGET_V2_FACTORY1200X3_ALL_PHYSICAL_TARGET_PARITY_SOURCE'])
REQUIRED=dict(native=2)
EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES,stage=common.FUNCTIONS,common.SCHEDULES,common.stage
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 paths=[Path(__file__),Path(fixture.__file__),root/'cp7_ow11_model_target_v2_factory_probe.py',
  root/'cp7_ow11_model_target_v2_factory_preflight.py',root/'cp7_f05_analysis_probe.py']
 return dict(common.sources(),**{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()for p in paths})


def seed(cur,_context):
 common.plan.b.api.admin(cur)
 base=common.bounded.work.base.retained.formula.sales.fg.base
 actor=common.native.policy.master.role_actor(cur,'OWNER')
 return fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)


def profile_roots(cur):
 # Each commercial SKU has three distinct roots. Select size S1 explicitly;
 # do not collapse three physical members with DISTINCT or an arbitrary LIMIT.
 rows=cur.execute("""select p.sku,s.size_code,p.identity_root_id,p.size_id
  from erp.products p join erp.sizes s on s.id=p.size_id
  where p.sku in('OW12BF36-1','OW12BF36-2')order by p.sku,s.size_code""").fetchall()
 assert len(rows)==6
 for sku in('OW12BF36-1','OW12BF36-2'):
  group=[r for r in rows if r[0]==sku]
  assert len(group)==3 and {r[1]for r in group}=={'OW12BF36-S1','OW12BF36-S2','OW12BF36-S3'}
  assert len({str(r[2])for r in group})==len({str(r[3])for r in group})==3
 return[str(r[2])for r in rows if r[1]=='OW12BF36-S1']


def dimensional_signature(products):
 rows=[p for p in products if p['sku'].startswith('OW12BF36-')]
 assert len(rows)==3600,'FACTORY1200X3_CAPTURE_PHYSICAL_PRODUCT_COUNT'
 assert len({p['root_id']for p in rows})==3600,'FACTORY1200X3_DUPLICATE_PHYSICAL_ROOT'
 assert len({p['size_id']for p in rows})==3,'FACTORY1200X3_GLOBAL_SIZE_COUNT'
 groups=defaultdict(list);signature=[]
 for p in rows:
  assert len(p['commercial'])==1,'FACTORY1200X3_AMBIGUOUS_OR_MISSING_COMMERCIAL_MEMBER'
  c=p['commercial'][0]
  assert c['sku']==p['sku']and c['revision']=='1'
  groups[(c['sku_id'],c['sku'])].append((p['size_id'],c['version_id']))
  signature.append(tuple(str(v)for v in(p['id'],p['root_id'],p['size_id'],p['sku'],c['sku_id'],c['version_id'],c['revision'])))
 assert len(groups)==1200,'FACTORY1200X3_COMMERCIAL_SKU_COUNT'
 assert len({sku for _,sku in groups})==1200
 for members in groups.values():
  assert len(members)==3 and len({s for s,_ in members})==3,'FACTORY1200X3_EACH_SKU_REQUIRES_THREE_DISTINCT_SIZES'
  assert len({v for _,v in members})==1,'FACTORY1200X3_MEMBER_VERSION_MISMATCH'
 return sorted(signature)


def captured_shape(cur,run):
 reference=run['row']['reference'];products=reference['facts']['products']
 signature=dimensional_signature(products)
 common.plan.b.api.admin(cur)
 expected=cur.execute("""select p.id,p.identity_root_id,p.size_id,p.sku,s.id,v.id,v.revision
  from erp.products p join erp.bf_sku_members_v1 m on m.product_root=p.identity_root_id
  join erp.bf_sku_versions_v1 v on v.id=m.version_id
  join erp.bf_skus_v1 s on s.id=v.sku_id and s.brand_id=p.brand_id and s.sku=p.sku
  where p.sku like 'OW12BF36-%%'order by p.id""").fetchall()
 assert signature==sorted(tuple(str(v)for v in r)for r in expected),'FACTORY1200X3_CAPTURED_MEMBERS_DIFFER_FROM_ACTUAL_NATIVE'
 targets=reference['bounded_history_inputs']['inputs']['targets']
 keys={r[1]+':'+r[2]for r in signature}
 assert len(keys)==3600
 assert len(targets)==len(products)==run['pages']['targets_total']
 assert {r['target_key']for r in targets if r['target_key']in keys}==keys
 assert sum(r['target_key']in keys for r in targets)==3600,'FACTORY1200X3_PHYSICAL_TARGETS_MISSING_OR_DUPLICATE'
 return dict(products=3600,commercial_SKUs=1200,physical_sizes=3,physical_roots=3600,
  actual_native_members_exact=True,each_SKU_three_distinct_physical_sizes=True,
  all3600_physical_targets_once=True,member_shape_sha256=sha256(json.dumps(signature,separators=(',',':')).encode()).hexdigest())


def cases(cur,today):
 common.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(common,name,globals()[name])
 pairs=common.cases(cur,today,fixture_seed=seed,profile_roots=profile_roots,capture_check=captured_shape)
 def dimensional():
  result=pairs[1][1]()
  if result['status']=='PASS':
   checks=result['dimensional_capture_checks']
   assert set(checks)=={'PREDECESSOR','CURRENT'}and checks['PREDECESSOR']==checks['CURRENT']
   result.update(actual_Native_qualification=True,dimensional_native_component_qualified=True,
    both_captured_references_have1200_SKUs_x3_physical_sizes=True)
  return result
 return[(IDS['native'][0],pairs[0][1]),(IDS['native'][1],dimensional)]


def races(tools,today):return []
def http_cases(http,today):return []
