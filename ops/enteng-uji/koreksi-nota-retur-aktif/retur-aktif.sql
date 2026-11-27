do $note_catalog$
declare actual_ jsonb;
begin
  if session_user<>'postgres' or current_user<>'postgres' or current_setting('is_superuser')<>'off' or to_regnamespace('cp7_note_replay') is not null
     or pg_has_role('postgres','cp7_sales_write','SET') or pg_has_role('postgres','cp7_sales_write','USAGE')
     or has_schema_privilege('postgres','cp7_note','CREATE') then raise exception 'Unexpected authority or note namespace'; end if;
  select coalesce(jsonb_object_agg(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))),'{}')
    into actual_ from pg_proc p join pg_namespace ns on ns.oid=p.pronamespace
    where ns.nspname='cp7_note_replay' or p.oid::regprocedure::text in (select jsonb_object_keys('{"cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)":"8011f1995b6249d5d72fa98910c2bda3","cp7_credit.assert_financial_materialization_provenance(jsonb)":"d7a4811567bdcd49786d99329943cb78","cp7_credit.assert_initial_return_closed_v1(uuid)":"bf3e85df164913ba6a10e3d90a0c9b0c","cp7_credit.enforce_initial_return_closure_v1()":"83c81c2e61101e21296cf6a3a3db752b","cp7_note.command(jsonb,uuid,text)":"0712b785c0d44b46878e2cca642be71f","erp.post_sales_return(uuid)":"9341d82b8266d306b6db9cc6dd784495"}'::jsonb));
  if actual_ is distinct from '{"cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)":"8011f1995b6249d5d72fa98910c2bda3","cp7_credit.assert_financial_materialization_provenance(jsonb)":"d7a4811567bdcd49786d99329943cb78","cp7_credit.assert_initial_return_closed_v1(uuid)":"bf3e85df164913ba6a10e3d90a0c9b0c","cp7_credit.enforce_initial_return_closure_v1()":"83c81c2e61101e21296cf6a3a3db752b","cp7_note.command(jsonb,uuid,text)":"0712b785c0d44b46878e2cca642be71f","erp.post_sales_return(uuid)":"9341d82b8266d306b6db9cc6dd784495"}'::jsonb then raise exception 'The installed note, return or credit functions differ from the qualified source'; end if;
end $note_catalog$;
create schema cp7_note_replay authorization postgres;
revoke all on schema cp7_note_replay from public,anon,authenticated,service_role;

create table cp7_note_replay.work (
  pid integer not null, tx bigint not null, actor uuid not null, request_id uuid not null,
  correction uuid primary key, old_sale uuid not null, gross numeric(20,2) not null,
  expected text not null, payload_sha text not null, access_snapshot jsonb not null,
  previous_objects jsonb not null, original_returns jsonb not null, expected_events jsonb not null,
  replacements jsonb not null default '[]', pending jsonb,
  unique(pid,tx),unique(actor,request_id)
);
create table cp7_note_replay.receipts (
  correction uuid primary key references cp7_note.revisions(id),
  root_sale uuid not null unique, new_sale uuid not null unique,
  actor uuid not null, request_id uuid not null, request_digest text not null,
  endpoint_receipt jsonb not null, return_links jsonb not null, profile_digest text not null,
  new_objects jsonb not null, dated_events jsonb not null, source_digest text not null, unique(actor,request_id)
);
alter table cp7_note_replay.work enable row level security;
alter table cp7_note_replay.receipts enable row level security;
revoke all on cp7_note_replay.work,cp7_note_replay.receipts from public,anon,authenticated,service_role;
create trigger immutable_row before update or delete on cp7_note_replay.receipts for each row execute function cp7_credit.immutable_fact();
create trigger immutable_truncate before truncate on cp7_note_replay.receipts for each statement execute function cp7_credit.immutable_fact();

create function cp7_note_replay.dated_totals(events jsonb) returns jsonb language sql immutable set search_path='' as $fn$
  select coalesce(jsonb_agg(jsonb_build_array(kind,economic,book,amount) order by kind collate "C",economic,book),'[]')
  from (select e->>'kind' as kind,(e->>'economic_date')::date as economic,
               (e->>'transaction_date')::date as book,sum((e->>'amount')::numeric) as amount
        from jsonb_array_elements(events) e group by 1,2,3 having sum((e->>'amount')::numeric)<>0) g
$fn$;

create function cp7_note_replay.begin_replay(p jsonb, request uuid, p_expected_version text, correction_id uuid, access_state jsonb)
returns boolean language plpgsql volatile set search_path='' as $fn$
declare sale uuid:=(p->>'sale_id')::uuid; h erp.sales_headers; original jsonb; proposed jsonb;
  profile jsonb; ret jsonb; sale_event text; original_count int; gross numeric; active jsonb;
begin
  if not exists (select 1 from erp.sales_returns where sale_id=sale and status='POSTED') then return false; end if;
  if exists(select 1 from cp7_note.revisions where sale in(root_sale_id,previous_sale_id,replacement_sale_id))
     or exists(select 1 from cp7_credit.cohorts c join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=sale)
     or exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY' and target_sale_id=sale)
     or exists(select 1 from erp.sales_returns where sale_id=sale and status<>'POSTED')
     or exists(select 1 from cp7_sales_return_correction.links where sale_id=sale)
     or exists(select 1 from erp.sales_payments p0 where p0.sale_id=sale and (p0.status<>'POSTED' or p0.replaces_payment_id is not null))
     or exists(select 1 from erp.sales_payments p0 join erp.initial_import_prepayment_payments a on a.payment_id=p0.id where p0.sale_id=sale)
     or cp7_mandor_shop.invoice_offset_paid(sale)<>0 then return false; end if;
  select * into strict h from erp.sales_headers where id=sale;
  if (h.row_version::text,cp7_sales.review_token(sale),cp7_note.access_now()) is distinct from(p_expected_version,p->>'review_token',access_state)
     or not exists(select 1 from cp7_note.requests q where q.actor=auth.uid() and q.request_id=request
          and q.payload=p and q.expected_version=p_expected_version and q.response is null) then raise exception 'CP7_NOTE_REPLAY_REVIEW_CHANGED'; end if;
  original_count:=(select count(*) from erp.sales_returns where sale_id=sale and status='POSTED');
  select jsonb_agg(jsonb_build_object('old',r.id,'family',m.family_id,'operation',m.operation_id) order by r.id) into active
    from erp.sales_returns r join cp7_credit.initial_return_materializations m on m.source_return_id=r.id and m.source_sale_id=sale and m.origin='ORDINARY'
    join cp7_credit.return_family_members fm on fm.return_id=r.id and fm.family_id=m.family_id and fm.member_kind='ORIGINAL'
    where r.sale_id=sale and r.status='POSTED';
  if coalesce(jsonb_array_length(active),0)<>original_count then return false; end if;
  perform cp7_credit.assert_current_materialized_profile(sale,sale,sale);
  profile:=cp7_credit.current_materialized_objects(sale,sale,sale);
  for ret in select value from jsonb_array_elements(active) loop
    perform cp7_credit.assert_initial_return_closed_v1((ret->>'operation')::uuid);
    perform ow04_source_proposal.verify_return_member_v1((ret->>'old')::uuid);
  end loop;
  original:=ow04_source_proposal.locked_source_family(sale);
  if original->>'source_status'<>'BASE_COLLECTED' or original->'blockers'<>'[]'::jsonb then raise exception 'CP7_NOTE_REPLAY_BASE_DOCUMENTS_INCOMPLETE'; end if;
  select b->>'id' into strict sale_event from jsonb_array_elements(original->'event_bindings') b
    where b->>'document_kind'='SALE' and b->>'role'='ORIGINAL' and (b->>'document_id')::uuid=sale;
  select sum(round((i->>'qty_pcs')::numeric*(i->>'unit_price_snapshot')::numeric-coalesce((i->>'discount_amount')::numeric,0),2))
    into gross from jsonb_array_elements(p->'items') i;
  if gross is null or gross<0 then raise exception 'CP7_NOTE_REPLAY_INVALID_TOTAL'; end if;
  select jsonb_agg(case when e->>'id'=sale_event then jsonb_set(e,'{amount}',to_jsonb(cp7_credit.cent_text(gross))) else e end order by e->>'id')
    into proposed from jsonb_array_elements(original->'events') e;
  perform cp7_credit.assert_zero_excess_v1(original->'events');
  -- The dated projection is compared with actual journals and checked by the kernel in finish.
  insert into cp7_note_replay.work(pid,tx,actor,request_id,correction,old_sale,gross,expected,payload_sha,access_snapshot,previous_objects,original_returns,expected_events)
    values(pg_backend_pid(),txid_current(),auth.uid(),request,correction_id,sale,gross,p_expected_version,cp7_credit.pg_jsonb_sha256(p),access_state,profile->'actual_objects',active,cp7_note_replay.dated_totals(proposed));
  return true;
