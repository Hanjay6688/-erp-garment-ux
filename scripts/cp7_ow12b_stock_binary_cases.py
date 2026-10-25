"""Closed Native4 for a separate PG17 reference, before any caller adoption."""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from time import monotonic
from uuid import uuid4
import json,traceback
import psycopg
from psycopg import sql
import cp7_history_reference_binary_v2 as binary_stage
import cp7_ow13c_history_reference_cases as legacy
import cp7_ow12b_factory3600_fixture as fixture
import cp7_ow12b_stock_binary_codec as codec
import cp7_ow11_model_policy_cases as policy
from cp7_ow04_restore_bundle import _catalog_rows

stage,work=legacy.stage,legacy.work
CONTRACT='cp7.ow12b.stock-reference-binary-native4.v1'
IDS=dict(native=['OW12B_STOCK_BINARY_PRIVATE_CATALOG22',
 'OW12B_STOCK_BINARY_NATIVE_RAW_AND_TYPED_FRAME_PARITY',
 'OW12B_STOCK_BINARY_SYNTHETIC1200X3_ORDERED_TIMINGS',
 'OW12B_STOCK_BINARY_ACTUAL_LATE_RECORDED_CLOCK'])
REQUIRED=dict(native=4)
EXPECTED=DECLARED=4
FUNCTIONS,SCHEDULES=legacy.FUNCTIONS,legacy.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE={},{},{},{},{},{}


def sources():
 root=Path(__file__).resolve().parent
 extra=[Path(__file__),Path(codec.__file__),Path(fixture.__file__),Path(policy.__file__),
  root/'cp7_ow12b_stock_binary_probe.py',root/'cp7_ow12b_stock_binary_preflight.py',root/'cp7_f05_analysis_probe.py']
 return {**{'cp7_history_reference/'+k:v for k,v in stage.sources().items()},
  **{'cp7_history_reference_binary_v2/'+k:v for k,v in binary_stage.sources().items()},
  **{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()for p in extra}}


def install(cur):
 stage.verify(cur,REFERENCE_STATE)
 before=_catalog_rows(cur);state=binary_stage.install_delta(cur)
 binary_stage.admit_catalog(before,_catalog_rows(cur),state)
 return state


def digest(cur,products,at,binary=True):
 work.plan.b.api.admin(cur)
 prior=cur.execute('show statement_timeout').fetchone()[0]
 cur.execute('savepoint stock_binary_private_call')
 try:
  cur.execute("set local statement_timeout='8s'")
  cur.execute('set local role cp7_capture')
  name='cp7_history_reference_binary_v2.stock_digest'if binary else'cp7_history_reference.stock_digest'
  value=cur.execute('select '+name+'(%s::jsonb,%s::timestamptz)',(json.dumps(products),at)).fetchone()[0]
 except Exception:
  cur.execute('rollback to savepoint stock_binary_private_call')
  work.plan.b.api.admin(cur);cur.execute('release savepoint stock_binary_private_call');raise
 work.plan.b.api.admin(cur)
 cur.execute("select set_config('statement_timeout',%s,true)",(prior,))
 cur.execute('release savepoint stock_binary_private_call')
 return value


def check_shape(value):
 assert value['contract_version']==binary_stage.render.CONTRACT
 assert value['encoding']==binary_stage.render.ENCODING
 assert value['layout_sha256']==binary_stage.render.LAYOUT_SHA256
 assert value['scope']=='ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
 for key in('raw_rows_truncated','raw_rows_materialized_as_JSON_array','raw_native_capture_status_overridden','apply_enabled','production_go'):assert value[key]is False


def encoder_expression():
 # Exercise the producer's actual framing expression, compared with the
 # independently declared Python encoder/decoder rather than another join.
 text=(binary_stage.ROOT/'digest.sql').read_text();needle='pg_catalog.record_send('
 assert text.count(needle)==1;start=text.index(needle);depth=0;quoted=False
 for i in range(start,len(text)):
  char=text[i]
  if char=="'":quoted=not quoted
  if quoted:continue
  if char=='(':depth+=1
  elif char==')':
   depth-=1
   if depth==0:return text[start:i+1]
 raise AssertionError('BINARY_PRODUCER_FRAME_UNCLOSED')


