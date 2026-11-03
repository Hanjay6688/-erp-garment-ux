"""Exact Native one-lot bridge; no public facade, physical writer or audit clone."""
from hashlib import sha256
try:from .valuation_delta import Derivation
except ImportError:from valuation_delta import Derivation

ORIGINALS={
 'erp.be_source_revision_v1(uuid,uuid)':'69e27cfc284a3d886d06d8440732a05db3ef858fc32609a72954c96707371766',
 'erp.be_conversion_preview_v1(jsonb)':'a6159f6a6d34c320367d2bc3b84b2ff44d4036dad12bd8ace252af0debdea818',
 'erp.be_post_conversion_v1(jsonb,uuid,text,uuid)':'f902acefd85f1834303797986f61dd7063adac971507c011f616dfded0ed6102',
 'erp.be_reverse_conversion_v1(uuid,text)':'f7a552a9718f88986fca51f4c4614423cf72e32249ed8db0885570838a2c1adf',
}

def derive(catalog,private):
    result={};routes={}
    def edit(sig):
        source=catalog['functions'][sig][0]
        if sha256(source.encode()).hexdigest()!=ORIGINALS[sig]:raise ValueError('SKU_LEGACY_ORIGINAL_CHANGED:'+sig)
        return Derivation(source)
    def save(sig,d):
        if d.inverse()!=catalog['functions'][sig][0]:raise ValueError('SKU_LEGACY_NATIVE_NOT_REVERSIBLE:'+sig)
        result[sig]=d.source;routes[sig]=[r[2]for r in d.routes]

    sig='erp.be_source_revision_v1(uuid,uuid)';d=edit(sig)
    d.once(' select md5(', ' select cp7_sku_conversion.legacy_source_revision_v4(p_lot,p_location,md5(',
           'complete original physical revision plus current whole-source economic revision')
    d.once("'[]'::jsonb))::text)\n$function$", "'[]'::jsonb))::text))\n$function$",'close the original entire revision without changing its source facts')
    save(sig,d)

    sig='erp.be_conversion_preview_v1(jsonb)';d=edit(sig)
    d.once('v_hpp numeric;v_cost jsonb;', 'v_hpp numeric;v_cost jsonb;v_source_pool jsonb;v_target_pool jsonb;',
           'economic preview remains separate from original physical value')
    d.once(" return jsonb_build_object('source_lot_id'", """ if not cp7_sku_conversion.manual_allocation_v1(l.id,t.id,v_location,v_qty,v_at)then
  v_source_pool:=cp7_sku_conversion.pool_quote_v2(s.id,v_location,'GRADE_A');
  v_target_pool:=cp7_sku_conversion.pool_quote_v2(t.id,v_location,'GRADE_A');
  if (v_source_pool->>'qty')::numeric<v_qty then raise exception 'CP7_SKU_INSUFFICIENT_VALUE_POOL: stok fisik bernilai tidak cukup';end if;
  if erp.has_permission('finance.hpp.view')then
   v_cost:=jsonb_build_object('source_unit_hpp',v_source_pool->>'average',
    'source_value',round(v_qty*(v_source_pool->>'average')::numeric,2)::text,
    'native_physical_value',round(v_hpp*v_qty,2)::text,'basis','SKU_LOCATION_GRADE_MOVING_AVERAGE_V2');
  end if;
 end if;
 return jsonb_build_object('source_lot_id'""",'after every original Native guard quote both economic pools; private children retain their admitted physical preview')
    d.once("'source_revision',p_payload->>'expected_version','cost',v_cost);", """'source_revision',p_payload->>'expected_version','cost',v_cost)
  ||case when v_source_pool is null then '{}'::jsonb else jsonb_build_object(
   'source_value_revision',v_source_pool->>'revision','target_value_revision',v_target_pool->>'revision')end;""",
           'opaque source and target value revisions without leaking hidden money')
    save(sig,d)

    sig='erp.be_post_conversion_v1(jsonb,uuid,text,uuid)';d=edit(sig)
    d.once('v_material uuid;v_dest uuid;', 'v_material uuid;v_dest uuid;v_legacy boolean;v_original_preview jsonb;v_native_request uuid;',
           'track only the one Native child that owns its new legacy group')
    token=' v:=erp.be_conversion_preview_v1(p_payload);'
    d.once(token,token+"""
 v_legacy:=not cp7_sku_conversion.manual_allocation_v1(l.id,(v->>'target_product_id')::uuid,
  (v->>'location_id')::uuid,(v->>'qty_pcs')::int,(v->>'physical_at')::timestamptz);
 if v_legacy then
  if exists(select 1 from cp7_sku_conversion.execution_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
   raise exception 'CP7_SKU_LEGACY_EXECUTION_CONFLICT';end if;
  select request_id into strict v_native_request from erp.be_execution_context_v1
   where backend_pid=pg_backend_pid()and transaction_id=txid_current();
  v_original_preview:=v;
  insert into cp7_sku_conversion.groups_v1(request_id,actor,payload)values(p_request,erp.current_app_user_id(),p_payload);
  perform cp7_sku_conversion.prepare_valuation_v2(p_request,v);
  insert into cp7_sku_conversion.legacy_groups_v4(group_id,source_lot_id,origin_kind,rework_id,original_preview,
   native_request_id,admission_backend_pid,admission_transaction_id)
  values(p_request,l.id,p_origin,p_rework,v,v_native_request,pg_backend_pid(),txid_current());
  insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode,source_lot_id,target_id,location_id,qty,physical_at)
  values(pg_backend_pid(),txid_current(),p_request,'POST',l.id,(v->>'target_product_id')::uuid,
   (v->>'location_id')::uuid,(v->>'qty_pcs')::int,(v->>'physical_at')::timestamptz);
  v:=jsonb_set(v,'{source_revision}',to_jsonb(erp.be_source_revision_v1(l.id,(v->>'location_id')::uuid)));
 end if;""",'prepare a one-child economic group under the unchanged Native lock and current owning BE context')
    token=' select destination_lot_id into strict v_dest from erp.product_conversion_allocations where conversion_id=p_request;'
    d.once(token,""" if v_legacy then
  insert into cp7_sku_conversion.members_v1(conversion_id,group_id,line_no)values(p_request,p_request,1);
  perform cp7_sku_conversion.finalize_valuation_v2(p_request);
  delete from cp7_sku_conversion.execution_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and group_id=p_request;
  v:=v_original_preview;
 end if;
"""+token,'finalize only after unchanged Native physical post and all expected-return lines; retain the client preview in the reply')
    save(sig,d)

    sig='erp.be_reverse_conversion_v1(uuid,text)';d=edit(sig)
    d.once('AS $function$\nbegin','AS $function$\ndeclare v_legacy uuid;v_own boolean:=false;v_revalue boolean:=false;v_status text;\nbegin',
           'legacy inverse owns a frame only when no correct outer group inverse exists')
    token=' perform erp.reverse_product_conversion(p_conversion,p_reason);'
    d.once(token,""" select g.group_id into v_legacy from cp7_sku_conversion.legacy_groups_v4 g where g.group_id=p_conversion;
 if v_legacy is not null then
  if (select count(*)from cp7_sku_conversion.members_v1 where group_id=v_legacy)<>1
   or not exists(select 1 from cp7_sku_conversion.members_v1 m
    join cp7_sku_conversion.legacy_groups_v4 g on g.group_id=m.group_id
    join erp.be_conversion_sources_v1 s on s.conversion_id=m.conversion_id
    where m.group_id=v_legacy and m.conversion_id=p_conversion and m.line_no=1
     and s.source_lot_id=g.source_lot_id and s.origin_kind=g.origin_kind and s.rework_id is not distinct from g.rework_id)then
   raise exception 'CP7_SKU_LEGACY_MEMBER_NOT_EXACT';end if;
  if exists(select 1 from cp7_sku_conversion.execution_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current())then
   if not exists(select 1 from cp7_sku_conversion.execution_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()
    and group_id=v_legacy and mode='REVERSE')then raise exception 'CP7_SKU_LEGACY_EXECUTION_CONFLICT';end if;
  else
   select status into strict v_status from erp.product_conversions where id=p_conversion for update;
   if v_status='REVERSED'then
    if not exists(select 1 from cp7_sku_conversion.valuation_postings_v2 where group_id=v_legacy and phase='REVERSE')then
     raise exception 'CP7_SKU_LEGACY_REVERSE_NOT_EXACT';end if;
   else
    perform cp7_sku_conversion.assert_group_inverse_capacity_v3(v_legacy);v_revalue:=true;
   end if;
   insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode)
   values(pg_backend_pid(),txid_current(),v_legacy,'REVERSE');v_own:=true;
  end if;
 end if;
"""+token,'after every original BE dependency guard, admit only the marked single child and its current economic capacity')
    token=" update erp.bc_outstanding_returns_v1 set status='CANCELLED' where id in(select outstanding_id from erp.be_conversion_returns_v1 where conversion_id=p_conversion);"
    d.once(token,token+"""
 if v_own then
  if v_revalue then perform cp7_sku_conversion.reverse_valuation_v2(v_legacy);end if;
  delete from cp7_sku_conversion.execution_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()and group_id=v_legacy;
 end if;""",'after original physical inverse and pending-return cancellation, append current economic inverse once')
    save(sig,d)

    d=Derivation(private)
    d.once("exists(select 1 from cp7_sku_conversion.members_v1 where conversion_id=(p_payload->>'conversion_id')::uuid)",
           "exists(select 1 from cp7_sku_conversion.members_v1 m where conversion_id=(p_payload->>'conversion_id')::uuid\n   and not exists(select 1 from cp7_sku_conversion.legacy_groups_v4 g where g.group_id=m.group_id))",
           'legacy reverse retains the original Native facade, idempotency namespace and audit response')
    d.once("'expected_version',part->'source_revision'", "'expected_version',erp.be_source_revision_v1((part->>'source_lot_id')::uuid,(v->>'location_id')::uuid)",
           'translate only an already admitted private child under its exact execution frame')
    if d.inverse()!=private:raise ValueError('SKU_LEGACY_PRIVATE_ACTION_NOT_REVERSIBLE')
    result['cp7_sku_conversion.action_v1(text,jsonb,uuid)']=d.source
    routes['cp7_sku_conversion.action_v1(text,jsonb,uuid)']=[r[2]for r in d.routes]
    return result,routes


def bind_base_transition(source):
    d=Derivation(source)
    d.once('and b.transaction_id=e.transaction_id and b.request_id=pc.id))',
           """and b.transaction_id=e.transaction_id and(b.request_id=pc.id or exists(
     select 1 from cp7_sku_conversion.legacy_groups_v4 g
     join erp.be_conversion_sources_v1 s on s.conversion_id=g.group_id
     where g.group_id=pc.id and g.group_id=e.group_id and g.source_lot_id=e.source_lot_id
      and g.admission_backend_pid=e.backend_pid and g.admission_transaction_id=e.transaction_id
      and g.native_request_id=b.request_id and s.source_lot_id=g.source_lot_id
      and s.origin_kind=g.origin_kind and s.rework_id is not distinct from g.rework_id))))""",
           'automatic rework preserves its separate Native request; immutable same-transaction legacy admission must match every source fact')
    if d.inverse()!=source:raise ValueError('SKU_LEGACY_PENDING_NATIVE_NOT_REVERSIBLE')
    return d.source