end $fn$;

create function cp7_note_replay.work_for(p_return uuid) returns cp7_note_replay.work language plpgsql stable set search_path='' as $fn$
declare w cp7_note_replay.work;
begin
  select * into strict w from cp7_note_replay.work where pid=pg_backend_pid() and tx=txid_current() and actor=auth.uid();
  if w.pending is null or (w.pending->>'new')::uuid is distinct from p_return
     or cp7_note.access_now() is distinct from w.access_snapshot
     or not exists(select from cp7_note.context where backend_pid=w.pid and transaction_id=w.tx and actor=w.actor and source_sale_id=w.old_sale)
     or not exists(select from cp7_sales.command_context where backend_pid=w.pid and transaction_id=w.tx and actor=w.actor and sale_id=w.old_sale and action='SALE_REVERSE')
     or not exists(select from cp7_note.requests q where q.actor=w.actor and q.request_id=w.request_id and q.response is null
                and q.expected_version=w.expected and cp7_credit.pg_jsonb_sha256(q.payload)=w.payload_sha) then
      raise exception 'CP7_NOTE_REPLAY_SOURCE_CONTEXT_CHANGED'; end if;
  return w;
end $fn$;

create function cp7_note_replay.bind_return(p_old uuid,p_new uuid, p_sale uuid, item_map jsonb) returns void language plpgsql set search_path='' as $fn$
declare w cp7_note_replay.work; row_ jsonb; lineage jsonb; old_ erp.sales_returns; new_ erp.sales_returns;
begin
  select * into strict w from cp7_note_replay.work where pid=pg_backend_pid() and tx=txid_current() and actor=auth.uid();
  select value into strict row_ from jsonb_array_elements(w.original_returns) where (value->>'old')::uuid=p_old;
  select * into strict old_ from erp.sales_returns where id=p_old and sale_id=w.old_sale and status='REVERSED';
  select * into strict new_ from erp.sales_returns where id=p_new and sale_id=p_sale and status='DRAFT';
  if w.pending is not null or p_sale=w.old_sale or exists(select from jsonb_array_elements(w.replacements) v where (v->>'old')::uuid=p_old or (v->>'new')::uuid=p_new)
   or (new_.physical_at,new_.customer_id,new_.notes) is distinct from(old_.physical_at,old_.customer_id,old_.notes) then raise exception 'CP7_NOTE_REPLAY_WRONG_RETURN'; end if;
  select jsonb_object_agg(i.id::text,item_map->i.id::text) into lineage from erp.sales_return_items i where i.return_id=p_new;
  if lineage is null then raise exception 'CP7_NOTE_REPLAY_EMPTY_RETURN'; end if;
  if (select count(*) from erp.sales_return_items where return_id=p_old)<>(select count(*) from jsonb_each(lineage)) or
     exists(select from jsonb_each_text(lineage) a join erp.sales_return_items n on n.id=a.key::uuid
       left join erp.sales_return_items o on o.id=a.value::uuid and o.return_id=p_old
       where o.id is null or (n.product_id,n.lot_id,n.location_id,n.quality_grade,n.qty_pcs,n.refund_amount,n.notes)
       is distinct from(o.product_id,o.lot_id,o.location_id,o.quality_grade,o.qty_pcs,o.refund_amount,o.notes)) or
     (select count(distinct value) from jsonb_each_text(lineage))<>(select count(*) from jsonb_each(lineage)) then
     raise exception 'CP7_NOTE_REPLAY_ITEM_SOURCE_CHANGED'; end if;
  update cp7_note_replay.work set pending=row_||jsonb_build_object('new',p_new,'sale',p_sale,'items',lineage) where correction=w.correction;
  perform cp7_note_replay.work_for(p_new);
end $fn$;

create function cp7_note_replay.checked_paid(p_return uuid,refund numeric,net numeric,posted_paid numeric,already_posted boolean)
returns numeric language plpgsql stable set search_path='' as $fn$
declare w cp7_note_replay.work; sale uuid; exact_refund numeric; exact_net numeric; funded numeric;
begin
  w:=cp7_note_replay.work_for(p_return);
  sale:=(w.pending->>'sale')::uuid;
  select sum(refund_amount) into exact_refund from erp.sales_return_items where return_id=(w.pending->>'old')::uuid;
  select w.gross-coalesce(sum(i.refund_amount),0)-exact_refund into exact_net from erp.sales_returns r join erp.sales_return_items i on i.return_id=r.id
       where r.sale_id=sale and r.id<>p_return and r.status='POSTED';
  select coalesce(sum(amount),0) into funded from erp.sales_payments where sale_id=sale and status='POSTED';
  if not exists(select from erp.sales_returns where id=p_return and sale_id=sale and status=case when already_posted then 'POSTED' else 'DRAFT' end)
    or (refund,net) is distinct from(exact_refund,exact_net) or (posted_paid is not null and posted_paid<>funded)
    or funded>exact_net or funded<0 or (select sum(line_total) from erp.sales_items where sale_id=sale) is distinct from w.gross then
       raise exception 'CP7_NOTE_REPLAY_NATIVE_TOTALS_CHANGED'; end if;
  return funded;
end $fn$;

create function cp7_note_replay.post_journal(kind text,p_return uuid,economic date,description text,lines jsonb)
returns uuid language plpgsql set search_path='' as $fn$
declare w cp7_note_replay.work; old_j erp.journal_entries; new_j erp.journal_entries; journal_id uuid;
begin
  w:=cp7_note_replay.work_for(p_return);
  select * into strict old_j from erp.journal_entries where source_type='SALES_RETURN' and source_id=(w.pending->>'old')::uuid and reversal_of_id is null and status='REVERSED';
  if kind<>'SALES_RETURN' or economic<>old_j.economic_date or exists(select from erp.journal_entries where source_type=kind and source_id=p_return) then
      raise exception 'CP7_NOTE_REPLAY_JOURNAL_SOURCE_CHANGED'; end if;
  journal_id:=erp.post_journal(kind,p_return,economic,description,lines);
  select * into strict new_j from erp.journal_entries where id=journal_id;
  if (new_j.source_type,new_j.source_id,new_j.economic_date,new_j.transaction_date,new_j.status) is distinct from
     (kind,p_return,old_j.economic_date,old_j.transaction_date,'POSTED'::text)
    or ow04_source_proposal.line_vector(new_j.id,false) is distinct from ow04_source_proposal.line_vector(old_j.id,false) then
       raise exception 'CP7_NOTE_REPLAY_RETURN_JOURNAL_CHANGED'; end if;
  return new_j.id;
end $fn$;

create function cp7_note_replay.keep_link(p_return uuid) returns void language plpgsql set search_path='' as $fn$
declare w cp7_note_replay.work;
begin
  w:=cp7_note_replay.work_for(p_return);
  if not exists(select from erp.sales_returns where id=p_return and status='POSTED' and sale_id=(w.pending->>'sale')::uuid) then raise exception 'CP7_NOTE_REPLAY_RETURN_POST_NOT_COMPLETE'; end if;
  update cp7_note_replay.work set replacements=replacements||jsonb_build_array(pending),pending=null where correction=w.correction;
