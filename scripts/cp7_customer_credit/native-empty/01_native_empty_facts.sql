-- OUTSIDE PRODUCT. Compose after the frozen coordinator and exact Native
-- transforms, in the same installation transaction. Never install this alone.
do $not_an_installer$begin
 raise exception 'OW04_NATIVE_EMPTY_REQUIRES_ATOMIC_NATIVE_COMPOSITION';
end $not_an_installer$;

-- A Native operation is not a CP7 request. Native's original require_internal /
-- require_owner_admin remain the only admission. These nulls never stand for a
-- generated human UUID or a fabricated CP7 envelope. Existing CP7 row shape and
-- JSON hash codecs are unchanged; no new column is added to a shared fact.
alter table cp7_credit.return_families alter column actor drop not null;
alter table cp7_credit.return_families alter column request_id drop not null;
alter table cp7_credit.return_family_members alter column actor drop not null;
alter table cp7_credit.return_family_members alter column request_id drop not null;
alter table cp7_credit.financial_materializations alter column actor drop not null;
alter table cp7_credit.financial_materializations alter column request_id drop not null;
alter table cp7_credit.return_families add constraint native_or_cp7_assignment check(
 (actor is not null and request_id is not null)or(request_id is null and
  assignment_proof->>'contract_version'is not distinct from'ow04.native-empty-return-family-assignment.v1'));
alter table cp7_credit.return_family_members add constraint native_or_cp7_member check(
 (actor is not null and request_id is not null)or(request_id is null and member_kind='ORIGINAL'));
alter table cp7_credit.financial_materializations add constraint native_or_cp7_marker check(
 (actor is not null and request_id is not null)or(request_id is null and owning_action='NATIVE_EMPTY_RETURN'and request_ordinal=1));

