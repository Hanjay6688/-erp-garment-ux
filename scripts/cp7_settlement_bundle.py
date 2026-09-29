"""P12 native lifecycle adapter; exact accepted non-work preparation, selected work preserved."""
import gzip,hashlib,json
import cp7_settlement_read_bundle as read
import cp7_nota_bundle as nota
ROOT=read.ROOT
CATALOGUE=ROOT/'docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz'

def accepted(name):
    f=next(f for f in json.loads(gzip.decompress(CATALOGUE.read_bytes()))['functions'] if f['schema']=='erp' and f['name']==name)
    assert hashlib.sha256(f['definition'].encode()).hexdigest()==f['definition_sha256']
    return f['definition']

WORK_DELETE='  delete from erp.payroll_work_items where payroll_id = p.id;\n'
WORK_INSERT="""  insert into erp.payroll_work_items(
    payroll_id, po_id, work_component_id, source_type, source_id,
    qty_payable, rate_snapshot
  )
  select p.id, e.po_id, e.work_component_id, e.source_type, e.source_id,
         e.remaining_qty, e.rate_snapshot
  from erp.v_payroll_eligible_work_lines e
  where e.contractor_id = p.contractor_id
    and (e.eligible_at AT TIME ZONE 'Asia/Jakarta')::date <= p.period_end
    and e.remaining_qty > 0
  order by e.eligible_at, e.source_type, e.source_id;
"""

def derive_nonwork(definition):
    assert definition==accepted('populate_payroll_draft'),'P12_POPULATE_PREDECESSOR_CHANGED'
    for part in (WORK_DELETE,WORK_INSERT):assert definition.count(part)==1
    return definition.replace('erp.populate_payroll_draft(p_payroll_id uuid)','cp7_payroll.rebuild_nonwork(p_payroll_id uuid)',1).replace("SET search_path TO 'erp', 'public', 'pg_temp'","SET search_path TO ''",1).replace('  perform erp.require_internal();','  perform cp7_payroll.require_settlement_context(p_payroll_id);',1).replace(WORK_DELETE,'',1).replace(WORK_INSERT,'',1)

CONTEXT="""  if exists(select 1 from cp7_payroll.settlement_context c where c.backend_pid=pg_backend_pid()
    and c.transaction_id=txid_current() and c.actor=auth.uid() and v_jwt_role='authenticated'
    and erp.has_permission('finance.payroll.view')
    and(c.action not in('PREPARE','APPROVE','CANCEL','REVERSE') or erp.has_permission('finance.payroll.approve'))
    and(c.action not in('PAY','REVERSE') or erp.has_permission('finance.payroll.pay'))
  ) then return;end if;
"""
OWNER_ANCHOR="  if coalesce(erp.current_app_role(),'') not in ('OWNER','ADMIN') then"
def patched_internal(d):
    assert d.count(nota.ANCHOR)==1 and 'cp7_payroll.settlement_context' not in d
    return d.replace(nota.ANCHOR,CONTEXT+nota.ANCHOR)
def patched_owner(d):
    assert d==accepted('require_owner_admin') and d.count(OWNER_ANCHOR)==1
    return d.replace(OWNER_ANCHOR,CONTEXT+OWNER_ANCHOR)

def expected_internal():
    body=(ROOT/'scripts/cp7-src/procurement/accepted-deltas.sql').read_text().split('as $function$',1)[1].split('$function$',1)[0]
    return body.replace(nota.ANCHOR,nota.ADMISSION+nota.ANCHOR)

def extension():
    before=accepted('populate_payroll_draft');derived=derive_nonwork(before);owner=accepted('require_owner_admin')
    guard="""do $verify$ begin
 if encode(extensions.digest(pg_get_functiondef('erp.populate_payroll_draft(uuid)'::regprocedure),'sha256'),'hex')<>'%s'
 or encode(extensions.digest(pg_get_functiondef('erp.require_owner_admin()'::regprocedure),'sha256'),'hex')<>'%s'
 or(select encode(extensions.digest(prosrc,'sha256'),'hex') from pg_proc where oid='erp.require_internal()'::regprocedure)<>'%s' then raise exception 'CP7_PAYROLL_PREDECESSOR_CHANGED';end if;
end $verify$;"""%(hashlib.sha256(before.encode()).hexdigest(),hashlib.sha256(owner.encode()).hexdigest(),hashlib.sha256(expected_internal().encode()).hexdigest())
    # Create the private helpers before the derived rebuild body is invoked.
    sql=(ROOT/'scripts/cp7-src/payroll/settlement-write.sql').read_text()
    patch="""do $patch$ declare d text;begin
 d:=pg_get_functiondef('erp.require_internal()'::regprocedure);
 execute replace(d,$anchor$%s$anchor$,$delta$%s$delta$);
 d:=pg_get_functiondef('erp.require_owner_admin()'::regprocedure);
 execute replace(d,$anchor$%s$anchor$,$delta$%s$delta$);
end $patch$;"""%(nota.ANCHOR,CONTEXT+nota.ANCHOR,OWNER_ANCHOR,CONTEXT+OWNER_ANCHOR)
    return '\n'.join((guard,sql,derived+';\nalter function cp7_payroll.rebuild_nonwork(uuid) owner to postgres;\n',"revoke all on function cp7_payroll.rebuild_nonwork(uuid) from public,anon,authenticated,service_role,cp7_capture,cp7_payroll_read,cp7_nota_write,cp7_payroll_header,cp7_payroll_write;",patch))

def bundle():return read.bundle()+'\n'+extension()
RULES={**read.RULES,'settlement_access':('cp7_payroll_read',True,'s'),'require_settlement_context':('postgres',True,'s'),'settlement_meaning':('postgres',True,'s'),'apply_settlement':('postgres',True,'v'),'settlement_command':('cp7_payroll_write',False,'v'),'rebuild_nonwork':('postgres',True,'v')}