end $fn$;
create function cp7_note_replay.finish(p_response jsonb) returns void language plpgsql set search_path='' as $fn$
declare w cp7_note_replay.work; link jsonb; fact jsonb; member jsonb; src jsonb; profile jsonb; added jsonb; entry jsonb; new_sale uuid:=(p_response->>'sale_id')::uuid;
begin
  select * into strict w from cp7_note_replay.work where pid=pg_backend_pid() and tx=txid_current() and actor=auth.uid();
  if w.pending is not null or jsonb_array_length(w.replacements)<>jsonb_array_length(w.original_returns)
     or cp7_note.access_now() is distinct from w.access_snapshot
     or (p_response->>'revision_id')::uuid is distinct from w.correction
     or not exists(select from cp7_note.revisions v where (v.id,v.root_sale_id,v.previous_sale_id,v.replacement_sale_id,v.actor,v.request_id)
        is not distinct from(w.correction,w.old_sale,w.old_sale,new_sale,w.actor,w.request_id))
     or not exists(select from cp7_note.requests q where q.actor=w.actor and q.request_id=w.request_id and cp7_credit.pg_jsonb_sha256(q.payload)=w.payload_sha and q.response=p_response)
      then raise exception 'CP7_NOTE_REPLAY_NOTE_RECEIPT_CHANGED'; end if;
  for link in select value from jsonb_array_elements(w.replacements) loop
    fact:=ow04_source_proposal.return_fact_v1((link->>'new')::uuid);
    if (fact->>'sale_id',fact->>'family_root_sale_id') is distinct from (new_sale::text,w.old_sale::text)
       or (link->>'sale')::uuid<>new_sale then raise exception 'CP7_NOTE_REPLAY_MEMBER_SALE_CHANGED'; end if;
    member:=jsonb_build_object('contract_version','ow04.actual-return-family-member.v1','family_id',link->'family',
       'family_root_sale_id',w.old_sale,'return_id',link->'new','sale_id',new_sale,'member_kind','NOTE_REPLAY',
       'predecessor_return_id',link->'old','native_lineage_id',w.correction,'return_item_lineage',link->'items',
       'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
       'financial_source_sha256',fact->'financial_source_sha256','no_journal_proof',fact->'no_journal_proof');
    insert into cp7_credit.return_family_members(family_id,return_id,member_kind,source_journal_id,source_sha256,actual_lineage_snapshot,actor,request_id,financial_state,financial_source_proof)
      values((link->>'family')::uuid,(link->>'new')::uuid,'NOTE_REPLAY',(fact->>'source_journal_id')::uuid,ow04_source_proposal.sha(member),member,w.actor,w.request_id,fact->>'financial_state',fact->'no_journal_proof');
    perform ow04_source_proposal.verify_return_member_v1((link->>'new')::uuid);
  end loop;
  src:=ow04_source_proposal.locked_source_family(new_sale);
  if src->>'source_status' is distinct from 'BASE_COLLECTED' or src->'blockers' is distinct from '[]'::jsonb
    or cp7_note_replay.dated_totals(src->'events') is distinct from w.expected_events then raise exception 'CP7_NOTE_REPLAY_SETTLEMENT_DATES_CHANGED'; end if;
  perform cp7_credit.assert_zero_excess_v1(src->'events');
  profile:=cp7_credit.current_materialized_objects(new_sale,w.old_sale,new_sale);
  if (profile->>'I')::numeric<>0 or (profile->>'U')::numeric<>0 or (profile->>'adjustment')::numeric<>0
     or profile->'upstream_root_ids' is distinct from jsonb_build_array(w.old_sale)
     or not (profile->'actual_objects' @> w.previous_objects) then raise exception 'CP7_NOTE_REPLAY_PROTECTED_FACTS_CHANGED'; end if;
  select coalesce(jsonb_agg(v order by v->>'object_kind' collate "C",v->>'object_id' collate "C"),'[]') into added
     from jsonb_array_elements(profile->'actual_objects') v where not exists(select from jsonb_array_elements(w.previous_objects) old where old=v);
  if jsonb_array_length(added)<>jsonb_array_length(w.replacements)
     or exists(select from jsonb_array_elements(added) o where o->>'object_kind'<>'MEMBER' or not exists(
         select from jsonb_array_elements(w.replacements) l where l->>'new'=o->>'object_id'))
     or exists(select from jsonb_array_elements(added) o join cp7_credit.financial_materialization_objects old
         on old.object_kind=o->>'object_kind' and old.object_id=(o->>'object_id')::uuid) then raise exception 'CP7_NOTE_REPLAY_MANIFEST_CHANGED'; end if;
  insert into cp7_credit.financial_materializations(id,root_sale_id,actor,request_id,request_ordinal,owning_action,payload_sha256,source_plan_sha256,actual_objects,actual_objects_sha256)
     values(w.correction,w.old_sale,w.actor,w.request_id,1,'NOTE_REPLAY',w.payload_sha,src->>'state_sha256',added,cp7_credit.pg_jsonb_sha256(added));
  for entry in select value from jsonb_array_elements(added) loop
     insert into cp7_credit.financial_materialization_objects(object_kind,object_id,materialization_id,fact_sha256)
        values(entry->>'object_kind',(entry->>'object_id')::uuid,w.correction,entry->>'fact_sha256');
  end loop;
  insert into cp7_note_replay.receipts(correction,root_sale,new_sale,actor,request_id,request_digest,endpoint_receipt,return_links,profile_digest,new_objects,dated_events,source_digest)
     values(w.correction,w.old_sale,new_sale,w.actor,w.request_id,w.payload_sha,p_response,w.replacements,cp7_credit.pg_jsonb_sha256(profile),added,w.expected_events,src->>'state_sha256');
  delete from cp7_note_replay.work where correction=w.correction;
end $fn$;

create function cp7_note_replay.owned_leaf(root uuid,operation uuid) returns uuid language sql stable set search_path='' as $fn$
  select r.new_sale from cp7_note_replay.receipts r join cp7_note.revisions v on v.id=r.correction
  join cp7_note.requests q on q.actor=r.actor and q.request_id=r.request_id and q.response=r.endpoint_receipt and cp7_credit.pg_jsonb_sha256(q.payload)=r.request_digest
  where r.root_sale=root and v.root_sale_id=root and v.previous_sale_id=root and v.replacement_sale_id=r.new_sale
    and v.actor=r.actor and v.request_id=r.request_id and not exists(select from cp7_note.revisions n where n.previous_sale_id=r.new_sale)
    and exists(select from jsonb_array_elements(r.return_links) l
        join cp7_credit.initial_return_materializations m on m.operation_id=operation and m.source_return_id=(l->>'old')::uuid and m.family_id=(l->>'family')::uuid
        join cp7_credit.return_family_members fm on fm.return_id=(l->>'new')::uuid and fm.family_id=m.family_id and fm.member_kind='NOTE_REPLAY'
        where (l->>'operation')::uuid=operation and m.source_sale_id=root and m.origin='ORDINARY')
$fn$;

create function cp7_note_replay.assert_marker(marker uuid) returns void language plpgsql stable set search_path='' as $fn$
declare r cp7_note_replay.receipts; m cp7_credit.financial_materializations; l jsonb; actual jsonb;
begin
  select * into strict r from cp7_note_replay.receipts where correction=marker;
  select * into strict m from cp7_credit.financial_materializations where id=marker;
  if (m.root_sale_id,m.actor,m.request_id,m.request_ordinal,m.owning_action,m.payload_sha256,m.source_plan_sha256,m.actual_objects,m.actual_objects_sha256)
     is distinct from (r.root_sale,r.actor,r.request_id,1,'NOTE_REPLAY',r.request_digest,r.source_digest,r.new_objects,cp7_credit.pg_jsonb_sha256(r.new_objects)) then raise exception 'CP7_NOTE_REPLAY_MARKER_CHANGED'; end if;
  select coalesce(jsonb_agg(jsonb_build_object('object_kind',o.object_kind,'object_id',o.object_id,'fact_sha256',o.fact_sha256) order by o.object_kind collate "C",o.object_id::text collate "C"),'[]')
     into actual from cp7_credit.financial_materialization_objects o where o.materialization_id=marker;
  if actual is distinct from r.new_objects then raise exception 'CP7_NOTE_REPLAY_MARKER_OBJECT_CHANGED'; end if;
  for l in select value from jsonb_array_elements(r.return_links) loop
     if cp7_note_replay.owned_leaf(r.root_sale,(l->>'operation')::uuid) is distinct from r.new_sale then raise exception 'CP7_NOTE_REPLAY_MARKER_OWNER_CHANGED'; end if;
     perform ow04_source_proposal.verify_return_member_v1((l->>'new')::uuid);
  end loop;
end $fn$;