create table cp7_credit.native_empty_work(
 operation_id uuid primary key,backend_pid integer not null,transaction_id bigint not null,
 source_return_id uuid not null unique,source_sale_id uuid not null,
 principal jsonb not null,principal_sha256 text not null,
 source_snapshot jsonb not null,preserved_source jsonb not null,before_events jsonb not null,
 draft_manifest jsonb not null,prior_causal jsonb not null,period_snapshot jsonb not null,
 projected_events jsonb not null,projected_kernel jsonb not null,
 phase text not null check(phase in('ENTERED','GUARDED','REGISTERED')),
 guard_values jsonb,posting_lines jsonb,posting_lines_sha256 text,planned_book_date date,
 family_id uuid,materialization_id uuid,
 unique(backend_pid,transaction_id),
 check(principal_sha256~'^[0-9a-f]{64}$'),
 check(jsonb_typeof(principal)='object'and jsonb_typeof(source_snapshot)='object'
  and jsonb_typeof(preserved_source)='object'and jsonb_typeof(before_events)='array'
  and jsonb_typeof(draft_manifest)='object'and jsonb_typeof(prior_causal)='object'
  and jsonb_typeof(period_snapshot)='object'and jsonb_typeof(projected_events)='array'
  and jsonb_typeof(projected_kernel)='object'),
 check((posting_lines is null)=(posting_lines_sha256 is null)),
 check(phase<>'REGISTERED'or(family_id is not null and materialization_id is not null))
);
create table cp7_credit.native_empty_operations(
 operation_id uuid primary key,source_return_id uuid not null unique references erp.sales_returns(id),
 source_sale_id uuid not null references erp.sales_headers(id),
 family_id uuid not null unique references cp7_credit.return_families(id),
 family_ordinal bigint not null check(family_ordinal>0),backend_pid integer not null,transaction_id bigint not null,
 principal jsonb not null,principal_sha256 text not null,draft_manifest jsonb not null,draft_sha256 text not null,
 source_snapshot jsonb not null,source_sha256 text not null,preserved_source jsonb not null,
 before_events jsonb not null,prior_causal jsonb not null,period_snapshot jsonb not null,
 projected_events jsonb not null,projected_kernel jsonb not null,
 actual_fact jsonb not null,actual_physical jsonb not null,actual_events jsonb not null,actual_kernel jsonb not null,
 actual_original_journal jsonb,assignment_proof jsonb not null,
 materialization_id uuid not null unique,actual_objects jsonb not null,actual_objects_sha256 text not null,
 recorded_at timestamptz not null default statement_timestamp(),
 check(principal_sha256~'^[0-9a-f]{64}$'and draft_sha256~'^[0-9a-f]{64}$'
  and source_sha256~'^[0-9a-f]{64}$'and actual_objects_sha256~'^[0-9a-f]{64}$'),
 check(jsonb_typeof(principal)='object'and jsonb_typeof(draft_manifest)='object'
  and jsonb_typeof(source_snapshot)='object'and jsonb_typeof(preserved_source)='object'
  and jsonb_typeof(before_events)='array'and jsonb_typeof(prior_causal)='object'
  and jsonb_typeof(period_snapshot)='object'and jsonb_typeof(projected_events)='array'
  and jsonb_typeof(projected_kernel)='object'and jsonb_typeof(actual_fact)='object'and jsonb_typeof(actual_physical)='object'
  and jsonb_typeof(actual_events)='array'and jsonb_typeof(actual_kernel)='object'
  and jsonb_typeof(assignment_proof)='object'and jsonb_typeof(actual_objects)='array'),
 check(actual_kernel->>'has_recognition_effect'='false'and actual_kernel->>'net_current_k'='0.00')
);
create table cp7_credit.native_empty_completions(
 operation_id uuid primary key references cp7_credit.native_empty_operations(operation_id),
 final_manifest jsonb not null check(jsonb_typeof(final_manifest)='object'),
 final_manifest_sha256 text not null check(final_manifest_sha256~'^[0-9a-f]{64}$'),
 recorded_at timestamptz not null default statement_timestamp()
);
create table cp7_credit.native_empty_source_scope(
 backend_pid integer not null,transaction_id bigint not null,operation_id uuid not null unique,
 action text not null check(action in('PAYMENT','PAYMENT_REVERSE','RETURN_REVERSE','SALE_REVERSE')),
 source_id uuid not null,source_sale_id uuid not null,principal jsonb not null,
 before_events jsonb not null,source_snapshot jsonb not null,
 primary key(backend_pid,transaction_id)
);
do $protect$declare t text;begin
 foreach t in array array['native_empty_work','native_empty_operations','native_empty_completions','native_empty_source_scope']loop
  execute format('alter table cp7_credit.%I owner to postgres',t);
  execute format('alter table cp7_credit.%I enable row level security',t);
  execute format('create policy deny_direct on cp7_credit.%I for all to public using(false)with check(false)',t);
  execute format('revoke all on cp7_credit.%I from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write',t);
 end loop;
 foreach t in array array['native_empty_operations','native_empty_completions']loop
  execute format('create trigger immutable_row before update or delete on cp7_credit.%I for each row execute function cp7_credit.immutable_fact()',t);
  execute format('create trigger immutable_truncate before truncate on cp7_credit.%I for each statement execute function cp7_credit.immutable_fact()',t);
 end loop;
end $protect$;

-- Observation only, never an alternate permission predicate. auth functions
-- are read when actually present. A database execution with no auth functions
-- retains its real session identity; it is not assigned a synthetic user.
create function cp7_credit.native_empty_principal_v1()returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare uid uuid;jwt_role text;kind text;has_uid boolean;has_jwt boolean;
begin
 has_uid:=to_regprocedure('auth.uid()')is not null;has_jwt:=to_regprocedure('auth.jwt()')is not null;
 if has_uid then execute 'select auth.uid()'into uid;end if;
 if has_jwt then execute 'select auth.jwt()->>''role'''into jwt_role;end if;
 kind:=case when jwt_role='service_role'then'SERVICE_ROLE'
  when jwt_role='authenticated'and uid is not null then'AUTHENTICATED_SUBJECT'
  when uid is null then'DATABASE_SESSION'else'OTHER_NATIVE_PRINCIPAL'end;
 return jsonb_build_object('contract_version','ow04.native-principal-observation.v1','kind',kind,
  'auth_uid',uid,'jwt_role',jwt_role,'session_user',session_user::text,
  'session_role',current_setting('role'),'auth_uid_function_present',has_uid,'auth_jwt_function_present',has_jwt);
end $$;

