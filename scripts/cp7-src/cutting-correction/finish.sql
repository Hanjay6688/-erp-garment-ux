-- D14-14 gap G2: finish a Production Order from the connected HPP screen, which makes its HPP final (the UX demo HPP
-- checklist line "Produksi sudah selesai · PO berstatus FINISHED").
-- One command, one transaction, through the accepted Native writer only: erp.finish_production_order(po), which itself
-- refuses a PO with laundry still out, laundry GOOD pieces not yet through QC, an open BS case, or no finished goods; then
-- rebuilds the PO HPP, propagates conversion HPP, syncs the HPP to the GL and closes the residual WIP of the PO to
-- OTHER_EXPENSE on today's WIB date. The facade shows those same Native preconditions before the click (same sums as the
-- Native function), plus the predicate of the Native trigger erp.guard_finished_po_source_accounting (every cut piece of
-- each Potongan sent to laundry or through direct QC, Astra ASTRA-C17-05), the current WIP balance of the PO and the
-- Native completeness list (erp.get_hpp_completeness), and asks for a reviewed token and a reason. A finished PO can be
-- reopened from the app through po-reopen.sql (owner D15-4; Native erp.reopen_production_order, Fable FABLE-014).
-- Post-conditions: the PO is FINISHED and its WIP balance is zero.
create table cp7_cutting_correction.finish_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,response jsonb,primary key(actor,request_id)
);
create table cp7_cutting_correction.finish_history(
 actor uuid not null,request_id uuid not null,po_id uuid not null references erp.production_orders,
 source jsonb not null,result jsonb not null,reason text not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_cutting_correction.finish_requests owner to postgres;
alter table cp7_cutting_correction.finish_history owner to postgres;
alter table cp7_cutting_correction.finish_requests enable row level security;
alter table cp7_cutting_correction.finish_history enable row level security;
create policy private_finish_requests on cp7_cutting_correction.finish_requests for all using(false)with check(false);
create policy private_finish_history on cp7_cutting_correction.finish_history for all using(false)with check(false);
revoke all on cp7_cutting_correction.finish_requests,cp7_cutting_correction.finish_history
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
create trigger immutable_finish_history before update or delete on cp7_cutting_correction.finish_history
 for each row execute function cp7_cutting_correction.immutable();
create trigger immutable_finish_history_truncate before truncate on cp7_cutting_correction.finish_history
 for each statement execute function cp7_cutting_correction.immutable();

create function cp7_cutting_correction.finish_access_now()returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;permission text;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_PO_FINISH_DENIED';end if;
 a:=erp.get_my_access_v1();
 if a->'allowed'is distinct from'true'::jsonb or coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')then
  raise exception using errcode='42501',message='CP7_PO_FINISH_DENIED';end if;
 foreach permission in array array['finance.hpp.view','finance.hpp.manage']loop
  if erp.has_permission(permission)is distinct from true then
   raise exception using errcode='42501',message='CP7_PO_FINISH_DENIED';end if;
 end loop;
 return a;
end $$;

-- Everything the command reads, for the review token. The blockers are the Native finish preconditions, computed with the
-- same sums as erp.finish_production_order; the Native function stays the authority.
create function cp7_cutting_correction.finish_snapshot(p_po uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare po erp.production_orders;c erp.contractors;sent bigint;returned bigint;claimed bigint;good bigint;qc bigint;open_bs bigint;
 fg bigint;lots bigint;recost bigint;wip numeric;closed numeric;h jsonb;b jsonb:='[]';unaccounted bigint;unaccounted_groups bigint;
begin
 select *into po from erp.production_orders where id=p_po;
 if po.id is null then return null;end if;
 select *into c from erp.contractors where id=po.contractor_id;
 select coalesce(sum(ldl.qty_sent_pcs),0)into sent from erp.laundry_delivery_lines ldl join erp.laundry_deliveries ld on ld.id=ldl.delivery_id
  where ld.po_id=po.id and ld.status not in('DRAFT','REVERSED');
 select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0)into returned from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr on lr.id=lrl.receipt_id join erp.laundry_deliveries ld on ld.id=lr.delivery_id
  where ld.po_id=po.id and lr.status='POSTED'and ld.status<>'REVERSED';
 select coalesce(sum(lc.qty_claimed),0)into claimed from erp.laundry_claims lc
  where lc.delivery_id in(select id from erp.laundry_deliveries where po_id=po.id)and lc.claim_type in('MISSING','STUCK')and lc.status in('SETTLED','WRITTEN_OFF');
 select coalesce(sum(lrl.qty_good_received),0)into good from erp.laundry_receipt_lines lrl
  join erp.laundry_receipts lr on lr.id=lrl.receipt_id join erp.laundry_deliveries ld on ld.id=lr.delivery_id
  where ld.po_id=po.id and lr.status='POSTED';
 select coalesce(sum(qii.qty_good_pcs+qii.qty_bs_pcs),0)into qc from erp.qc_inspection_items qii join erp.qc_inspections qi on qi.id=qii.inspection_id
  where qi.po_id=po.id and qi.status='POSTED'and qii.source_laundry_receipt_line_id is not null;
 select count(*)into open_bs from erp.bs_cases where po_id=po.id and status in('OPEN','IN_REWORK','PARTIAL');
 -- The exact predicate of the Native trigger erp.guard_finished_po_source_accounting (same view, same comparison).
 select coalesce(sum(abs(p.effective_qty_pcs-coalesce(p.source_accounted_qty_pcs,0))),0),count(*)into unaccounted,unaccounted_groups
  from erp.v_fg_partial_completion_progress p
  where p.po_id=po.id and p.effective_qty_pcs>0 and p.source_accounted_qty_pcs is distinct from p.effective_qty_pcs;
 select coalesce(sum(initial_qty_pcs),0),count(*)into fg,lots from erp.fg_lots where po_id=po.id and lot_origin='PRODUCTION';
 select count(*)into recost from erp.cost_recalc_queue q where q.entity_type='PO'and q.entity_id=po.id and q.status in('PENDING','RUNNING','FAILED');
 select coalesce(sum(jl.debit-jl.credit),0)into wip from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
  where je.status in('POSTED','REVERSED')and jl.po_id=po.id and jl.account_id=erp.account_id('WIP');
 select coalesce(sum(residual_amount),0)into closed from erp.po_wip_close_events where po_id=po.id;
 select to_jsonb(x)into h from erp.get_hpp_completeness(po.id)x;
 if po.status='CANCELLED'then b:=b||jsonb_build_object('kind','PO_CANCELLED','qty',null);end if;
 if po.status='FINISHED'then b:=b||jsonb_build_object('kind','ALREADY_FINISHED','qty',null);end if;
 if returned+claimed<sent then b:=b||jsonb_build_object('kind','LAUNDRY_OUTSTANDING','qty',sent-returned-claimed);end if;
 if sent>0 and qc<good then b:=b||jsonb_build_object('kind','QC_UNACCOUNTED','qty',good-qc);end if;
 if open_bs>0 then b:=b||jsonb_build_object('kind','OPEN_BS','qty',open_bs);end if;
 if unaccounted_groups>0 then b:=b||jsonb_build_object('kind','SOURCE_UNACCOUNTED','qty',unaccounted);end if;
 if fg<=0 then b:=b||jsonb_build_object('kind','NO_FG_OUTPUT','qty',null);end if;
 return jsonb_build_object('po',jsonb_build_object('id',po.id,'number',po.po_number,'status',po.status,'stage',po.current_stage,
   'contractor_id',po.contractor_id,'contractor_name',c.contractor_name,'updated_at',po.updated_at),
  'laundry_sent_pcs',sent,'laundry_returned_pcs',returned,'laundry_claimed_pcs',claimed,'laundry_good_pcs',good,'qc_accounted_pcs',qc,
  'open_bs_cases',open_bs,'fg_pcs',fg,'fg_lots',lots,'recost_open',recost,'wip_balance',round(wip,2),'wip_closed',round(closed,2),
  'hpp',h,'blockers',b);
end $$;

create function cp7_cutting_correction.finish_hpp(h jsonb)returns jsonb
language sql immutable security definer set search_path=''as $$
 select case when h is null then null else jsonb_build_object('display_status',h->>'display_status','engine_cost_state',h->>'engine_cost_state',
  'total',to_char(round((h->>'current_hpp_total')::numeric,2),'FM999999999999999990.00'),'qty_basis_pcs',(h->>'qty_basis_pcs')::bigint,
  'per_pcs',case when h->>'hpp_per_pcs'is null then null else to_char(round((h->>'hpp_per_pcs')::numeric,2),'FM999999999999999990.00')end,
  'pending_reasons',coalesce(h->'pending_reasons','[]'::jsonb),'latest_hpp_at',h->>'latest_hpp_at')end$$;

create function cp7_cutting_correction.finish_list(p_query text,p_offset integer)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q text;rows jsonb;n bigint;
begin
 a:=cp7_cutting_correction.finish_access_now();
 if p_offset is null or p_offset<0 or p_offset>1000000 or p_query is null or length(p_query)>80 then raise exception 'CP7_PO_FINISH_QUERY';end if;
 q:='%'||replace(replace(replace(btrim(p_query),'\','\\'),'%','\%'),'_','\_')||'%';
 select count(*)into n from erp.production_orders p where p.status<>'CANCELLED'and p.po_number ilike q;
 select coalesce(jsonb_agg(x.r order by x.finished,x.created_at desc,x.id),'[]')into rows from(
  select p.status='FINISHED'finished,p.created_at,p.id,jsonb_build_object('id',p.id,'number',p.po_number,'status',p.status,
   'contractor_name',c.contractor_name,'fg_pcs',(select coalesce(sum(l.initial_qty_pcs),0)from erp.fg_lots l where l.po_id=p.id and l.lot_origin='PRODUCTION'))r
  from erp.production_orders p left join erp.contractors c on c.id=p.contractor_id
  where p.status<>'CANCELLED'and p.po_number ilike q order by p.status='FINISHED',p.created_at desc,p.id limit 20 offset p_offset)x;
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_FINISH_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.po-finish-list.v1','query',btrim(p_query),'rows',rows,'total',n,'offset',p_offset,'limit',20,
  'next_offset',case when p_offset+jsonb_array_length(rows)<n then p_offset+jsonb_array_length(rows)end,'business_DML',false);
end $$;

create function cp7_cutting_correction.finish_workspace(p_po uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;
begin
 a:=cp7_cutting_correction.finish_access_now();s:=cp7_cutting_correction.finish_snapshot(p_po);
 if s is null or s->'hpp'is null or s->'hpp'='null'::jsonb then raise exception 'CP7_PO_FINISH_NOT_FOUND';end if;
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_FINISH_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.po-finish-workspace.v1','po_id',p_po,'po_number',s->'po'->>'number',
  'po_status',s->'po'->>'status','stage',s->'po'->>'stage','contractor_name',s->'po'->>'contractor_name',
  'fg_pcs',(s->>'fg_pcs')::bigint,'fg_lots',(s->>'fg_lots')::bigint,'laundry_sent_pcs',(s->>'laundry_sent_pcs')::bigint,
  'laundry_returned_pcs',(s->>'laundry_returned_pcs')::bigint,'laundry_claimed_pcs',(s->>'laundry_claimed_pcs')::bigint,
  'laundry_good_pcs',(s->>'laundry_good_pcs')::bigint,'qc_accounted_pcs',(s->>'qc_accounted_pcs')::bigint,
  'open_bs_cases',(s->>'open_bs_cases')::bigint,'recost_open',(s->>'recost_open')::bigint,
  'wip_balance',to_char((s->>'wip_balance')::numeric,'FM999999999999999990.00'),
  'hpp',cp7_cutting_correction.finish_hpp(s->'hpp'),'finish_date',to_char((statement_timestamp()at time zone 'Asia/Jakarta')::date,'YYYY-MM-DD'),
  'review_token',md5(s::text),'eligible',jsonb_array_length(s->'blockers')=0,'blockers',s->'blockers','business_DML',false);
end $$;

create function cp7_cutting_correction.finish_command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_cutting_correction.finish_requests;po erp.production_orders;s jsonb;s2 jsonb;r jsonb;answer jsonb;
 v_reason text;v_actor uuid;v_group uuid;wip numeric;residual numeric;
 uuid_re constant text:='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_correction.finish_access_now();
 if p_request is null or jsonb_typeof(p)is distinct from'object'
  or not(p?&array['action','po_id','review_token','change_reason'])or(select count(*)from jsonb_object_keys(p))<>4
  or p->'action'is distinct from'"FINISH"'::jsonb
  or jsonb_typeof(p->'po_id')is distinct from'string'or coalesce(p->>'po_id','')!~uuid_re
  or jsonb_typeof(p->'review_token')is distinct from'string'or coalesce(p->>'review_token','')!~'^[a-f0-9]{32}$'
  or jsonb_typeof(p->'change_reason')is distinct from'string'or length(btrim(p->>'change_reason'))not between 5 and 1000 then
  raise exception 'CP7_PO_FINISH_FIELDS';end if;
 v_reason:=btrim(p->>'change_reason');
 insert into cp7_cutting_correction.finish_requests values(auth.uid(),p_request,p,null)on conflict do nothing;
 select *into strict old from cp7_cutting_correction.finish_requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p then raise exception 'CP7_PO_FINISH_REQUEST_CHANGED';end if;
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_FINISH_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 -- Same order as the cutting writers (cutting flow lock of each Potongan, then the PO row), groups by id.
 for v_group in select id from erp.cutting_groups where po_id=(p->>'po_id')::uuid order by id loop
  perform pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||v_group::text,0));
 end loop;
 select *into po from erp.production_orders where id=(p->>'po_id')::uuid for update;
 if po.id is null then raise exception 'CP7_PO_FINISH_NOT_FOUND';end if;
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_FINISH_ACCESS_CHANGED';end if;
 s:=cp7_cutting_correction.finish_snapshot(po.id);
 if md5(s::text)is distinct from p->>'review_token'then raise exception 'CP7_PO_FINISH_STALE_REVIEW';end if;
 if jsonb_array_length(s->'blockers')<>0 then raise exception 'CP7_PO_FINISH_BLOCKED: %',s->'blockers';end if;
 v_actor:=erp.current_app_user_id();
 if v_actor is null then raise exception using errcode='42501',message='CP7_PO_FINISH_DENIED';end if;
 perform set_config('app.change_reason',v_reason,true);
 perform erp.finish_production_order(po.id);
 s2:=cp7_cutting_correction.finish_snapshot(po.id);
 select coalesce(sum(jl.debit-jl.credit),0)into wip from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
  where je.status in('POSTED','REVERSED')and jl.po_id=po.id and jl.account_id=erp.account_id('WIP');
 residual:=(s2->>'wip_closed')::numeric-(s->>'wip_closed')::numeric;
 -- Post-conditions: the PO is FINISHED, its WIP is fully moved to finished goods or closed, and HPP rows exist.
 if s2->'po'->>'status'is distinct from'FINISHED'or abs(wip)>0.005 or s2->'hpp'is null or s2->'hpp'='null'::jsonb then
  raise exception 'CP7_PO_FINISH_INCOMPLETE';end if;
 r:=jsonb_build_object('status','FINISHED','fg_pcs',(s2->>'fg_pcs')::bigint,'hpp',cp7_cutting_correction.finish_hpp(s2->'hpp'),
  'residual_closed',to_char(round(residual,2),'FM999999999999999990.00'),'wip_after',to_char(round(wip,2),'FM999999999999999990.00'),
  'finished_on',to_char((statement_timestamp()at time zone 'Asia/Jakarta')::date,'YYYY-MM-DD'),'recost_open',(s2->>'recost_open')::bigint);
 if cp7_cutting_correction.finish_access_now()is distinct from a then raise exception using errcode='42501',message='CP7_PO_FINISH_ACCESS_CHANGED';end if;
 insert into cp7_cutting_correction.finish_history values(auth.uid(),p_request,po.id,s,r,v_reason,clock_timestamp());
 answer:=jsonb_build_object('contract_version','cp7.po-finish-outcome.v1','kind','COMMITTED_OUTCOME','action','FINISH',
  'request_id',p_request,'po_id',po.id,'po_number',po.po_number,'result',r);
 update cp7_cutting_correction.finish_requests set response=answer where actor=auth.uid()and request_id=p_request;
 return answer;
end $$;

create function public.erp_cp7_list_po_finish_v1(p_query text default '',p_offset integer default 0)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.finish_list(p_query,p_offset)$$;
create function public.erp_cp7_get_po_finish_v1(p_po uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.finish_workspace(p_po)$$;
create function public.erp_cp7_finish_po_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_correction.finish_command(p_payload,p_request)$$;
alter function cp7_cutting_correction.finish_access_now()owner to postgres;
alter function cp7_cutting_correction.finish_snapshot(uuid)owner to postgres;
alter function cp7_cutting_correction.finish_hpp(jsonb)owner to postgres;
alter function cp7_cutting_correction.finish_list(text,integer)owner to postgres;
alter function cp7_cutting_correction.finish_workspace(uuid)owner to postgres;
alter function cp7_cutting_correction.finish_command(jsonb,uuid)owner to postgres;
grant create on schema public to cp7_cutting_read,cp7_cutting_write;
alter function public.erp_cp7_list_po_finish_v1(text,integer)owner to cp7_cutting_read;
alter function public.erp_cp7_get_po_finish_v1(uuid)owner to cp7_cutting_read;
alter function public.erp_cp7_finish_po_v1(jsonb,uuid)owner to cp7_cutting_write;
revoke create on schema public from cp7_cutting_read,cp7_cutting_write;
revoke all on function cp7_cutting_correction.finish_access_now(),cp7_cutting_correction.finish_snapshot(uuid),
 cp7_cutting_correction.finish_hpp(jsonb),cp7_cutting_correction.finish_list(text,integer),cp7_cutting_correction.finish_workspace(uuid),
 cp7_cutting_correction.finish_command(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_cutting_read,cp7_cutting_write;
grant execute on function cp7_cutting_correction.finish_list(text,integer),cp7_cutting_correction.finish_workspace(uuid)to cp7_cutting_read;
grant execute on function cp7_cutting_correction.finish_command(jsonb,uuid)to cp7_cutting_write;
revoke all on function public.erp_cp7_list_po_finish_v1(text,integer),public.erp_cp7_get_po_finish_v1(uuid),public.erp_cp7_finish_po_v1(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_list_po_finish_v1(text,integer),public.erp_cp7_get_po_finish_v1(uuid),public.erp_cp7_finish_po_v1(jsonb,uuid)to authenticated;