create function cp7_note_replay.assert_profile(sale uuid,root uuid,leaf uuid,actual jsonb) returns void language plpgsql stable set search_path='' as $fn$
declare r cp7_note_replay.receipts; l jsonb; fresh jsonb;
begin
  select * into strict r from cp7_note_replay.receipts where root_sale=root and new_sale=leaf;
  if sale<>leaf or (actual->>'sale_id',actual->>'root_sale_id',actual->>'current_leaf_id') is distinct from (sale::text,root::text,leaf::text)
    then raise exception 'CP7_NOTE_REPLAY_CURRENT_LEAF_CHANGED'; end if;
  fresh:=cp7_credit.current_materialized_objects(sale,root,leaf);
  if cp7_credit.pg_jsonb_sha256(fresh)<>r.profile_digest or (actual-'materialization_ids'-'financial_data_complete'-'financial_marker_verified'-'source_authority_proven')
      is distinct from (fresh-'materialization_ids'-'financial_data_complete'-'financial_marker_verified'-'source_authority_proven')
      then raise exception 'CP7_NOTE_REPLAY_CURRENT_CREDIT_PROFILE_CHANGED'; end if;
  for l in select value from jsonb_array_elements(r.return_links) loop
    if cp7_note_replay.owned_leaf(root,(l->>'operation')::uuid) is distinct from leaf then raise exception 'CP7_NOTE_REPLAY_OWNER_LINK_CHANGED'; end if;
    perform ow04_source_proposal.verify_return_member_v1((l->>'new')::uuid);
  end loop;
end $fn$;

create function cp7_note_replay.closed_work() returns trigger language plpgsql set search_path='' as $fn$
begin
  if exists(select from cp7_note_replay.work where correction=new.correction)
     or not exists(select from cp7_note_replay.receipts where correction=new.correction and actor=new.actor and request_id=new.request_id)
       then raise exception 'CP7_NOTE_REPLAY_UNFINISHED_OPERATION'; end if;
  return null;
end $fn$;
create constraint trigger completed_note after insert or update on cp7_note_replay.work deferrable initially deferred for each row execute function cp7_note_replay.closed_work();
revoke all on all functions in schema cp7_note_replay from public,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION cp7_note_replay.post_return(p_return_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'erp', 'public'
AS $function$
declare
  h erp.sales_returns%rowtype;
  s erp.sales_headers%rowtype;
  r record;
  v_refund numeric(24,6):=0;
  v_sold_qty integer;
  v_prior_returned integer;
  v_current_return integer;
  v_product_sale_value numeric(24,6);
  v_prior_product_refund numeric(24,6);
  v_current_product_refund numeric(24,6);
  v_original_hpp numeric(18,6);
  v_unit_hpp numeric(18,6);
  v_net_total numeric(20,2);
  v_paid numeric(20,2);
  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_delta_other numeric(24,6);
  v_target_hpp numeric(24,6);
  v_target_other numeric(24,6);
  v_book_hpp numeric(24,6);
  v_book_other numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  perform erp.require_internal();
  perform cp7_note_replay.work_for(p_return_id);
  perform erp.require_internal();
  select * into h from erp.sales_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sales return must be DRAFT'; end if;
  if h.sale_id is null then raise exception 'Native sales return must reference the original sale'; end if;
  select * into s from erp.sales_headers where id=h.sale_id for update;
  if s.id is null or s.status not in('POSTED','PARTIAL_PAID','PAID') then raise exception 'Original sale must be active/posted'; end if;
  if s.customer_id is distinct from h.customer_id then raise exception 'Sales return customer does not match original sale customer'; end if;
  if not exists(select 1 from erp.sales_return_items where return_id=h.id) then raise exception 'Sales return has no lines'; end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  for r in
    select * from erp.sales_return_items where return_id=h.id
    order by product_id,location_id,quality_grade,lot_id,id
  loop
    if r.lot_id is null then raise exception 'Sales return line requires original FG lot'; end if;
    if not exists(select 1 from erp.fg_lots fl where fl.id=r.lot_id and fl.product_id=r.product_id) then raise exception 'Sales return lot does not belong to selected product'; end if;

    insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
    values(r.product_id,r.location_id,r.quality_grade,0)
    on conflict(product_id,location_id,quality_grade) do nothing;
    perform 1 from erp.fg_inventory_balances
    where product_id=r.product_id and location_id=r.location_id and quality_grade=r.quality_grade
    for update;
    perform 1 from erp.fg_lots where id=r.lot_id for update;

    -- Eligibility belongs to the selected allocation. Receipt destination is
    -- independently validated and may be another active FG warehouse.
    select a.qty_pcs,a.unit_hpp_snapshot into v_sold_qty,v_original_hpp
    from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id
    where a.id=r.sale_stock_allocation_id and si.sale_id=h.sale_id
      and si.product_id=r.product_id and a.lot_id=r.lot_id;
    if v_sold_qty is null or v_sold_qty<=0 or v_original_hpp is null then
      raise exception 'AH_RETURN_ALLOCATION_SOURCE_MISMATCH';
    end if;

    v_unit_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.lot_id),v_original_hpp);
    select coalesce(sum(sri.qty_pcs),0)::integer into v_prior_returned
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED'
      and sri.sale_stock_allocation_id=r.sale_stock_allocation_id;
    select coalesce(sum(sri.qty_pcs),0)::integer into v_current_return
    from erp.sales_return_items sri
    where sri.return_id=h.id and sri.sale_stock_allocation_id=r.sale_stock_allocation_id;
    if v_prior_returned+v_current_return>v_sold_qty then
      raise exception 'AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION: Sales return exceeds quantity originally sold for this allocation. Sold %, prior returned %, current return %',v_sold_qty,v_prior_returned,v_current_return;
    end if;

    select coalesce(sum(si.line_total),0) into v_product_sale_value
    from erp.sales_items si where si.sale_id=h.sale_id and si.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_prior_product_refund
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED' and sri.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_current_product_refund
    from erp.sales_return_items sri where sri.return_id=h.id and sri.product_id=r.product_id;
    if v_prior_product_refund+v_current_product_refund>v_product_sale_value then
      raise exception 'Refund exceeds original net sale value for product. Sold value %, prior refund %, current refund %',v_product_sale_value,v_prior_product_refund,v_current_product_refund;
    end if;

    update erp.sales_return_items set unit_hpp_snapshot=v_unit_hpp where id=r.id;
    perform erp.post_fg_movement(r.product_id,r.lot_id,r.location_id,r.quality_grade,
      'SALE_RETURN',r.qty_pcs,v_unit_hpp,h.customer_id,'SALES_RETURN_ITEM',r.id,
      h.physical_at,'Customer sales return',false);
    v_refund:=v_refund+r.refund_amount;
  end loop;

  select greatest(erp.sale_net_total(h.sale_id)-v_refund,0)::numeric(20,2) into v_net_total;
  select coalesce(sum(sp.amount),0)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.sale_id and sp.status='POSTED';
  v_paid:=cp7_note_replay.checked_paid(h.id,v_refund,v_net_total,v_paid,false);
  if v_paid>v_net_total then
    raise exception 'Retur ini membuat pembayaran customer melebihi nilai penjualan tersisa. Nilai setelah retur %, sudah dibayar %. Reverse/koreksi pembayaran customer dulu agar kelebihan bayar tidak hilang dari pembukuan.',v_net_total,v_paid;
  end if;

  update erp.sales_returns set status='POSTED' where id=h.id;
  if abs(v_refund)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',round(v_refund,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',round(v_refund,2),'customer_id',h.customer_id));
  end if;

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    select round(t.fg_value-b.fg_value,2),
      round(t.cogs_value-b.cogs_value,2),
      round(t.other_out_value-b.other_out_value,2)
    into v_delta_fg,v_delta_cogs,v_delta_other
    from erp.compute_non_po_product_hpp_targets_v2620f(r.product_id) t
    cross join lateral erp.compute_non_po_product_hpp_book_v2620f(r.product_id) b;
    if abs(v_delta_fg+v_delta_cogs+v_delta_other)>0.005 then
      raise exception 'Return non-PO HPP delta does not conserve source value for product %: fg %, cogs %, other %',
        r.product_id,v_delta_fg,v_delta_cogs,v_delta_other;
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0
        then jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,
          'credit',abs(v_delta_fg),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0
        then jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,
          'credit',abs(v_delta_cogs),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0
        then jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,
          'credit',0,'customer_id',h.customer_id,'product_id',r.product_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,
          'credit',abs(v_delta_other),'customer_id',h.customer_id,
          'product_id',r.product_id) end);
    end if;
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select
      round(coalesce(t.cogs_value,0),2)-st.cogs_value,
      round(coalesce(t.fg_value,0),2)-st.fg_value,
      (round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)
        -round(coalesce(t.cogs_value,0),2))-st.other_out_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      st.hpp_total_cost,st.other_out_value
    into v_delta_cogs,v_delta_fg,v_delta_other,
      v_target_hpp,v_target_other,v_book_hpp,v_book_other
    from erp.po_hpp_gl_state st
    cross join lateral erp.compute_po_hpp_gl_targets_v2620d(r.po_id) t
    where st.po_id=r.po_id for update of st;
    if v_delta_cogs>0.005 or v_delta_fg<-0.005
       or abs(v_delta_cogs+v_delta_fg+v_delta_other)>0.005
       or v_target_hpp is distinct from v_book_hpp then
      raise exception 'Sales-return cumulative HPP target does not conserve PO value %. dc %, df %, do %, target/book hpp %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_delta_other,v_target_hpp,v_book_hpp;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0 then
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0 then
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_delta_fg),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0 then
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_delta_other),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform cp7_note_replay.post_journal('SALES_RETURN',h.id,(h.physical_at AT TIME ZONE 'Asia/Jakarta')::date,
      'Sales return from customer · cumulative exact HPP target',v_lines);
  end if;
  perform cp7_credit.flush_opening_return_hpp_v1(h.id);
  v_paid:=cp7_note_replay.checked_paid(h.id,v_refund,v_net_total,null,true);
  perform erp.require_internal();

  for r in
    select distinct fl.product_id
    from erp.sales_return_items i
    join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is null
    order by fl.product_id
  loop
    perform erp.assert_non_po_product_hpp_target_book_v2620f(r.product_id);
  end loop;

  update erp.sales_headers
  set status=case when v_paid=v_net_total then 'PAID' when v_paid>0 and v_paid<v_net_total then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.sale_id;
  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620e(r.po_id);
  end loop;
  perform cp7_note_replay.keep_link(h.id);
  perform erp.require_internal();