def typed_controls(cur):
 work.plan.b.api.admin(cur);expr=encoder_expression()
 types={2950:'uuid',17:'text',1184:'timestamptz',20:'int8'}
 projection=','.join('%s::'+types[oid]+' as '+name for name,oid in codec.FIELDS)
 query='with m as(select '+projection+')select '+expr+' from m'
 values=dict(zip((k for k,_ in codec.FIELDS),[
  '11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',
  '33333333-3333-4333-8333-333333333333','44444444-4444-4444-8444-444444444444',
  None,'55555555-5555-4555-8555-555555555555','カイン\nA','-9007199254740993.00',
  '2026-10-25T01:02:03.123456+07:00','2026-10-25T01:02:03.123457+07:00',
  'SALE','SYNTHETIC\nSIZE三',None,None,'9223372036854775807']))
 def wire(row):
  data=bytes(cur.execute(query,tuple(row[k]for k,_ in codec.FIELDS)).fetchone()[0])
  assert data==codec.encode(row)
  assert codec.decode(data)==codec.expected_values(row)
  return data
 first=wire(values)
 for name,oid in codec.FIELDS:
  changed=deepcopy(values)
  changed[name]=str(uuid4())if oid==2950 else'9223372036854775806'if oid==20 else'2026-10-25T01:02:03.123458+07:00'if oid==1184 else changed[name]+' changed'
  current=wire(changed);assert sha256(current).digest()!=sha256(first).digest()
 for special in('-infinity','infinity'):
  changed=deepcopy(values);changed['physical_at']=special;wire(changed)
 # Prepare constants while UTF8 is active, then return bytea under LATIN1.
 # This tests actual client independence without a temporary table/schema.
 prepared=False;prior=cur.execute('show client_encoding').fetchone()[0]
 cur.execute('savepoint stock_binary_encoding_control')
 try:
  projection=sql.SQL(',').join(sql.SQL('{}::{} as {}').format(sql.Literal(values[name]),sql.SQL(types[oid]),sql.Identifier(name))for name,oid in codec.FIELDS)
  cur.execute(sql.SQL('prepare cp7_stock_binary_codec_encoding as with m as(select {})select '+expr+' from m').format(projection));prepared=True
  before=bytes(cur.execute('execute cp7_stock_binary_codec_encoding').fetchone()[0]);assert before==first
  cur.execute("set local client_encoding='LATIN1'")
  assert bytes(cur.execute('execute cp7_stock_binary_codec_encoding').fetchone()[0])==first
 except Exception:
  cur.execute('rollback to savepoint stock_binary_encoding_control');raise
 finally:
  cur.execute("select set_config('client_encoding',%s,true)",(prior,))
  if prepared:cur.execute('deallocate cp7_stock_binary_codec_encoding')
  cur.execute('release savepoint stock_binary_encoding_control')
 return dict(independent_Python_encoder_decoder_exact=True,all15_field_mutations_change_SHA256=True,
  wide_int64_UTF8_newline_microseconds_NULL_infinity_exact=True,LATIN1_and_UTF8_clients_same_bytes=True)


