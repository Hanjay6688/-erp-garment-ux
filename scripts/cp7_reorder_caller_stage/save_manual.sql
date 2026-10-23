create or replace function cp7_stock_formula.save_manual(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;h text;prev cp7_stock_formula.manual_points;root uuid;cur_rev integer;prod record;row cp7_stock_formula.manual_points;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_stock_formula.access_now(true);
 if p_request is null then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REQUIRED';end if;
 h:=encode(sha256(convert_to(coalesce(p::text,''),'UTF8')),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0));
 if cp7_stock_formula.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
 select*into prev from cp7_stock_formula.manual_points x where x.request_id=p_request;
 if found then
  if prev.actor<>auth.uid()or prev.request_hash<>h then raise exception using errcode='22023',message='CP7_FORMULA_REQUEST_REUSED';end if;
  if cp7_stock_formula.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
  return jsonb_build_object('contract_version','cp7.fg-reorder-manual.v2','replay',true,'root_id',prev.root_id,'revision',prev.revision,'reorder_point_pcs',prev.reorder_point_pcs);
 end if;
 if jsonb_typeof(p)is distinct from'object'or not p?&array['root_id','expected_revision','reorder_point_pcs','reason']
  or exists(select 1 from jsonb_object_keys(p)k where k not in('root_id','expected_revision','reorder_point_pcs','reason'))
  or jsonb_typeof(p->'root_id')<>'string'or(p->>'root_id')!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'expected_revision')<>'number'or(p->>'expected_revision')!~'^[0-9]{1,9}$'
  or jsonb_typeof(p->'reorder_point_pcs')not in('number','null')or coalesce(p->>'reorder_point_pcs','0')!~'^[0-9]{1,8}$'
  or jsonb_typeof(p->'reason')<>'string'or length(btrim(p->>'reason'))not between 1 and 500
 then raise exception using errcode='22023',message='CP7_FORMULA_MANUAL_INVALID';end if;
 root:=(p->>'root_id')::uuid;
 select p2.id,p2.size_id into prod from erp.products p2 where coalesce(p2.identity_root_id,p2.id)=root and p2.is_active
  and p2.effective_from<=clock_timestamp()and(p2.effective_to is null or p2.effective_to>clock_timestamp());
 if prod.id is null or(select count(*)from erp.products q where coalesce(q.identity_root_id,q.id)=root and q.effective_from<=clock_timestamp()
  and(q.effective_to is null or q.effective_to>clock_timestamp()))<>1 then raise exception using errcode='22023',message='CP7_FORMULA_ITEM_UNKNOWN';end if;
 select coalesce(max(x.revision),0)into cur_rev from cp7_stock_formula.manual_points x where x.root_id=root;
 if cur_rev<>(p->>'expected_revision')::integer then raise exception using errcode='40001',message='CP7_FORMULA_MANUAL_STALE';end if;
 insert into cp7_stock_formula.manual_points(root_id,revision,size_id,product_version_id,reorder_point_pcs,reason,actor,request_id,request_hash)
 values(root,cur_rev+1,prod.size_id,prod.id,(p->>'reorder_point_pcs')::integer,btrim(p->>'reason'),auth.uid(),p_request,h)returning*into row;
 perform cp7_stock_formula.compute(clock_timestamp(),interval'1 second');
 if cp7_stock_formula.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_FORMULA_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.fg-reorder-manual.v2','replay',false,'root_id',row.root_id,'revision',row.revision,'reorder_point_pcs',row.reorder_point_pcs,
  'evaluation',(select cp7_reorder_caller.wire_row(e.row,(select computed_at from cp7_stock_formula.runs where id))from cp7_reorder_caller.evaluations e where e.root_id=root));
end $$;