end
$function$
;
revoke all on function cp7_note_replay.post_return(uuid) from public,anon,authenticated,service_role;

grant cp7_sales_write to postgres with inherit false,set true granted by postgres;
set local role cp7_sales_write;
grant create on schema cp7_note to postgres;
reset role;
CREATE OR REPLACE FUNCTION cp7_note.command(p_payload jsonb, p_request uuid, p_expected text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare a jsonb;old cp7_note.requests%rowtype;h erp.sales_headers%rowtype;root uuid;leaf uuid;
 revision bigint;replaced uuid;native_request uuid;result jsonb;draft jsonb;line jsonb;payment record;returned record;
 paid jsonb;returns jsonb;returned_lines jsonb;new_payment uuid;new_return uuid;new_return_item uuid;allocation uuid;
 return_lineage jsonb:='{}'::jsonb;
 zero_effect_proof jsonb;
 replay_active boolean;
 correction_id uuid:=gen_random_uuid();before_movements uuid[];origin record;new_move record;anchor uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_note.access_now();perform cp7_sales.validate_draft(p_payload-'item_lineage',true);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_NOTE_REQUEST_REQUIRED';end if;
 insert into cp7_note.requests values(auth.uid(),p_request,p_payload,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_note.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_NOTE_REQUEST_CHANGED';end if;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform cp7_mandor_shop.sale_change_preflight('CORRECT',(p_payload->>'sale_id')::uuid);
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform pg_advisory_xact_lock(hashtextextended('FGBOOK|GLOBAL',0));
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 leaf:=(p_payload->>'sale_id')::uuid;
 perform 1 from erp.sales_payments where sale_id=leaf order by id for update;
 perform 1 from erp.sales_returns where sale_id=leaf order by id for update;
 select *into h from erp.sales_headers where id=leaf for update;
 if h.id is null or h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_NOTE_ACTIVE_POSTED_ONLY';end if;
 if h.row_version::text<>p_expected or cp7_sales.review_token(h.id)<>p_payload->>'review_token'then raise exception 'CP7_NOTE_REVIEW_CHANGED';end if;
 -- Historical correction keeps the actual original event identity/time.
 if p_payload->>'sale_number'is distinct from h.sale_number
  or(p_payload->>'sale_date')::timestamptz is distinct from h.sale_date
  or(p_payload->>'customer_id')::uuid is distinct from h.customer_id
  or(p_payload->>'source_location_id')::uuid is distinct from h.source_location_id then raise exception 'CP7_NOTE_SOURCE_IDENTITY_CHANGED';end if;
 select root_sale_id into root from cp7_note.revisions where replacement_sale_id=leaf;
 root:=coalesce(root,leaf);
 select coalesce(max(r.revision),0)+1 into revision from cp7_note.revisions r where r.root_sale_id=root;
 if exists(select 1 from cp7_note.revisions where previous_sale_id=leaf)then raise exception 'CP7_NOTE_SOURCE_SUPERSEDED';end if;
 if exists(select 1 from erp.sales_payments where sale_id=leaf and status='DRAFT')
  or exists(select 1 from erp.sales_returns where sale_id=leaf and status='DRAFT')then
  raise exception 'CP7_NOTE_PENDING_CHILD_REVIEW_REQUIRED';end if;
 -- A native cash reallocation is journaled at its predecessor's reversal date.
 -- Replaying it here would move that cash back to the original receipt clock;
 -- like payment correction, such a payment stays outside this command.
 if exists(select 1 from erp.sales_payments where sale_id=leaf and status='POSTED'and replaces_payment_id is not null)then
  raise exception 'CP7_NOTE_REALLOCATED_PAYMENT_REVIEW_REQUIRED';end if;
 select coalesce(jsonb_agg(to_jsonb(p)||jsonb_build_object('advance_id',l.advance_id)order by p.payment_date,p.id),'[]')into paid
 from erp.sales_payments p left join erp.initial_import_prepayment_payments l on l.payment_id=p.id
 where p.sale_id=leaf and p.status='POSTED';
 select coalesce(jsonb_agg(to_jsonb(r)||jsonb_build_object('items',
  (select jsonb_agg(to_jsonb(i)||jsonb_build_object('allocation_location_id',x.location_id)order by i.id)
    from erp.sales_return_items i join erp.sale_stock_allocations x on x.id=i.sale_stock_allocation_id where i.return_id=r.id))order by r.physical_at,r.id),'[]')into returns
 from erp.sales_returns r where r.sale_id=leaf and r.status='POSTED';
 select array_agg(m.id)into before_movements from erp.fg_stock_movements m where
  (m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=leaf)
   or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=leaf and r.status='POSTED'))
  and m.movement_type in('SALE','SALE_RETURN')and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);
 replay_active:=cp7_note_replay.begin_replay(p_payload,p_request,p_expected,correction_id,a);
 zero_effect_proof:=cp7_note_zero_effect.prepare_v1(p_payload,p_request,p_expected,correction_id,a);
 insert into cp7_note.context values(pg_backend_pid(),txid_current(),auth.uid(),leaf);
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),leaf,'SALE_REVERSE');
 perform set_config('app.change_reason',p_payload->>'change_reason',true);
 -- D15-1 / Sol SOL-R1-001: the cash guard judges the end state of inverse + replacement, not the half-way balance.
 if pg_catalog.to_regprocedure('cp7_guard.begin_compound(text)')is not null then perform cp7_guard.begin_compound('SALES_NOTE_CORRECTION');end if;
 -- Remove active children before reversing the invoice, then restore their
 -- immutable original physical inputs onto its replacement in one command.
 for payment in select *from jsonb_to_recordset(paid)as p(id uuid)loop
  perform cp7_sales.command_access('PAYMENT_REVERSE');perform cp7_note.reverse_sales_payment(payment.id,p_payload->>'change_reason');
 end loop;
 for returned in select *from jsonb_to_recordset(returns)as r(id uuid)loop
  perform cp7_sales.command_access('RETURN_REVERSE');perform cp7_note.reverse_sales_return(returned.id,p_payload->>'change_reason');
 end loop;
 perform cp7_note.reverse_sale(leaf,p_payload->>'change_reason');
 native_request:=md5(auth.uid()::text||':NOTE:'||p_request::text)::uuid;
 draft:=(p_payload-'sale_id'-'review_token'-'change_reason'-'item_lineage')||jsonb_build_object('sale_number',left((select sale_number from erp.sales_headers where id=root),38)||' · R'||revision::text||'-'||left(p_request::text,8),'reason',p_payload->>'change_reason');
 result:=erp.save_sale_draft_v2(draft,native_request,null);
 replaced:=(result->>'sale_id')::uuid;
 perform cp7_note.bind_items(leaf,replaced,correction_id,p_payload->'items',p_payload->'item_lineage');
 perform erp.post_sale(replaced);
 for returned in select value from jsonb_array_elements(returns)loop
  perform cp7_sales.command_access('RETURN');
  insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,notes,status,created_by)
  values(left(returned.value->>'return_number',38)||' · K-'||left(p_request::text,8),replaced,h.customer_id,
   (returned.value->>'physical_at')::timestamptz,returned.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_return;
  for line in select value from jsonb_array_elements(returned.value->'items')loop
   select x.id into allocation from erp.sale_stock_allocations x join erp.sales_items i on i.id=x.sale_item_id
    where i.sale_id=replaced and i.product_id=(line->>'product_id')::uuid and x.lot_id=(line->>'lot_id')::uuid
     and x.location_id=(line->>'allocation_location_id')::uuid
     and x.sale_item_id=(select l.replacement_item_id from cp7_note.item_lineage l
      join erp.sale_stock_allocations prior_allocation on prior_allocation.sale_item_id=l.previous_item_id
      where prior_allocation.id=(line->>'sale_stock_allocation_id')::uuid and l.replacement_item_id=x.sale_item_id)
     and not exists(select 1 from erp.sales_return_items z where z.return_id=new_return and z.sale_stock_allocation_id=x.id)
     and x.qty_pcs>=
      (line->>'qty_pcs')::integer+coalesce((select sum(z.qty_pcs)from erp.sales_return_items z where z.sale_stock_allocation_id=x.id),0)
    order by x.id limit 1;
   if allocation is null then raise exception 'CP7_NOTE_RETURN_ALLOCATION_CHANGED';end if;
   -- The refund was agreed for the old net price of each returned piece.
   -- Replaying it onto a line sold at another net price would overstate (or
   -- refuse) receivable without anyone seeing it: correct the return first.
   if exists(select 1 from erp.sale_stock_allocations old_x join erp.sales_items o on o.id=old_x.sale_item_id,
     erp.sale_stock_allocations new_x join erp.sales_items n on n.id=new_x.sale_item_id
    where old_x.id=(line->>'sale_stock_allocation_id')::uuid and new_x.id=allocation
     and(o.qty_pcs*o.unit_price_snapshot-coalesce(o.discount_amount,0))*n.qty_pcs
      <>(n.qty_pcs*n.unit_price_snapshot-coalesce(n.discount_amount,0))*o.qty_pcs)then
    raise exception 'CP7_NOTE_RETURNED_LINE_PRICE_CHANGED';end if;
   insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,quality_grade,refund_amount,notes)
   values(new_return,allocation,(line->>'product_id')::uuid,(line->>'lot_id')::uuid,(line->>'location_id')::uuid,
    (line->>'qty_pcs')::integer,line->>'quality_grade',(line->>'refund_amount')::numeric,line->>'notes')returning id into new_return_item;
   return_lineage:=return_lineage||jsonb_build_object(new_return_item::text,line->>'id');
  end loop;
  if replay_active then
   perform cp7_note_replay.bind_return((returned.value->>'id')::uuid,new_return,replaced,return_lineage);
   perform cp7_note_replay.post_return(new_return);
  else perform erp.post_sales_return(new_return); end if;
 end loop;
 for payment in select value from jsonb_array_elements(paid)loop
  perform cp7_sales.command_access('PAYMENT');
  insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,notes,status,created_by)
  values(replaced,left(payment.value->>'payment_number',38)||' · K-'||left(p_request::text,8),
   (payment.value->>'payment_date')::timestamptz,(payment.value->>'amount')::numeric,(payment.value->>'cash_account_id')::uuid,
   payment.value->>'payment_method',payment.value->>'reference_number',payment.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_payment;
  if payment.value->>'advance_id'is not null then
   -- Same original wallet and amount. Accepted Native funding validation locks
   -- it, checks its actual remaining amount/customer/source snapshot and dates,
   -- and posts liability/AR rather than cash. No opening balance is edited.
   insert into erp.initial_import_prepayment_payments(payment_id,advance_id,sales_payment_id,payment_snapshot)
   select new_payment,(payment.value->>'advance_id')::uuid,new_payment,to_jsonb(p)-'status'
   from erp.sales_payments p where p.id=new_payment;
  end if;
  perform erp.post_sales_payment(new_payment);
  insert into cp7_note.payment_replays(previous_payment_id,replacement_payment_id,correction_id)
  values((payment.value->>'id')::uuid,new_payment,correction_id);
 end loop;
 if pg_catalog.to_regprocedure('cp7_guard.end_compound()')is not null then perform cp7_guard.end_compound();end if;
 -- Collapse compensating movements under their original source card. A newly
 -- added SKU gets its own Native card inserted beside this note's source,
 -- using the accepted move writer. Unrelated manual order is never reset.
 -- Original quantity, recorded clock and posted price are never edited.
 for new_move in select m.*from erp.fg_stock_movements m where m.reversal_of_id=any(coalesce(before_movements,'{}'::uuid[]))
  or m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=replaced)
  or exists(select 1 from erp.fg_stock_movements reservation join erp.sales_items i on i.id=reservation.source_id
    where reservation.id=m.reversal_of_id and reservation.source_type='SALE_ITEM'and i.sale_id=replaced)
  or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=replaced)
  order by case when m.movement_type='SALE'and m.reversal_of_id is null then 0
    when m.reversal_of_id is null then 1 else 2 end,m.system_created_at,m.id loop
  anchor:=null;
  if new_move.reversal_of_id is not null then
   select coalesce(l.origin_id,new_move.reversal_of_id)into anchor from(select 1)x left join cp7_fg.correction_movements l on l.member_id=new_move.reversal_of_id;
  elsif new_move.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items where id=new_move.source_id and sale_id=replaced)then
   anchor:=cp7_note.line_origin(leaf,new_move.source_id,new_move.product_id,new_move.lot_id,new_move.location_id,new_move.quality_grade);
   if anchor is null then
    select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
     left join cp7_fg.correction_movements l on l.member_id=m.id
     where i.sale_id=replaced and i.id=new_move.source_id and m.movement_type='SALE'and m.product_id=new_move.product_id
      and m.location_id=new_move.location_id and m.quality_grade=new_move.quality_grade
     order by(m.lot_id=new_move.lot_id)desc,m.book_order,m.id limit 1;
    if anchor=new_move.id then
     select coalesce(l.origin_id,m.id) as origin_id into origin from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
      left join cp7_fg.correction_movements l on l.member_id=m.id
      where i.sale_id=leaf and m.movement_type='SALE'order by m.book_order,m.id limit 1;
     if origin.origin_id is null then raise exception 'CP7_NOTE_ORIGINAL_BOOK_SOURCE_REQUIRED';end if;
     perform erp.move_fg_stock_card_row_to_position(new_move.id,cp7_fg.book_anchor(new_move.id,origin.origin_id,'AFTER'));
    end if;
   end if;
  elsif new_move.source_type='SALES_RETURN_ITEM'then
   select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id join erp.sales_returns r on r.id=i.return_id
    left join cp7_fg.correction_movements l on l.member_id=m.id where r.sale_id=leaf and i.id=(return_lineage->>new_move.source_id::text)::uuid and m.movement_type='SALE_RETURN'
     and m.product_id=new_move.product_id and m.lot_id is not distinct from new_move.lot_id and m.location_id=new_move.location_id
     and m.quality_grade=new_move.quality_grade and m.physical_at=new_move.physical_at order by m.book_order,m.id limit 1;
  end if;
  if anchor is not null and anchor<>new_move.id then insert into cp7_fg.correction_movements values(new_move.id,anchor,correction_id,clock_timestamp());end if;
 end loop;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 insert into cp7_note.revisions(id,root_sale_id,previous_sale_id,replacement_sale_id,revision,actor,request_id,reason,effective_at)
 values(correction_id,root,leaf,replaced,revision,auth.uid(),p_request,p_payload->>'change_reason',h.sale_date);
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 delete from cp7_note.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 result:=jsonb_build_object('contract_version','cp7.note-correction-outcome.v1','kind','COMMITTED_OUTCOME',
  'action','CORRECT','request_id',p_request,'root_sale_id',root,'previous_sale_id',leaf,
  'sale_id',replaced,'revision_id',correction_id,'revision',revision::text,'effective_at',h.sale_date);
 update cp7_note.requests set response=result where actor=auth.uid()and request_id=p_request;
 if replay_active then perform cp7_note_replay.finish(result); end if;
 if zero_effect_proof is not null then
  perform cp7_note_zero_effect.finish_v1(zero_effect_proof,result);
 end if;
 return result;