create function cp7_credit.assert_native_empty_principal_v1(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare uid uuid;kind text;
begin
 if jsonb_typeof(p)is distinct from'object'or not p?&array['contract_version','kind','auth_uid','jwt_role','session_user','session_role',
  'auth_uid_function_present','auth_jwt_function_present']or p-array['contract_version','kind','auth_uid','jwt_role','session_user','session_role',
  'auth_uid_function_present','auth_jwt_function_present']<>'{}'::jsonb
  or p->>'contract_version'is distinct from'ow04.native-principal-observation.v1'
  or nullif(p->>'session_user','')is null or nullif(p->>'session_role','')is null
  or jsonb_typeof(p->'auth_uid_function_present')is distinct from'boolean'
  or jsonb_typeof(p->'auth_jwt_function_present')is distinct from'boolean'then
  raise exception 'CP7_NATIVE_EMPTY_PRINCIPAL_SHAPE';end if;
 uid:=(p->>'auth_uid')::uuid;
 kind:=case when p->>'jwt_role'='service_role'then'SERVICE_ROLE'
  when p->>'jwt_role'='authenticated'and uid is not null then'AUTHENTICATED_SUBJECT'
  when uid is null then'DATABASE_SESSION'else'OTHER_NATIVE_PRINCIPAL'end;
 if p->>'kind'is distinct from kind or not(p->>'auth_uid_function_present')::boolean and uid is not null
  or not(p->>'auth_jwt_function_present')::boolean and p->'jwt_role'<>'null'::jsonb then
  raise exception 'CP7_NATIVE_EMPTY_PRINCIPAL_BINDING';end if;
end $$;

create function cp7_credit.native_empty_draft_v1(p_return uuid)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('contract_version','ow04.native-first-return-input.v1',
  'document',to_jsonb(r)-'status','items',coalesce((select jsonb_agg(jsonb_build_object(
   'id',i.id,'return_id',i.return_id,'sale_stock_allocation_id',i.sale_stock_allocation_id,
   'qty_pcs',i.qty_pcs,'refund_amount',i.refund_amount,'location_id',i.location_id,
   'quality_grade',i.quality_grade,'notes',i.notes)order by i.id)from erp.sales_return_items i where i.return_id=r.id),'[]'))
 from erp.sales_returns r where r.id=p_return
$$;

-- A new ORIGINAL family has no old RETURN ancestor. Only its actual SALE
-- ancestor supplies a causal book floor. Other returns/funding/HPP-sync rows
-- do not move this floor. Completed current-return facts are not called here.
create function cp7_credit.native_empty_prior_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare j erp.journal_entries;n bigint;manifest jsonb;
begin
 select count(*)into n from erp.journal_entries where source_type='SALE'and source_id=p_sale and reversal_of_id is null;
 if n=0 then
  manifest:=jsonb_build_object('contract_version','ow04.native-empty-prior-sale-manifest.v1','sale_id',p_sale,
   'financial_state','NO_JOURNAL','actual_sale_absence',ow04_source_proposal.sale_absence_fact_v1(p_sale));
  return jsonb_build_object('state','PROVEN_ABSENT','causal_book_floor',null,'manifest',manifest,'proof_sha256',ow04_source_proposal.sha(manifest));
 elsif n<>1 then raise exception 'CP7_NATIVE_EMPTY_PRIOR_SALE_JOURNAL_COUNT';end if;
 select *into strict j from erp.journal_entries where source_type='SALE'and source_id=p_sale and reversal_of_id is null;
 manifest:=jsonb_build_object('contract_version','ow04.native-empty-prior-sale-manifest.v1','sale_id',p_sale,
  'financial_state','JOURNAL','actual_sale_journal',cp7_credit.materialized_journal_payload(j.id));
 return jsonb_build_object('state','DATED','causal_book_floor',j.transaction_date,
  'manifest',manifest,'proof_sha256',ow04_source_proposal.sha(manifest));
end $$;

-- Pure support check: later lawful originals/inverses may append to a source,
-- but every actual old support event retains its financial identity and pair.
create function cp7_credit.assert_native_empty_support_v1(p_sale uuid,p_events jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare current_events jsonb;x jsonb;
begin
 current_events:=cp7_credit.initial_base_events_v1(p_sale);
 for x in select value from jsonb_array_elements(p_events)loop
  if not exists(select 1 from jsonb_array_elements(current_events)y where y=x)then
   raise exception 'CP7_NATIVE_EMPTY_ACTUAL_SUPPORT_CHANGED';end if;
 end loop;
end $$;

-- Actual original physical movement proof for BOTH monetary and HPP-only
-- journals as well as NO_JOURNAL. Current lot cost is deliberately not used.
-- A later legal inverse is validated, while the original immutable proof stays
-- byte-for-byte identical. No return item/FG original is synthesized.
create function cp7_credit.native_empty_physical_v1(p_return uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;items jsonb;originals jsonb;allocations jsonb;
begin
 select *into strict r from erp.sales_returns where id=p_return;
 if r.status not in('POSTED','REVERSED')or not exists(select 1 from erp.sales_return_items where return_id=r.id)
  or exists(select 1 from erp.sales_return_items i where i.return_id=r.id and(i.qty_pcs<=0 or i.unit_hpp_snapshot<0
   or not exists(select 1 from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id
    where a.id=i.sale_stock_allocation_id and si.sale_id=r.sale_id and si.product_id=i.product_id
     and a.lot_id is not distinct from i.lot_id and a.qty_pcs>=i.qty_pcs)
   or(select count(*)from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'and m.source_id=i.id and m.reversal_of_id is null)<>1
   or not exists(select 1 from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'and m.source_id=i.id and m.reversal_of_id is null
    and m.movement_type='SALE_RETURN'and m.product_id=i.product_id and m.lot_id is not distinct from i.lot_id and m.location_id=i.location_id
    and m.quality_grade=i.quality_grade and m.customer_id=r.customer_id and m.qty_signed=i.qty_pcs
    and m.unit_hpp_snapshot=i.unit_hpp_snapshot and m.physical_at=r.physical_at)))then
  raise exception 'CP7_NATIVE_EMPTY_ACTUAL_PHYSICAL_PROOF';end if;
 select jsonb_agg(to_jsonb(i)order by i.id)into items from erp.sales_return_items i where i.return_id=r.id;
 select jsonb_agg(to_jsonb(a)order by a.id)into allocations from erp.sale_stock_allocations a
  where exists(select 1 from erp.sales_return_items i where i.return_id=r.id and i.sale_stock_allocation_id=a.id);
 select jsonb_agg(to_jsonb(m)-'book_order'order by m.id)into originals from erp.fg_stock_movements m
  where m.source_type='SALES_RETURN_ITEM'and m.reversal_of_id is null and exists(select 1 from erp.sales_return_items i where i.return_id=r.id and i.id=m.source_id);
 if exists(select 1 from jsonb_array_elements(originals)x where
  (r.status='POSTED'and exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid))
  or(r.status='REVERSED'and((select count(*)from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid)<>1
   or not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid
    and rv.source_type='FG_MOVEMENT_REVERSAL'and rv.source_id=(x->>'id')::uuid and rv.movement_type='REVERSAL'
    and rv.product_id=(x->>'product_id')::uuid and rv.lot_id is not distinct from(x->>'lot_id')::uuid
    and rv.location_id=(x->>'location_id')::uuid and rv.quality_grade=x->>'quality_grade'
    and rv.qty_signed=-(x->>'qty_signed')::integer and rv.unit_hpp_snapshot=(x->>'unit_hpp_snapshot')::numeric
    and rv.customer_id is not distinct from(x->>'customer_id')::uuid and rv.physical_at>=(x->>'physical_at')::timestamptz))))then
  raise exception 'CP7_NATIVE_EMPTY_ACTUAL_STOCK_INVERSE_PROOF';end if;
 return jsonb_build_object('contract_version','ow04.native-empty-original-physical.v1','return_id',r.id,
  'items',items,'actual_original_fg_movements',originals,'actual_allocations',allocations);
end $$;

create function cp7_credit.verify_native_empty_member_v1(p_return uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.native_empty_operations;f cp7_credit.return_families;m cp7_credit.return_family_members;
 r erp.sales_returns;fact jsonb;assignment jsonb;expected jsonb;fresh jsonb;prior jsonb;previous uuid;n bigint;floor date;book date;uid uuid;
begin
 select *into strict o from cp7_credit.native_empty_operations where source_return_id=p_return;
 select *into strict f from cp7_credit.return_families where id=o.family_id;
 select *into strict m from cp7_credit.return_family_members where return_id=p_return;
 select *into strict r from erp.sales_returns where id=p_return;
 perform cp7_credit.assert_native_empty_principal_v1(o.principal);uid:=(o.principal->>'auth_uid')::uuid;
 if o.principal_sha256 is distinct from ow04_source_proposal.sha(o.principal)
  or o.draft_sha256 is distinct from ow04_source_proposal.sha(o.draft_manifest)
  or o.source_sha256 is distinct from ow04_source_proposal.sha(o.source_snapshot)
  or f.assignment_kind<>'NEW_POST'or f.first_return_id<>p_return or f.family_root_sale_id<>o.source_sale_id
  or f.family_ordinal<>o.family_ordinal or r.sale_id<>o.source_sale_id or m.family_id<>f.id
  or m.member_kind<>'ORIGINAL'or f.actor is distinct from uid or m.actor is distinct from uid
  or f.request_id is not null or m.request_id is not null
  or exists(select 1 from cp7_credit.cohorts where family_id=f.id)
  or(select count(*)from cp7_credit.return_family_members where family_id=f.id)<>1 then
  raise exception 'CP7_NATIVE_EMPTY_OPERATION_MEMBER_BINDING';end if;
 if exists(select 1 from(select family_ordinal,row_number()over(order by family_ordinal)n
  from cp7_credit.return_families where family_root_sale_id=o.source_sale_id)v where v.family_ordinal<>v.n)then
  raise exception 'CP7_NATIVE_EMPTY_ORDINAL_CHAIN';end if;
 select id into previous from cp7_credit.return_families where family_root_sale_id=o.source_sale_id and family_ordinal=f.family_ordinal-1;
 assignment:=jsonb_build_object('contract_version','ow04.native-empty-return-family-assignment.v1','origin','NATIVE_RETURN',
  'operation_id',o.operation_id,'family_id',f.id,'family_root_sale_id',o.source_sale_id,'family_ordinal',f.family_ordinal::text,
  'first_return_id',p_return,'previous_family_id',previous,'principal_sha256',o.principal_sha256,'source_sha256',o.source_sha256);
 if f.assignment_proof is distinct from assignment or o.assignment_proof is distinct from assignment
  or f.source_sha256 is distinct from ow04_source_proposal.sha(assignment)then raise exception 'CP7_NATIVE_EMPTY_ASSIGNMENT_CHANGED';end if;
 fact:=ow04_source_proposal.return_fact_v1(p_return);
 if fact is distinct from o.actual_fact or cp7_credit.native_empty_draft_v1(p_return)is distinct from o.draft_manifest
  or cp7_credit.native_empty_physical_v1(p_return)is distinct from o.actual_physical then
  raise exception 'CP7_NATIVE_EMPTY_ACTUAL_RETURN_CHANGED';end if;
 expected:=jsonb_build_object('contract_version','ow04.actual-return-family-member.v1','family_id',f.id,'family_root_sale_id',o.source_sale_id,
  'return_id',p_return,'sale_id',o.source_sale_id,'member_kind','ORIGINAL','predecessor_return_id',null,'native_lineage_id',null,
  'return_item_lineage','{}'::jsonb,'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','no_journal_proof',fact->'no_journal_proof');
 if m.actual_lineage_snapshot is distinct from expected or m.source_sha256 is distinct from ow04_source_proposal.sha(expected)
  or m.financial_state is distinct from fact->>'financial_state'or m.source_journal_id is distinct from(fact->>'source_journal_id')::uuid
  or m.financial_source_proof is distinct from fact->'no_journal_proof'then raise exception 'CP7_NATIVE_EMPTY_MEMBER_SOURCE_CHANGED';end if;
 prior:=cp7_credit.native_empty_prior_v1(o.source_sale_id);
 if prior is distinct from o.prior_causal or prior->>'proof_sha256'is distinct from ow04_source_proposal.sha(prior->'manifest')then
  raise exception 'CP7_NATIVE_EMPTY_CAUSAL_SOURCE_CHANGED';end if;
 floor:=(prior->>'causal_book_floor')::date;
 if fact->>'financial_state'='JOURNAL'then
  if o.actual_original_journal is distinct from cp7_credit.materialized_journal_payload((fact->>'source_journal_id')::uuid)then
   raise exception 'CP7_NATIVE_EMPTY_ACTUAL_JOURNAL_CHANGED';end if;
  book:=(o.actual_original_journal#>>'{journal,transaction_date}')::date;
  if book<greatest((r.physical_at at time zone'Asia/Jakarta')::date,floor)then raise exception 'CP7_NATIVE_EMPTY_CAUSAL_BOOK_FLOOR';end if;
 elsif o.actual_original_journal is not null then raise exception 'CP7_NATIVE_EMPTY_NO_JOURNAL_IS_NOT_NULL';end if;
 perform cp7_credit.assert_zero_excess_v1(o.before_events);
 perform cp7_credit.assert_zero_excess_v1(o.before_events||o.actual_events);
 fresh:=ow04_pure_kernel.recognition_plan_v1(o.before_events,o.actual_events);
 if fresh is distinct from o.actual_kernel or(fresh->>'has_recognition_effect')::boolean
  or fresh->>'net_current_k'<>'0.00'or(o.projected_kernel->>'has_recognition_effect')::boolean
  or o.projected_kernel->'components'is distinct from fresh->'components'then
  raise exception 'CP7_NATIVE_EMPTY_RECOGNITION_NOT_EMPTY';end if;
 perform cp7_credit.assert_native_empty_support_v1(o.source_sale_id,o.before_events||o.actual_events);
 return jsonb_build_object('contract_version','ow04.verified-return-member.v1','family_id',f.id,'family_root_sale_id',o.source_sale_id,
  'family_ordinal',f.family_ordinal::text,'return_id',p_return,'sale_id',o.source_sale_id,'member_kind','ORIGINAL',
  'predecessor_return_id',null,'native_lineage_id',null,'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','member_sha256',m.source_sha256,'registration_sha256',f.source_sha256,
  'causal_book_floor',greatest(floor,book),'native_operation_id',o.operation_id,'principal_kind',o.principal->'kind');
end $$;

create function cp7_credit.assert_native_empty_provenance_v1(p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare marker_id uuid;o cp7_credit.native_empty_operations;f cp7_credit.financial_materializations;objects jsonb;
begin
 for marker_id in select value::uuid from jsonb_array_elements_text(p_actual->'materialization_ids')loop
  select *into f from cp7_credit.financial_materializations where id=marker_id;
  select *into o from cp7_credit.native_empty_operations where materialization_id=marker_id;
  if o.operation_id is null and f.owning_action<>'NATIVE_EMPTY_RETURN'then continue;end if;
  if o.operation_id is null or f.id is null then raise exception 'CP7_NATIVE_EMPTY_MATERIALIZATION_UNOWNED';end if;
  perform cp7_credit.verify_native_empty_member_v1(o.source_return_id);
  select jsonb_agg(x order by x->>'object_kind'collate"C",x->>'object_id'collate"C")into objects from(
   select cp7_credit.materialized_fact('FAMILY',rf.id,to_jsonb(rf))x from cp7_credit.return_families rf where rf.id=o.family_id
   union all select cp7_credit.materialized_fact('MEMBER',m.return_id,to_jsonb(m))from cp7_credit.return_family_members m where m.return_id=o.source_return_id)s;
  if(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.owning_action,f.payload_sha256,f.source_plan_sha256)is distinct from
   (o.source_sale_id,(o.principal->>'auth_uid')::uuid,null::uuid,1::bigint,'NATIVE_EMPTY_RETURN',o.draft_sha256,ow04_source_proposal.sha(o.actual_kernel))
   or o.actual_objects is distinct from objects or f.actual_objects is distinct from objects
   or o.actual_objects_sha256 is distinct from ow04_source_proposal.sha(objects)
   or f.actual_objects_sha256 is distinct from ow04_source_proposal.sha(objects)then
   raise exception 'CP7_NATIVE_EMPTY_MATERIALIZATION_CHANGED';end if;
 end loop;
end $$;

create function cp7_credit.without_native_empty_markers_v1(p_actual jsonb)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_set(p_actual,'{materialization_ids}',coalesce((select jsonb_agg(v order by v::text)from jsonb_array_elements(p_actual->'materialization_ids')v
  where not exists(select 1 from cp7_credit.native_empty_operations o where o.materialization_id=(v#>>'{}')::uuid)),'[]'))
$$;
