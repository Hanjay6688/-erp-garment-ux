-- SOURCE-ONLY outside active product. The missing source/coordinator verifiers
-- and owning materializer are explicit blockers, never permissive stubs.
do $not_an_installer$begin
 raise exception 'OW04_MATERIALIZED_PROFILE_REQUIRES_COMPLETE_OWNING_INTEGRATION';
end $not_an_installer$;

-- A DATA-COMPLETENESS fact, not authority, outer response or a session context.
-- A private owning coordinator must derive the exact objects from actual rows
-- after all journals exist; it cannot accept this manifest from a client. Final
-- deferred closure separately verifies owning-operation provenance/completion,
-- outer receipt, final status,
-- cash/daily/profile checks and no ephemeral scopes at COMMIT.
create table cp7_credit.financial_materializations(
 id uuid primary key,root_sale_id uuid not null references erp.sales_headers(id),
 actor uuid not null,request_id uuid not null,request_ordinal bigint not null check(request_ordinal>0),
 owning_action text not null,payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 source_plan_sha256 text not null check(source_plan_sha256~'^[0-9a-f]{64}$'),
 actual_objects jsonb not null check(jsonb_typeof(actual_objects)='array'),
 actual_objects_sha256 text not null check(actual_objects_sha256~'^[0-9a-f]{64}$'),
 recorded_at timestamptz not null default statement_timestamp(),
 unique(actor,request_id,request_ordinal)
);
create table cp7_credit.financial_materialization_objects(
 object_kind text not null check(object_kind in('FAMILY','MEMBER','COHORT','PLAN','COMPONENT','PART','PART_JOURNAL','CONSUMPTION')),
 object_id uuid not null,materialization_id uuid not null references cp7_credit.financial_materializations(id),
 fact_sha256 text not null check(fact_sha256~'^[0-9a-f]{64}$'),
 primary key(object_kind,object_id)
);
alter table cp7_credit.financial_materializations owner to postgres;
alter table cp7_credit.financial_materialization_objects owner to postgres;
do $protect_materialization$declare t text;begin
 foreach t in array array['financial_materializations','financial_materialization_objects']loop
  execute format('alter table cp7_credit.%I enable row level security',t);
  execute format('create policy no_direct_access on cp7_credit.%I for all to public using(false)with check(false)',t);
  execute format('create trigger immutable_row before update or delete on cp7_credit.%I for each row execute function cp7_credit.immutable_fact()',t);
  execute format('create trigger immutable_truncate before truncate on cp7_credit.%I for each statement execute function cp7_credit.immutable_fact()',t);
 end loop;
end $protect_materialization$;
revoke all on cp7_credit.financial_materializations,cp7_credit.financial_materialization_objects
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

create function cp7_credit.materialized_fact(p_kind text,p_id uuid,p_payload jsonb)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select jsonb_build_object('object_kind',p_kind,'object_id',p_id,'fact_sha256',cp7_credit.pg_jsonb_sha256(p_payload))
$$;
create function cp7_credit.materialized_journal_payload(p_id uuid)returns jsonb
language sql stable security definer set search_path='' set TimeZone='UTC' as $$
 select jsonb_build_object('journal',to_jsonb(j)-'status','lines',coalesce(
  (select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where l.journal_entry_id=j.id),'[]'))
 from erp.journal_entries j where j.id=p_id
$$;

-- Derives actual objects WITHOUT accepting any marker or pending-plan filter.
-- Public current reader never calls this alone. Owning materializer may use it
-- to derive data BEFORE inserting the protected fact; no command authority is
-- conferred. Native/BB account lineage, source-target arithmetic and ownership
-- are additional verifiers below, not a boolean in a supplied JSON manifest.
create function cp7_credit.current_materialized_objects(p_sale uuid,p_root uuid,p_leaf uuid)returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare a record;m record;f record;c record;p record;cc record;q record;e record;o record;j erp.journal_entries;
 roots uuid[];next_roots uuid[];sales uuid[];cohorts uuid[];part_ids uuid[]:='{}';journal_ids uuid[]:='{}';
 customer uuid;v_root uuid;v_leaf uuid;objects jsonb:='[]';components jsonb;parts jsonb;canonical jsonb;
 expected_lines jsonb;actual_lines jsonb;state jsonb;v_i numeric:=0;v_u numeric:=0;n bigint;v_sum numeric;