end $function$
;
set local role cp7_sales_write;
revoke create on schema cp7_note from postgres;
reset role;
revoke cp7_sales_write from postgres granted by postgres restrict;

CREATE OR REPLACE FUNCTION cp7_credit.assert_current_source_plan_profile(p_sale uuid, p_root uuid, p_leaf uuid, p_actual jsonb)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare root uuid;actual jsonb;e record;
begin
 if(p_actual->>'sale_id',p_actual->>'root_sale_id',p_actual->>'current_leaf_id')is distinct from
   (p_sale::text,p_root::text,p_leaf::text)then raise exception 'CP7_CREDIT_CURRENT_ASSIGNMENT_CHANGED';end if;
 if jsonb_typeof(p_actual->'upstream_root_ids')is distinct from'array'
  or not(p_actual->'upstream_root_ids')@>jsonb_build_array(p_root)then raise exception 'CP7_CREDIT_CURRENT_SOURCE_ROOT_SET_REQUIRED';end if;
 for root in select value::uuid from jsonb_array_elements_text(p_actual->'upstream_root_ids')order by value loop
  actual:=case when root=p_root then p_actual else cp7_credit.current_materialized_objects(root,root,root)end;
  for e in select ce.id from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=root order by ce.id loop
   perform cp7_credit.consumer_event_data_v1(e.id);
  end loop;
  if root=p_root and exists(select from cp7_note_replay.receipts rr where rr.root_sale=root and rr.new_sale=p_leaf)then
   perform cp7_note_replay.assert_profile(p_sale,p_root,p_leaf,actual);
  elsif root=p_root and cp7_credit_note_carry_de.has_root_v1(root)then
   perform cp7_credit_note_carry_de.assert_profile_v1(p_sale,p_root,p_leaf,actual);
  elsif root=p_root and cp7_note_zero_effect.has_owned_root_v1(root)then
   perform cp7_note_zero_effect.assert_owned_profile_v1(p_sale,p_root,p_leaf,actual);
  else perform cp7_credit._consumer_root_source_profile_v1(root,root,root,actual);end if;
 end loop;