def cases(cur,today):
 observed={}
 def catalog():
  before=_catalog_rows(cur);state=install(cur)
  assert len(before)==22
  v=binary_stage.verify(cur,state);assert v['private_functions']==1 and v['new_tables']==v['public_rpcs']==v['old_replacements']==0
  binary_stage.rollback_preuse(cur,state);assert _catalog_rows(cur)==before
  return dict(status='PASS',private_one_function_no_table_RPC_replacement=True,exact22_inverse=True,
   v1_unchanged=True,server_PG17_UTF8_and_builtin_types_bound=True)
 def parity():
  install(cur);work.plan.fixture(cur,today);capture=legacy.capture(cur)
  assert capture['status']=='COMPLETE'
  before=work.metadata(cur);products=capture['facts']['products'];at=capture['captured_at']
  old=digest(cur,products,at,False);value=digest(cur,products,at);check_shape(value)
  rows=capture['facts']['stock'];expected=codec.digest(rows,binary_stage.render.CONTRACT,binary_stage.render.ENCODING,binary_stage.render.LAYOUT_SHA256)
  assert(value['row_count'],value['rows_sha256'])==expected
  assert value['rows_sha256']!=old['rows_sha256']and old['contract_version']=='cp7.native-stock-row-digest.v1'
  assert digest(cur,list(reversed(products)),at)==value
  empty=digest(cur,[],at);check_shape(empty)
  assert(empty['row_count'],empty['rows_sha256'])==codec.digest([],binary_stage.render.CONTRACT,binary_stage.render.ENCODING,binary_stage.render.LAYOUT_SHA256)
  assert digest(cur,products,at,False)==old
  controls=typed_controls(cur)
  root=products[0]['root_id']
  for scope,clock,error in(({},at,'SCOPE'),(None,at,'SCOPE'),([],None,'SCOPE'),([{}],at,'ROOTS'),([{'root_id':root}]*2,at,'ROOTS'),([{'root_id':root}]*5001,at,'SCOPE')):
   try:digest(cur,scope,clock)
   except psycopg.Error as exc:assert str(exc).splitlines()[0]=='CP7_HISTORY_REFERENCE_V2_'+error
   else:raise AssertionError('BINARY_SCOPE_CONTROL_NOT_REFUSED')
  assert work.metadata(cur)==before
  return dict(status='PASS',**controls,actual_Native_raw_facts_independent_binary_hash_exact=True,
   rows=len(rows),all15_fields_retained=True,v1_hash_unchanged_v2_intentionally_distinct=True,
   malformed_duplicate_missing_over5000_scopes_refused=True,empty_scope_exact=True,root_scope_order_does_not_change_reference=True,reader_no_ERP_write=True)
 def volume():
  install(cur);work.plan.fixture(cur,today);work.plan.b.api.admin(cur)
  base=work.base.retained.formula.sales.fg.base
  actor=policy.master.role_actor(cur,'OWNER')
  size=fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  capture=legacy.capture(cur);assert capture['status']=='INCOMPLETE'and capture['stock_raw_omitted']is True
  products=capture['facts']['products'];rows=[p for p in products if p['sku'].startswith('OW12BF36-')]
  assert len(rows)==len({p['root_id']for p in rows})==3600 and len({p['size_id']for p in rows})==3
  groups={}
  for p in rows:
   assert len(p['commercial'])==1
   groups.setdefault(p['commercial'][0]['sku_id'],set()).add(p['size_id'])
  assert len(groups)==1200 and all(len(v)==3 for v in groups.values())
  before=work.metadata(cur);observed['ordered_measurements']=[];answers=[]
  for phase,binary in(('V1_FIRST',False),('V2_FIRST',True),('V2_SECOND',True),('V1_SECOND',False)):
   start=monotonic()
   try:value=digest(cur,products,capture['captured_at'],binary)
   except Exception:
    observed['failed_measurement']=dict(phase=phase,millis=round((monotonic()-start)*1000,3));raise
   elapsed=round((monotonic()-start)*1000,3)
   observed['ordered_measurements'].append(dict(phase=phase,millis=elapsed,row_count=value['row_count'],rows_sha256=value['rows_sha256']))
   assert elapsed<8000 and int(value['row_count'])>=363600
   if binary:check_shape(value)
   answers.append(value)
  assert answers[0]==answers[3]and answers[1]==answers[2]and answers[0]['rows_sha256']!=answers[1]['rows_sha256']
  assert work.metadata(cur)==before
  return dict(size,status='PASS',actual_Native_qualification=True,actual_products=len(products),
   actual_rows=int(answers[0]['row_count']),measurements=deepcopy(observed['ordered_measurements']),
   no_fastest_run_selection=True,v1_stable_v2_stable_hashes_intentionally_differ=True,reader_no_ERP_write=True,
   statement_limit='8s',caller_integrated=False,factory_SLA_claim=False,official_finance_included=False,production_go=False)
 def late():
  install(cur);work.plan.fixture(cur,today);work.plan.b.api.admin(cur)
  product=work.base.retained.formula.sales.fg.base.BASE_PRODUCT
  root=cur.execute('select coalesce(identity_root_id,id)::text from erp.products where id=%s',(product,)).fetchone()[0]
  ids=[r[0]for r in cur.execute('select m.id from erp.fg_stock_movements m join erp.products p on p.id=m.product_id where coalesce(p.identity_root_id,p.id)=%s::uuid',(root,))]
  work.plan.found_fg(cur,dict(root=product),'1')
  at,recorded,count=cur.execute('select min(m.physical_at),min(m.system_created_at),count(*)from erp.fg_stock_movements m join erp.products p on p.id=m.product_id where coalesce(p.identity_root_id,p.id)=%s::uuid and not(m.id=any(%s::uuid[]))',(root,ids)).fetchone()
  assert count>0 and at<recorded
  cutoff=recorded-timedelta(microseconds=1);assert at<cutoff
  capture=legacy.capture(cur);assert capture['status']=='COMPLETE'
  products=[p for p in capture['facts']['products']if p['root_id']==root];assert len(products)==1
  before=work.metadata(cur);old=digest(cur,products,cutoff);fresh=digest(cur,products,capture['captured_at'])
  rows=[r for r in capture['facts']['stock']if r['root_id']==root]
  old_rows=[r for r in rows if codec.timestamp(r['physical_at'])<=codec.timestamp(cutoff.isoformat())and codec.timestamp(r['system_created_at'])<=codec.timestamp(cutoff.isoformat())]
  for value,expected in((old,old_rows),(fresh,rows)):
   assert(value['row_count'],value['rows_sha256'])==codec.digest(expected,binary_stage.render.CONTRACT,binary_stage.render.ENCODING,binary_stage.render.LAYOUT_SHA256)
  assert int(fresh['row_count'])>=int(old['row_count'])+count and fresh['rows_sha256']!=old['rows_sha256']
  assert digest(cur,products,cutoff)==old and work.metadata(cur)==before
  return dict(status='PASS',actual_Native_writer=True,physical_backdate_not_visible_before_recorded_time=True,
   old_cutoff_immutable=True,both_clock_predicates_pinned_and_Native_facts_exact=True,no_posted_row_or_clock_rewrite=True,reader_no_ERP_write=True)
 def checked(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as exc:return dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked,(catalog,parity,volume,late))))


def races(tools,today):return []
def http_cases(http,today):return []