begin
 select *into strict a from cp7_credit.current_leaf_assignment(p_sale);
 if(a.root_sale_id,a.current_leaf_id)is distinct from(p_root,p_leaf)
  or p_sale<>p_leaf or a.requested_status not in('POSTED','PARTIAL_PAID','PAID')then
  raise exception 'CP7_CREDIT_CURRENT_ASSIGNMENT_CHANGED';end if;
 customer:=a.customer_id;roots:=array[p_root];
 -- Include complete upstream credit source roots for incoming APPLY, including
 -- restores/historical target headers. UUID ordering is for normalization only.
 loop
  select array_agg(distinct id order by id)into sales from(
   select unnest(roots)id union select x.previous_sale_id from cp7_note.revisions x where x.root_sale_id=any(roots)
   union select x.replacement_sale_id from cp7_note.revisions x where x.root_sale_id=any(roots))s;
  select array_agg(distinct id order by id)into next_roots from(
   select unnest(roots)id union select rf.family_root_sale_id from cp7_credit.consumption_events ce
    join cp7_credit.cohorts ch on ch.id=ce.cohort_id join cp7_credit.return_families rf on rf.id=ch.family_id
    where ce.event_kind='APPLY'and ce.target_sale_id=any(sales))s;
  exit when next_roots is not distinct from roots;roots:=next_roots;
 end loop;
 foreach v_root in array roots loop
  select *into strict m from cp7_credit.current_leaf_assignment(v_root);
  if m.root_sale_id<>v_root or m.customer_id is distinct from customer then raise exception 'CP7_CREDIT_MEMBER_ROOT_MISMATCH';end if;
  v_leaf:=m.current_leaf_id;
  if exists(select 1 from erp.sales_headers h where(h.id=v_root or exists(select 1 from cp7_note.revisions x
   where x.root_sale_id=v_root and h.id in(x.previous_sale_id,x.replacement_sale_id)))
   and h.status in('POSTED','PARTIAL_PAID','PAID')and h.id<>v_leaf)then
   raise exception 'CP7_CREDIT_CURRENT_ASSIGNMENT_CHANGED';end if;
 end loop;
 if exists(select 1 from erp.sales_returns r where r.sale_id=any(sales)and r.status<>'DRAFT'
  and not exists(select 1 from cp7_credit.return_family_members mm where mm.return_id=r.id))then
  raise exception 'CP7_CREDIT_RETURN_REGISTRATION_INCOMPLETE';end if;
 if exists(select 1 from cp7_credit.return_family_members mm join erp.sales_returns r on r.id=mm.return_id
  join cp7_credit.return_families ff on ff.id=mm.family_id where r.sale_id=any(sales)and not ff.family_root_sale_id=any(roots))then
  raise exception 'CP7_CREDIT_MEMBER_ROOT_MISMATCH';end if;
 if exists(select 1 from(select family_ordinal,row_number()over(partition by family_root_sale_id order by family_ordinal)n
  from cp7_credit.return_families where family_root_sale_id=any(roots))x where x.family_ordinal<>x.n)then
  raise exception 'CP7_CREDIT_RETURN_REGISTRATION_INCOMPLETE';end if;
 for f in select *from cp7_credit.return_families where family_root_sale_id=any(roots)order by family_root_sale_id,family_ordinal loop
  if not exists(select 1 from cp7_credit.return_family_members mm where mm.family_id=f.id and mm.return_id=f.first_return_id
   and mm.member_kind='ORIGINAL')then raise exception 'CP7_CREDIT_RETURN_REGISTRATION_INCOMPLETE';end if;
  objects:=objects||jsonb_build_array(cp7_credit.materialized_fact('FAMILY',f.id,to_jsonb(f)));
  for m in select mm.*,r.sale_id,r.customer_id,r.status,r.physical_at from cp7_credit.return_family_members mm
   join erp.sales_returns r on r.id=mm.return_id where mm.family_id=f.id order by mm.return_id loop
   if not m.sale_id=any(sales)or m.customer_id is distinct from customer or m.status not in('POSTED','REVERSED')then
    raise exception 'CP7_CREDIT_MEMBER_ROOT_MISMATCH';end if;
   select *into strict a from cp7_credit.current_leaf_assignment(m.sale_id);
   if a.root_sale_id is distinct from f.family_root_sale_id then raise exception 'CP7_CREDIT_MEMBER_ROOT_MISMATCH';end if;
   if m.financial_state='JOURNAL'then
    if m.source_journal_id is null or not exists(select 1 from erp.journal_entries jj where jj.id=m.source_journal_id
     and jj.source_type='SALES_RETURN'and jj.source_id=m.return_id and jj.reversal_of_id is null
     and jj.economic_date=(m.physical_at at time zone'Asia/Jakarta')::date
     and jj.transaction_date>=jj.economic_date and jj.status=case when m.status='REVERSED'then'REVERSED'else'POSTED'end)
     or(select count(*)from erp.journal_entries jj where jj.source_type='SALES_RETURN'and jj.source_id=m.return_id
      and jj.reversal_of_id is null)<>1 then raise exception 'CP7_CREDIT_MEMBER_JOURNAL_MISMATCH';end if;
   elsif m.financial_state='NO_JOURNAL'then
    if m.source_journal_id is not null or exists(select 1 from erp.journal_entries jj where jj.source_type='SALES_RETURN'and jj.source_id=m.return_id)
     or not exists(select 1 from erp.sales_return_items ri where ri.return_id=m.return_id)
     or exists(select 1 from erp.sales_return_items ri where ri.return_id=m.return_id and(ri.qty_pcs<=0 or ri.refund_amount<>0 or ri.unit_hpp_snapshot<>0
      or not exists(select 1 from erp.sale_stock_allocations sa join erp.sales_items si on si.id=sa.sale_item_id
       where sa.id=ri.sale_stock_allocation_id and si.sale_id=m.sale_id and si.product_id=ri.product_id
        and sa.lot_id is not distinct from ri.lot_id and sa.qty_pcs>=ri.qty_pcs)
      or(select count(*)from erp.fg_stock_movements fm where fm.source_type='SALES_RETURN_ITEM'and fm.source_id=ri.id and fm.reversal_of_id is null)<>1
      or not exists(select 1 from erp.fg_stock_movements fm where fm.source_type='SALES_RETURN_ITEM'and fm.source_id=ri.id
       and fm.reversal_of_id is null and fm.movement_type='SALE_RETURN'and fm.product_id=ri.product_id
       and fm.lot_id is not distinct from ri.lot_id and fm.location_id=ri.location_id and fm.quality_grade=ri.quality_grade
       and fm.qty_signed=ri.qty_pcs and fm.unit_hpp_snapshot=0 and fm.customer_id=customer and fm.physical_at=m.physical_at)))then
     raise exception 'CP7_CREDIT_NO_JOURNAL_SOURCE_CHANGED';end if;
   else raise exception 'CP7_CREDIT_MEMBER_JOURNAL_MISMATCH';end if;
   objects:=objects||jsonb_build_array(cp7_credit.materialized_fact('MEMBER',m.return_id,
    (select to_jsonb(mm)from cp7_credit.return_family_members mm where mm.return_id=m.return_id)));
  end loop;
 end loop;
 select coalesce(array_agg(ch.id order by ch.id),'{}')into cohorts from cp7_credit.cohorts ch
  join cp7_credit.return_families ff on ff.id=ch.family_id where ff.family_root_sale_id=any(roots);
 for c in select ch.*,ff.family_root_sale_id from cp7_credit.cohorts ch join cp7_credit.return_families ff on ff.id=ch.family_id
  where ch.id=any(cohorts)order by ch.id loop
  if c.customer_id is distinct from customer or c.ar_account_id=c.credit_account_id or not exists(
   select 1 from cp7_credit.return_family_members mm join erp.sales_returns r on r.id=mm.return_id
   where mm.return_id=c.source_return_id and mm.family_id=c.family_id and r.sale_id=c.source_sale_id
    and(mm.financial_state,mm.source_journal_id,mm.financial_source_proof)is not distinct from
     (c.source_return_financial_state,c.source_return_journal_id,c.source_return_financial_proof))
   or not exists(select 1 from erp.journal_entries sj where sj.id=c.source_sale_journal_id and sj.source_type='SALE'
    and sj.source_id=c.source_sale_id and sj.reversal_of_id is null and sj.status in('POSTED','REVERSED'))then
   raise exception 'CP7_CREDIT_COHORT_SOURCE_MISMATCH';end if;
  objects:=objects||jsonb_build_array(cp7_credit.materialized_fact('COHORT',c.id,to_jsonb(c)-'family_root_sale_id'));
  if(select count(*)from cp7_credit.recognition_plans pp where pp.cohort_id=c.id and pp.plan_kind='INITIAL')<>1
   or not exists(select 1 from cp7_credit.recognition_plans pp where pp.id=c.initial_plan_id and pp.cohort_id=c.id
    and pp.plan_kind='INITIAL'and pp.net_amount=c.initial_net_amount and pp.expected_component_count>0)then
   raise exception 'CP7_CREDIT_PLAN_COHORT_MISMATCH';end if;
  for p in select *from cp7_credit.recognition_plans where cohort_id=c.id order by id loop
   if p.family_root_sale_id is distinct from c.family_root_sale_id or(p.plan_kind='INITIAL')<>(p.id=c.initial_plan_id)then
    raise exception 'CP7_CREDIT_PLAN_COHORT_MISMATCH';end if;
   select count(*),coalesce(sum(z.amount),0),coalesce(jsonb_agg(jsonb_build_object('amount',cp7_credit.cent_text(z.amount),
    'economic_date',z.economic_date::text,'transaction_date',z.transaction_date::text,
    'previous_economic_date',z.previous_economic_date::text,'previous_transaction_date',z.previous_transaction_date::text,
    'corners',z.corners)order by z.ordinal),'[]')into n,v_sum,components from cp7_credit.recognition_components z where z.plan_id=p.id;
   if n<>p.expected_component_count or cp7_credit.pg_jsonb_sha256(components)is distinct from p.components_sha256_pg
    or exists(select 1 from(select ordinal,row_number()over(order by ordinal)n from cp7_credit.recognition_components where plan_id=p.id)x where x.ordinal<>x.n)then
    raise exception 'CP7_CREDIT_COMPONENT_MANIFEST_CHANGED';end if;
   if v_sum is distinct from p.net_amount or p.has_recognition_effect is distinct from(n>0)then raise exception 'CP7_CREDIT_PLAN_TOTAL_CHANGED';end if;
   objects:=objects||jsonb_build_array(cp7_credit.materialized_fact('PLAN',p.id,to_jsonb(p)));
   select coalesce(jsonb_agg(jsonb_build_object('id',qq.id,'component_id',z.id,'ordinal',qq.ordinal,'amount',cp7_credit.cent_text(qq.amount))
    order by z.ordinal,qq.ordinal),'[]')into parts from cp7_credit.recognition_components z join cp7_credit.component_parts qq on qq.component_id=z.id where z.plan_id=p.id;
   if jsonb_array_length(parts)::bigint is distinct from p.expected_part_count or cp7_credit.pg_jsonb_sha256(parts)is distinct from p.parts_sha256_pg then
    raise exception 'CP7_CREDIT_PART_MANIFEST_CHANGED';end if;
   for cc in select *from cp7_credit.recognition_components where plan_id=p.id order by ordinal loop
    canonical:=components->(cc.ordinal-1);
    if cc.kernel_component is distinct from canonical or cc.component_sha256_pg is distinct from cp7_credit.pg_jsonb_sha256(canonical)
     or cc.amount is distinct from((cc.corners->>'d_here')::numeric-(cc.corners->>'d_prev_economic')::numeric
      -(cc.corners->>'d_prev_transaction')::numeric+(cc.corners->>'d_prev_both')::numeric)then
     raise exception 'CP7_CREDIT_COMPONENT_MANIFEST_CHANGED';end if;
    select count(*),sum(qq.amount)into n,v_sum from cp7_credit.component_parts qq where qq.component_id=cc.id;
    if n::numeric<>ceil(abs(cc.amount)/cp7_credit.native_journal_cent_max())or v_sum is distinct from cc.amount then
     raise exception 'CP7_CREDIT_PART_MANIFEST_CHANGED';end if;
    objects:=objects||jsonb_build_array(cp7_credit.materialized_fact('COMPONENT',cc.id,to_jsonb(cc)));
    for q in select *from cp7_credit.component_parts where component_id=cc.id order by ordinal loop
     if q.ordinal<1 or q.ordinal>n or q.amount is distinct from sign(cc.amount)*least(cp7_credit.native_journal_cent_max(),
      abs(cc.amount)-(q.ordinal-1)*cp7_credit.native_journal_cent_max())then raise exception 'CP7_CREDIT_PART_MANIFEST_CHANGED';end if;
     part_ids:=part_ids||q.id;
     select *into o from cp7_credit.component_journals where part_id=q.id;
     if o.part_id is null then raise exception 'CP7_CREDIT_PART_JOURNAL_INCOMPLETE';end if;
     select *into j from erp.journal_entries where id=o.journal_id;
     if j.id is null or(j.source_type,j.source_id,j.economic_date,j.transaction_date,j.reversal_of_id)is distinct from
      ('CP7_CUSTOMER_CREDIT_RECOGNITION',q.id,cc.economic_date,cc.transaction_date,null::uuid)
      or(o.economic_date,o.transaction_date)is distinct from(cc.economic_date,cc.transaction_date)
      or j.status not in('POSTED','REVERSED')then raise exception 'CP7_CREDIT_PART_JOURNAL_CHANGED';end if;
     if j.status='REVERSED'or exists(select 1 from erp.journal_entries jj where jj.reversal_of_id=j.id
      or(jj.source_type='JOURNAL_REVERSAL'and jj.source_id=j.id))then
      raise exception 'CP7_CREDIT_UNREPRESENTED_RECOGNITION_INVERSE';end if;
     expected_lines:=cp7_credit.native_cent_lines(jsonb_build_array(
      jsonb_build_object('account_id',c.ar_account_id,'customer_id',c.customer_id,'description','OW04 source-bound recognition',
       'debit',case when q.amount>0 then q.amount else 0 end,'credit',case when q.amount<0 then-q.amount else 0 end),
      jsonb_build_object('account_id',c.credit_account_id,'customer_id',c.customer_id,'description','OW04 source-bound recognition',
       'debit',case when q.amount<0 then-q.amount else 0 end,'credit',case when q.amount>0 then q.amount else 0 end)));
     select coalesce(jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,'description',l.description,
      'debit',l.debit,'credit',l.credit)order by case when l.account_id=c.ar_account_id then 0 else 1 end,l.id),'[]')into actual_lines
      from erp.journal_lines l where l.journal_entry_id=j.id;
     if actual_lines is distinct from expected_lines or o.lines_sha256_pg is distinct from cp7_credit.native_lines_sha256(actual_lines)
      or exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and
       (l.vendor_id is not null or l.contractor_id is not null or l.po_id is not null or l.product_id is not null))then
      raise exception 'CP7_CREDIT_PART_LINES_CHANGED';end if;
     journal_ids:=journal_ids||j.id;
     if c.family_root_sale_id=p_root then v_i:=v_i+q.amount;end if;
     objects:=objects||jsonb_build_array(cp7_credit.materialized_fact('PART',q.id,to_jsonb(q)),
      cp7_credit.materialized_fact('PART_JOURNAL',q.id,jsonb_build_object('link',to_jsonb(o),'actual',cp7_credit.materialized_journal_payload(j.id))));
    end loop;
   end loop;
  end loop;
 end loop;
 -- All signed consumers of upstream cohorts are included; restores are real
 -- linked facts, not a filter which drops the original consumption.
 for e in select *from cp7_credit.consumption_events where cohort_id=any(cohorts)order by id loop
  select *into strict c from cp7_credit.cohorts where id=e.cohort_id;
  if e.event_kind='APPLY'and not exists(select 1 from erp.sales_headers h where h.id=e.target_sale_id and h.customer_id=c.customer_id)then
   raise exception 'CP7_CREDIT_CONSUMPTION_TARGET_CHANGED';end if;
  select *into j from erp.journal_entries where id=e.journal_id;
  if j.id is null or(j.economic_date,j.transaction_date)is distinct from(e.economic_date,e.transaction_date)
   or j.status not in('POSTED','REVERSED')then raise exception 'CP7_CREDIT_CONSUMPTION_JOURNAL_CHANGED';end if;
  if e.amount<0 then
   select *into o from cp7_credit.consumption_events where id=e.restores_event_id;
   if o.id is null or o.amount<=0 or(e.cohort_id,e.event_kind,e.target_sale_id,e.cash_account_id,e.amount)is distinct from
    (o.cohort_id,o.event_kind,o.target_sale_id,o.cash_account_id,-o.amount)
    or e.economic_date<o.economic_date or e.transaction_date<o.transaction_date then
    raise exception 'CP7_CREDIT_CONSUMPTION_RESTORE_CHANGED';end if;
   if j.source_type='JOURNAL_REVERSAL'and(j.source_id is distinct from o.journal_id or j.reversal_of_id is distinct from o.journal_id
    or not exists(select 1 from erp.journal_entries oj where oj.id=o.journal_id and oj.status='REVERSED'))then
    raise exception 'CP7_CREDIT_CONSUMPTION_RESTORE_CHANGED';end if;
  end if;
  -- Posting source-ID protocol and full account/line/capacity proof are NOT
  -- invented here: the exact actual payload goes to the source-plan verifier.
  if exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(l.debit<0 or l.credit<0
   or l.debit::text in('NaN','Infinity','-Infinity')or l.credit::text in('NaN','Infinity','-Infinity')))
   or not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id group by l.journal_entry_id
   having sum(l.debit)=sum(l.credit)and sum(l.debit)>0)then raise exception 'CP7_CREDIT_CONSUMPTION_JOURNAL_CHANGED';end if;
  journal_ids:=journal_ids||j.id;
  if e.event_kind='APPLY'and e.target_sale_id=p_sale then v_u:=v_u+e.amount;end if;
  objects:=objects||jsonb_build_array(cp7_credit.materialized_fact('CONSUMPTION',e.id,
   jsonb_build_object('event',to_jsonb(e),'actual',cp7_credit.materialized_journal_payload(j.id))));
 end loop;
 if exists(select 1 from erp.journal_entries jj where jj.source_type in('CP7_CUSTOMER_CREDIT_RECOGNITION','CP7_CUSTOMER_CREDIT_APPLY',
  'CP7_CUSTOMER_CREDIT_REFUND','CP7_CUSTOMER_CREDIT_EVENT_REVERSE')and
  ((jj.source_id=any(part_ids)and not jj.id=any(journal_ids))or
   (exists(select 1 from erp.journal_lines l where l.journal_entry_id=jj.id and l.customer_id=customer)
    and not exists(select 1 from cp7_credit.component_journals cj where cj.journal_id=jj.id)
    and not exists(select 1 from cp7_credit.consumption_events ce where ce.journal_id=jj.id))))then
   raise exception 'CP7_CREDIT_UNREGISTERED_FINANCIAL_JOURNAL';end if;
 select coalesce(jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C"),'[]')into objects from jsonb_array_elements(objects)x;
 state:=jsonb_build_object('contract_version','ow04.actual-materialized-objects.v1','sale_id',p_sale,'root_sale_id',p_root,'current_leaf_id',p_leaf,
  'upstream_root_ids',roots,'actual_objects',objects,'actual_objects_sha256',cp7_credit.pg_jsonb_sha256(objects),
  'I',cp7_credit.cent_text(v_i),'U',cp7_credit.cent_text(v_u),'adjustment',cp7_credit.cent_text(v_u-v_i),
  'source_authority_proven',false,'financial_marker_verified',false,'consumption_posting_contract_proven',false);
 return state;
end $$;

create function cp7_credit.inspect_current_materialized_profile(p_sale uuid,p_root uuid,p_leaf uuid)returns jsonb
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare actual jsonb;x jsonb;b record;f record;ids uuid[]:='{}';manifest jsonb;
begin
 actual:=cp7_credit.current_materialized_objects(p_sale,p_root,p_leaf);
 for x in select value from jsonb_array_elements(actual->'actual_objects')loop
  select *into b from cp7_credit.financial_materialization_objects where object_kind=x->>'object_kind'and object_id=(x->>'object_id')::uuid;
  if b.object_id is null then raise exception 'CP7_CREDIT_FINANCIAL_MATERIALIZATION_INCOMPLETE';end if;
  if b.fact_sha256 is distinct from x->>'fact_sha256'then raise exception 'CP7_CREDIT_FINANCIAL_MATERIALIZATION_CHANGED';end if;
  if not b.materialization_id=any(ids)then ids:=ids||b.materialization_id;end if;
 end loop;
 for f in select *from cp7_credit.financial_materializations where id=any(ids)loop
  select coalesce(jsonb_agg(jsonb_build_object('object_kind',o.object_kind,'object_id',o.object_id,'fact_sha256',o.fact_sha256)
   order by o.object_kind collate"C",o.object_id::text collate"C"),'[]')into manifest
   from cp7_credit.financial_materialization_objects o where o.materialization_id=f.id;
  if manifest is distinct from f.actual_objects or cp7_credit.pg_jsonb_sha256(manifest)is distinct from f.actual_objects_sha256 then
   raise exception 'CP7_CREDIT_FINANCIAL_MATERIALIZATION_CHANGED';end if;
 end loop;
 if(select count(*)from cp7_credit.financial_materializations where id=any(ids))<>cardinality(ids)then
  raise exception 'CP7_CREDIT_FINANCIAL_MATERIALIZATION_INCOMPLETE';end if;
 return actual||jsonb_build_object('financial_marker_verified',true,'financial_data_complete',true,
  'materialization_ids',ids,'source_authority_proven',false);
end $$;

-- Concrete replacement of 01's always-refusing placeholder. No verifier below
-- is installed as a stub returning OK. An absent owning interface is explicit
-- refusal even when every local mechanical/materialization test succeeds.
create or replace function cp7_credit.assert_current_materialized_profile(p_sale uuid,p_root uuid,p_leaf uuid)returns void
language plpgsql stable security definer set search_path='' set TimeZone='UTC' as $$
declare actual jsonb;x jsonb;
begin
 actual:=cp7_credit.inspect_current_materialized_profile(p_sale,p_root,p_leaf);
 if to_regprocedure('ow04_source_proposal.verify_return_member_v1(uuid)')is null then
  raise exception 'CP7_CREDIT_CURRENT_SOURCE_VERIFIER_UNAVAILABLE'using detail='Exact STABLE immutable Native member proof is unavailable';end if;
 for x in select value from jsonb_array_elements(actual->'actual_objects')where value->>'object_kind'='MEMBER'loop
  -- The separate source proposal is pure Native/member proof: no current-E,
  -- materialization callback or lock acquisition, so this has no cycle.
  execute 'select ow04_source_proposal.verify_return_member_v1($1)'using(x->>'object_id')::uuid;
 end loop;
 if to_regprocedure('cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)')is null then
  raise exception 'CP7_CREDIT_CURRENT_SOURCE_VERIFIER_UNAVAILABLE'using detail='Complete actual source/ordinal target/I/C reconciliation is unavailable';end if;
 -- Owning STABLE source verifier: pure exact return_member proof, authoritative
 -- ordinal/replay membership; full actual original/inverse/restatement sources;
 -- ALL retained I/C vs ordinal target at every joint prefix; account/source-ID
 -- posting/capacity protocols, upstream dependencies and no unbound inverse.
 execute 'select cp7_credit.assert_current_source_plan_profile($1,$2,$3,$4)'using p_sale,p_root,p_leaf,actual;
 if to_regprocedure('cp7_credit.assert_financial_materialization_provenance(jsonb)')is null then
  raise exception 'CP7_CREDIT_CURRENT_COORDINATOR_VERIFIER_UNAVAILABLE';end if;
 -- Protected coordinator provenance/actual request+manifest binding, NOT outer
 -- response or scopes-cleared. Those are mandatory separately at COMMIT.
 execute 'select cp7_credit.assert_financial_materialization_provenance($1)'using actual;
end $$;
alter function cp7_credit.materialized_fact(text,uuid,jsonb)owner to postgres;
alter function cp7_credit.materialized_journal_payload(uuid)owner to postgres;
alter function cp7_credit.current_materialized_objects(uuid,uuid,uuid)owner to postgres;
alter function cp7_credit.inspect_current_materialized_profile(uuid,uuid,uuid)owner to postgres;
alter function cp7_credit.assert_current_materialized_profile(uuid,uuid,uuid)owner to postgres;
revoke all on function cp7_credit.materialized_fact(text,uuid,jsonb),cp7_credit.materialized_journal_payload(uuid),
 cp7_credit.current_materialized_objects(uuid,uuid,uuid),cp7_credit.inspect_current_materialized_profile(uuid,uuid,uuid),
 cp7_credit.assert_current_materialized_profile(uuid,uuid,uuid)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