end $function$
;

CREATE OR REPLACE FUNCTION cp7_credit.assert_initial_return_closed_v1(p_operation uuid)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare m cp7_credit.initial_return_materializations;c cp7_credit.initial_return_completions;q cp7_sales.requests;a jsonb;h erp.sales_headers;net numeric;paid numeric; leaf uuid;
begin
 select *into strict m from cp7_credit.initial_return_materializations where operation_id=p_operation;
 select *into strict q from cp7_sales.requests where actor=m.actor and request_id=m.request_id;
 if q.action<>'RETURN'or q.payload is distinct from m.legacy_payload or q.expected_version is distinct from m.expected_version
  or(q.response->>'sale_id',q.response->>'return_id',q.response->>'return_status',q.response->>'action',q.response->>'request_id')is distinct from
   (m.source_sale_id::text,m.source_return_id::text,'POSTED','RETURN',m.request_id::text)then raise exception 'CP7_CREDIT_FINAL_INNER_RECEIPT_REQUIRED';end if;
 if m.origin='REVIEWED_SETTLEMENT'then
  select *into strict c from cp7_credit.initial_return_completions where operation_id=m.operation_id;
  if c.inner_receipt is distinct from q.response or c.final_manifest_sha256 is distinct from ow04_source_proposal.sha(c.final_manifest)
   or not exists(select 1 from cp7_credit.return_requests o where o.actor=m.actor and o.request_id=m.request_id and o.expected_version=m.expected_version
    and cp7_credit.pg_jsonb_sha256(o.payload)=m.payload_sha256 and o.response=c.outer_receipt)then raise exception 'CP7_CREDIT_FINAL_OUTER_RECEIPT_REQUIRED';end if;
 end if;
 if exists(select 1 from cp7_credit.initial_return_work where operation_id=m.operation_id)
  or exists(select 1 from cp7_credit.execution_context where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.return_native_scope where actor=m.actor and return_id=m.source_return_id)
  or exists(select 1 from cp7_credit.return_command_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.posting_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where actor=m.actor and request_id=m.request_id)then raise exception 'CP7_CREDIT_FINAL_PRIVATE_SCOPE_LEAK';end if;
 select *into strict h from erp.sales_headers where id=m.source_sale_id;
 if h.status='REVERSED'and m.origin='ORDINARY'then
  leaf:=cp7_note_zero_effect.owned_leaf_for_return_v1(m.source_sale_id,m.operation_id);
  if leaf is null then leaf:=cp7_note_replay.owned_leaf(m.source_sale_id,m.operation_id);end if;
  if leaf is not null then select *into strict h from erp.sales_headers where id=leaf;end if;
 end if;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_CREDIT_NEW_RETURN_FINAL_ACTIVE_SALE_REQUIRED';end if;
 a:=cp7_credit.inspect_current_materialized_profile(h.id,m.source_sale_id,h.id);
 perform cp7_credit.assert_current_source_plan_profile(h.id,m.source_sale_id,h.id,a);
 perform cp7_credit.assert_financial_materialization_provenance(a);
 net:=(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=h.id)
  -(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.status='POSTED');
 paid:=(select coalesce(sum(amount),0)from erp.sales_payments where sale_id=h.id and status='POSTED')+(a->>'U')::numeric-(a->>'I')::numeric;
 if net<0 or paid<0 or paid>net or h.status<>(case when paid=net then'PAID'when paid>0 then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_FINAL_AR_OR_STATUS_MISMATCH';end if;
 if m.cohort_id is not null and m.settlement->>'mode'='REFUND'and not exists(select 1 from cp7_credit.consumption_events ce
  where ce.id=m.refund_operation_id and ce.cohort_id=m.cohort_id and ce.amount=(m.actual_kernel->>'net_current_k')::numeric)then
  raise exception 'CP7_CREDIT_FINAL_FULL_REFUND_MISSING';end if;
end $function$
;

CREATE OR REPLACE FUNCTION cp7_credit.assert_financial_materialization_provenance(p_actual jsonb)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare marker_id uuid;f cp7_credit.financial_materializations;m cp7_credit.initial_return_materializations;o cp7_credit.initial_refund_operations;
begin
 perform cp7_credit.assert_native_empty_provenance_v1(p_actual);
 p_actual:=cp7_credit.without_native_empty_markers_v1(p_actual);
 for marker_id in select value::uuid from jsonb_array_elements_text(p_actual->'materialization_ids')loop
  select fm.*into strict f from cp7_credit.financial_materializations fm where fm.id=marker_id;
  select *into m from cp7_credit.initial_return_materializations where materialization_id=f.id;
  if m.operation_id is not null then
   if(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.payload_sha256,f.source_plan_sha256)is distinct from
    (m.source_sale_id,m.actor,m.request_id,1,m.payload_sha256,m.projection_sha256)
    or f.owning_action<>(case when m.origin='ORDINARY'then'RETURN'else'RETURN_SETTLEMENT'end)
    or m.projection_sha256 is distinct from ow04_source_proposal.sha(m.projection)
    or m.projection_actual_proof_sha256 is distinct from ow04_source_proposal.sha(m.projection_actual_proof)
    or m.prior_causal->>'proof_sha256'is distinct from ow04_source_proposal.sha(m.prior_causal_manifest)
    or not exists(select 1 from cp7_credit.return_families rf where rf.id=m.family_id and rf.first_return_id=m.source_return_id
     and rf.family_ordinal=m.family_ordinal and rf.actor=m.actor and rf.request_id=m.request_id)then
    raise exception 'CP7_CREDIT_INITIAL_PROVENANCE_CHANGED';end if;
  elsif exists(select 1 from cp7_credit.source_operation_materializations_v1 where financial_marker_id=f.id)then
   perform cp7_credit.assert_source_materialization_v1((select operation_id from cp7_credit.source_operation_materializations_v1 where financial_marker_id=f.id));
  elsif exists(select 1 from cp7_credit.consumer_operations_v1 where id=f.id)then
   perform cp7_credit.consumer_actual_manifest_v1(f.id);
  elsif exists(select from cp7_note_replay.receipts nr where nr.correction=f.id)then
   perform cp7_note_replay.assert_marker(f.id);
  elsif cp7_credit_correction_de.marker_owned_v1(f.id)then
   perform cp7_credit_correction_de.assert_marker_v1(f.id);
  else
   select *into strict o from cp7_credit.initial_refund_operations where id=f.id;
   select *into strict m from cp7_credit.initial_return_materializations where refund_operation_id=o.id;
   if(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.owning_action,f.payload_sha256,f.source_plan_sha256)is distinct from
    (m.source_sale_id,m.actor,m.request_id,o.materialization_ordinal,'RETURN_SETTLEMENT',m.payload_sha256,m.projection_sha256)
    or not exists(select 1 from cp7_credit.consumption_events ce where ce.id=o.id and ce.cohort_id=m.cohort_id)
    or jsonb_array_length(f.actual_objects)<>1 or f.actual_objects->0->>'object_kind'<>'CONSUMPTION'
    or f.actual_objects->0->>'object_id'<>o.id::text then raise exception 'CP7_CREDIT_REFUND_PROVENANCE_CHANGED';end if;
  end if;
 end loop;
end $function$
;

CREATE OR REPLACE FUNCTION cp7_credit.enforce_initial_return_closure_v1()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare operation uuid;source_operation uuid;row jsonb:=to_jsonb(new);family uuid;plan uuid;
begin
 if cp7_credit_correction_de.close_fact_v1(tg_table_name,row)then return null;end if;
 if tg_table_name in('financial_materializations','financial_materialization_objects') then
   operation:=(case when tg_table_name='financial_materializations' then row->>'id' else row->>'materialization_id' end)::uuid;
   if exists(select from cp7_note_replay.receipts nr where nr.correction=operation) then
      perform cp7_note_replay.assert_marker(operation); return null;
   end if;
   operation:=null;
 end if;
 if tg_table_name in('consumption_events','financial_materializations','financial_materialization_objects')then
  select id into source_operation from cp7_credit.consumer_operations_v1 where id=
   (case when tg_table_name='financial_materialization_objects'then row->>'materialization_id'else row->>'id'end)::uuid;
  if source_operation is not null then perform cp7_credit.assert_consumer_closed_v1(source_operation);return null;end if;
 end if;
 operation:=cp7_credit.native_empty_closure_id_v1(tg_table_name,to_jsonb(new));
 if operation is not null then perform cp7_credit.assert_native_empty_closed_v1(operation);return null;end if;
 if tg_table_name in('financial_materializations','financial_materialization_objects')then
  select operation_id into source_operation from cp7_credit.source_operation_materializations_v1
   where financial_marker_id=(case when tg_table_name='financial_materializations'then row->>'id'else row->>'materialization_id'end)::uuid;
  if source_operation is not null then perform cp7_credit.assert_source_operation_closed_v1(source_operation);return null;end if;
 end if;
 if tg_table_name in('initial_return_materializations','initial_return_completions')then operation:=(row->>'operation_id')::uuid;
 elsif tg_table_name='initial_refund_operations'then select operation_id into operation from cp7_credit.initial_return_materializations where refund_operation_id=(row->>'id')::uuid;
 elsif tg_table_name='financial_materializations'then select operation_id into operation from cp7_credit.initial_return_materializations where materialization_id=(row->>'id')::uuid or refund_operation_id=(row->>'id')::uuid;
 elsif tg_table_name='financial_materialization_objects'then select operation_id into operation from cp7_credit.initial_return_materializations where materialization_id=(row->>'materialization_id')::uuid or refund_operation_id=(row->>'materialization_id')::uuid;
 else
  case tg_table_name
   when'return_families'then family:=(row->>'id')::uuid;
   when'return_family_members'then family:=(row->>'family_id')::uuid;
   when'cohorts'then family:=(row->>'family_id')::uuid;
   when'recognition_plans'then plan:=(row->>'id')::uuid;
   when'plan_support_events'then plan:=(row->>'plan_id')::uuid;
   when'recognition_components'then plan:=(row->>'plan_id')::uuid;
   when'component_parts'then select plan_id into plan from cp7_credit.recognition_components where id=(row->>'component_id')::uuid;
   when'component_journals'then select cc.plan_id into plan from cp7_credit.component_parts pp join cp7_credit.recognition_components cc on cc.id=pp.component_id where pp.id=(row->>'part_id')::uuid;
   when'consumption_events'then select family_id into family from cp7_credit.cohorts where id=(row->>'cohort_id')::uuid;
   when'plan_dependencies'then plan:=(row->>'plan_id')::uuid;
   else raise exception 'CP7_CREDIT_CLOSURE_TABLE_UNRECOGNIZED';
  end case;
  select operation_id into source_operation from cp7_credit.source_operation_plans_v1 where plan_id=plan;
  if source_operation is not null then perform cp7_credit.assert_source_operation_closed_v1(source_operation);return null;end if;
  select operation_id into operation from cp7_credit.initial_return_materializations where family_id=family or plan_id=plan;
 end if;
 if operation is null then raise exception 'CP7_CREDIT_UNOWNED_IMMUTABLE_FACT';end if;
 perform cp7_credit.assert_initial_return_closed_v1(operation);return null;
end $function$
;
do $note_catalog$
declare actual_ jsonb;
begin
  if session_user<>'postgres' or current_user<>'postgres' or current_setting('is_superuser')<>'off' or to_regnamespace('cp7_note_replay') is null
     or pg_has_role('postgres','cp7_sales_write','SET') or pg_has_role('postgres','cp7_sales_write','USAGE')
     or has_schema_privilege('postgres','cp7_note','CREATE') then raise exception 'Unexpected authority or note namespace'; end if;
  select coalesce(jsonb_object_agg(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))),'{}')
    into actual_ from pg_proc p join pg_namespace ns on ns.oid=p.pronamespace
    where ns.nspname='cp7_note_replay' or p.oid::regprocedure::text in (select jsonb_object_keys('{"cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)":"8011f1995b6249d5d72fa98910c2bda3","cp7_credit.assert_financial_materialization_provenance(jsonb)":"d7a4811567bdcd49786d99329943cb78","cp7_credit.assert_initial_return_closed_v1(uuid)":"bf3e85df164913ba6a10e3d90a0c9b0c","cp7_credit.enforce_initial_return_closure_v1()":"83c81c2e61101e21296cf6a3a3db752b","cp7_note.command(jsonb,uuid,text)":"0712b785c0d44b46878e2cca642be71f","erp.post_sales_return(uuid)":"9341d82b8266d306b6db9cc6dd784495"}'::jsonb));
  if actual_ is distinct from '{"cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)":"ff2ab80b8bfa2535de22be22c591ad52","cp7_credit.assert_financial_materialization_provenance(jsonb)":"baa46b87b43586ee680196846e86d7d2","cp7_credit.assert_initial_return_closed_v1(uuid)":"dd71a5fca19320a07c1a1026d34b5787","cp7_credit.enforce_initial_return_closure_v1()":"e6cc80fa83c1edd91374775117921cf1","cp7_note.command(jsonb,uuid,text)":"890f3e7681d212ecf0b191d5a91d2185","cp7_note_replay.assert_marker(uuid)":"30fe5feb974c9babe4c72112a854588c","cp7_note_replay.assert_profile(uuid,uuid,uuid,jsonb)":"239bdfd8564e60e73801191b2f77ade5","cp7_note_replay.begin_replay(jsonb,uuid,text,uuid,jsonb)":"9624314f8afab55dc55a0e5f6884aa2c","cp7_note_replay.bind_return(uuid,uuid,uuid,jsonb)":"ba3c0848dbd223ee987cfec5e017286c","cp7_note_replay.checked_paid(uuid,numeric,numeric,numeric,boolean)":"8147515ec6e6338e8fb8f3e8b68b839c","cp7_note_replay.closed_work()":"304081d9b7f3890e1026d9956f3318ed","cp7_note_replay.dated_totals(jsonb)":"eda32e73967e96175e45eb512deb98ea","cp7_note_replay.finish(jsonb)":"02220060005cf0c8e233deb09b47cbcf","cp7_note_replay.keep_link(uuid)":"6bc4fe69bc3791a680565973c38afad7","cp7_note_replay.owned_leaf(uuid,uuid)":"44a0f855a52d81dc3be181cdd4645bdd","cp7_note_replay.post_journal(text,uuid,date,text,jsonb)":"ea9388241e055bbfe37dcf18e8c95255","cp7_note_replay.post_return(uuid)":"a601acb2b653a85273182553c139d20c","cp7_note_replay.work_for(uuid)":"33f66370be1d56ce435fccab2479de92","erp.post_sales_return(uuid)":"9341d82b8266d306b6db9cc6dd784495"}'::jsonb then raise exception 'The installed note, return or credit functions differ from the qualified source'; end if;
end $note_catalog$;
